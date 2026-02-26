from typing import Optional, List
import logging

from fastapi import APIRouter, Depends, HTTPException, status

from open_webui.models.courses import Courses, CourseForm, CourseUpdateForm, CourseModel
from open_webui.models.labs import Labs, LabModel
from open_webui.models.groups import Groups, GroupForm
from open_webui.constants import ERROR_MESSAGES
from open_webui.env import SRC_LOG_LEVELS
from open_webui.utils.auth import get_verified_user, get_admin_user

from open_webui.models.channels import Channels, ChannelForm
from open_webui.models.knowledge import Knowledges


log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MAIN"])

router = APIRouter()


def _get_allowed_course_ids_for_user(user) -> set[str]:
    """
    For non-admins: courses are visible only if the user belongs to
    a Group whose meta.course_id matches the course id.
    """
    if getattr(user, "role", None) == "admin":
        return set()

    groups = Groups.get_groups_by_member_id(user.id)
    course_ids: set[str] = set()

    for g in groups:
        try:
            if g.meta and g.meta.get("course_id"):
                course_ids.add(g.meta["course_id"])
        except Exception:
            continue

    return course_ids


############################
# Student-facing
############################


@router.get("/", response_model=List[CourseModel])
async def list_courses(user=Depends(get_verified_user)):
    """
    Return courses visible to this user.
    - Admin: all courses.
    - Normal user: only courses whose group they belong to and that are enabled.
    """
    try:
        all_courses = Courses.get_courses()

        # Admin sees everything
        if getattr(user, "role", None) == "admin":
            return all_courses

        allowed_ids = _get_allowed_course_ids_for_user(user)

        return [c for c in all_courses if c.id in allowed_ids and (c.enabled is True)]
    except Exception as e:
        log.exception(f"Error listing courses: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.get("/id/{id}", response_model=Optional[CourseModel])
async def get_course_by_id(id: str, user=Depends(get_verified_user)):
    course = Courses.get_course_by_id(id=id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    if getattr(user, "role", None) != "admin":
        allowed_ids = _get_allowed_course_ids_for_user(user)
        if course.id not in allowed_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

    return course


@router.get("/id/{id}/labs", response_model=List[LabModel])
async def list_labs_for_course(id: str, user=Depends(get_verified_user)):
    """
    List labs for a course, with same group-based visibility rules.
    """
    try:
        course = Courses.get_course_by_id(id=id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        if getattr(user, "role", None) != "admin":
            allowed_ids = _get_allowed_course_ids_for_user(user)
            if course.id not in allowed_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=ERROR_MESSAGES.NOT_FOUND,
                )

        labs = Labs.get_labs_by_course_id(course_id=id)

        # Only enabled labs for non-admins
        if getattr(user, "role", None) != "admin":
            labs = [l for l in labs if l.enabled]

        return labs
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error listing labs for course {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


############################
# Admin-only
############################


@router.post("/create", response_model=Optional[CourseModel])
async def create_new_course(form_data: CourseForm, user=Depends(get_admin_user)):
    """
    Create a Course, its Group, and its course-level Channel.
    """
    try:
        course = Courses.insert_new_course(user.id, form_data)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=ERROR_MESSAGES.DEFAULT("Error creating course"),
            )

        # 1) Course Group (enrollment)
        group_form = GroupForm(
            name=course.code,
            description=course.name or "",
            permissions=None,
            meta={"course_id": course.id},
        )
        group = Groups.insert_new_group(user.id, group_form)

        # 2) Course Channel (one per course)
        # Make the channel readable/writable ONLY by members of the course group.
        channel_access_control = None

        if group:
            channel_access_control = {
                "read": {"group_ids": [group.id], "user_ids": []},
                "write": {"group_ids": [group.id], "user_ids": []},
            }

        channel_form = ChannelForm(
            name=course.code,
            description=course.name or "",
            data=None,
            meta={"type": "course", "course_id": course.id},
            access_control=channel_access_control,
        )

        channel = Channels.insert_new_channel(
            type="course",
            form_data=channel_form,
            user_id=user.id,
        )

        # 3) Save references in course.meta
        meta = course.meta or {}
        if group:
            meta["group_id"] = group.id
        if channel:
            meta["channel_id"] = channel.id

        if meta:
            course = Courses.update_course_by_id(course.id, CourseUpdateForm(meta=meta))

        return course
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error creating course: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.post("/id/{id}/update", response_model=Optional[CourseModel])
async def update_course_by_id(
        id: str, form_data: CourseUpdateForm, user=Depends(get_admin_user)
):
    """Update a course (admin only). Used for toggling `enabled` and editing metadata."""
    try:
        course = Courses.get_course_by_id(id=id)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ERROR_MESSAGES.NOT_FOUND,
            )

        updated = Courses.update_course_by_id(id, form_data)
        if updated:
            return updated

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT("Error updating course"),
        )
    except HTTPException:
        raise
    except Exception as e:
        log.exception(f"Error updating course {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )


@router.delete("/id/{id}/delete", response_model=bool)
async def delete_course_by_id(id: str, user=Depends(get_admin_user)):
    course = Courses.get_course_by_id(id=id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERROR_MESSAGES.NOT_FOUND,
        )

    try:
        # 1) Delete all labs (and their channels/knowledge) for this course
        labs = Labs.get_labs_by_course_id(course_id=id)
        for lab in labs:
            if lab.channel_id:
                Channels.delete_channel_by_id(lab.channel_id)
            if lab.knowledge_id:
                Knowledges.delete_knowledge_by_id(lab.knowledge_id)
            Labs.delete_lab_by_id(lab.id)

        # 2) Delete a course-level channel, if stored in course.meta["channel_id"]
        channel_id = (course.meta or {}).get("channel_id")
        if channel_id:
            Channels.delete_channel_by_id(channel_id)

        # 3) Delete any Group whose meta.course_id == this course id
        for group in Groups.get_groups():
            if group.meta and group.meta.get("course_id") == id:
                Groups.delete_group_by_id(group.id)

        # 4) Finally, delete the course itself
        Courses.delete_course_by_id(id)
        return True

    except Exception as e:
        log.exception(f"Error deleting course {id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERROR_MESSAGES.DEFAULT(e),
        )
