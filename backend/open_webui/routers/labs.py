# backend/open_webui/routers/labs.py
from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from open_webui.models.labs import Labs, LabForm, LabUpdateForm, LabModel
from open_webui.models.channels import Channels
from open_webui.models.knowledge import Knowledges, KnowledgeForm
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_verified_user, get_admin_user


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


class LabCreateForm(BaseModel):
    course_id: str
    name: str
    description: Optional[str] = None
    enabled: Optional[bool] = True

class LabKnowledgeLinkForm(BaseModel):
    knowledge_id: str


############################
# Student-facing
############################


@router.get("/id/{id}", response_model=Optional[LabModel])
async def get_lab_by_id(id: str, user=Depends(get_verified_user)):
    lab = Labs.get_lab_by_id(id=id)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    # normal users should not see disabled labs
    if not lab.enabled and getattr(user, "role", None) != "admin":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )
    return lab


############################
# Admin-only
############################


@router.post("/create", response_model=Optional[LabModel])
async def create_new_lab(form_data: LabCreateForm, user=Depends(get_admin_user)):
    """
    Create a Lab + its own Knowledge Base.
    Channels are per-course, not per-lab.
    """
    try:
        # Knowledge base (still per-lab)
        knowledge_form = KnowledgeForm(
            name=f"{form_data.course_id} - {form_data.name} Resources",
            description=form_data.description or "Lab-specific resources",
            data={"file_ids": []},
            access_control=None,
        )
        knowledge = Knowledges.insert_new_knowledge(user.id, knowledge_form)

        lab_form = LabForm(
            course_id=form_data.course_id,
            name=form_data.name,
            description=form_data.description,
            enabled=form_data.enabled if form_data.enabled is not None else True,
            channel_id=None,  # labs don't own channels anymore
            knowledge_id=knowledge.id if knowledge else None,
            meta={},
        )

        lab = Labs.insert_new_lab(user.id, lab_form)
        if lab:
            return lab

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error creating lab"),
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating lab: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/new", response_model=Optional[LabModel])
async def create_new_lab_alias(
        form_data: LabCreateForm, user=Depends(get_admin_user)
):
    """
    Backwards-compatible alias for creating a lab.
    Uses the same logic as /create.
    """
    return await create_new_lab(form_data=form_data, user=user)

@router.post("/id/{id}/update", response_model=Optional[LabModel])
async def update_lab_by_id(
        id: str, form_data: LabUpdateForm, user=Depends(get_admin_user)
):
    try:
        lab = Labs.update_lab_by_id(id, form_data)
        if lab:
            return lab
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error updating lab"),
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating lab {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )



@router.delete("/id/{id}/delete", response_model=bool)
async def delete_lab_by_id(id: str, user=Depends(get_admin_user)):
    lab = Labs.get_lab_by_id(id)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # Legacy cleanup: if an old lab still has its own channel, delete it
        if lab.channel_id:
            Channels.delete_channel_by_id(lab.channel_id)

        # Delete attached knowledge, if any
        if lab.knowledge_id:
            Knowledges.delete_knowledge_by_id(lab.knowledge_id)

        Labs.delete_lab_by_id(id)
        return True
    except Exception as e:
        log.exception(f"Error deleting lab {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
