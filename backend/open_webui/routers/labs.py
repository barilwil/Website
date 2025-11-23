# backend/open_webui/routers/labs.py
from typing import Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from open_webui.models.labs import Labs, LabForm, LabUpdateForm, LabModel
from open_webui.models.channels import Channels, ChannelForm
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
    Create a Lab + its own Channel + its own Knowledge Base.
    """
    try:
        # Channel
        channel_form = ChannelForm(
            name=f"{form_data.course_id} - {form_data.name}",
            description=form_data.description or "",
            data=None,
            meta={"type": "lab"},
            access_control=None,
        )
        channel = Channels.insert_new_channel(
            type="lab",
            form_data=channel_form,
            user_id=user.id,
        )

        # Knowledge base
        knowledge_form = KnowledgeForm(
            name=f"{form_data.course_id} - {form_data.name} Resources",
            description=form_data.description or "Lab-specific resources",
            data={"file_ids": []},
            access_control=None,
        )
        knowledge = Knowledges.insert_new_knowledge(user.id, knowledge_form)

        # Lab record
        lab_form = LabForm(
            course_id=form_data.course_id,
            name=form_data.name,
            description=form_data.description,
            enabled=form_data.enabled if form_data.enabled is not None else True,
            channel_id=channel.id if channel else None,
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

@router.delete("/labs/id/{id}/delete", response_model=bool)
async def delete_lab_by_id(id: str, user=Depends(get_admin_user)):
    lab = Labs.get_lab_by_id(id)
    if not lab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # Delete channel
        if lab.channel_id:
            Channels.delete_channel_by_id(lab.channel_id)

        # Delete knowledge base (and its vector data if you want to copy the
        # delete logic from the knowledge router)
        if lab.knowledge_id:
            Knowledges.delete_knowledge_by_id(lab.knowledge_id)

        # Finally delete lab record
        Labs.delete_lab_by_id(id)
        return True
    except Exception as e:
        log.exception(f"Error deleting lab {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
