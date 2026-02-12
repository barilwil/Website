# backend/open_webui/models/courses.py
import logging
import time
import uuid
from typing import Optional, List

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, String, Text, JSON, Boolean

from open_webui.internal.db import Base, get_db, engine
from open_webui.env import SRC_LOG_LEVELS

log = logging.getLogger(__name__)
log.setLevel(SRC_LOG_LEVELS["MODELS"])

####################
# Course DB Schema
####################

class Course(Base):
    __tablename__ = "course"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)

    code = Column(Text, nullable=False)        # e.g. "ECEN 403"
    name = Column(Text, nullable=False)        # e.g. "Capstone"
    description = Column(Text, nullable=True)

    enabled = Column(Boolean, default=True)

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)

####################
# Pydantic models
####################

class CourseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None

    code: str
    name: str
    description: Optional[str] = None

    enabled: bool = True

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class CourseForm(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    enabled: Optional[bool] = True
    meta: Optional[dict] = None


class CourseUpdateForm(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    meta: Optional[dict] = None

####################
# Table helper
####################

class CourseTable:
    def insert_new_course(self, user_id: str, form_data: CourseForm) -> Optional[CourseModel]:
        with get_db() as db:
            now = int(time.time())
            course = Course(
                id=str(uuid.uuid4()),
                user_id=user_id,
                code=form_data.code,
                name=form_data.name,
                description=form_data.description,
                enabled=form_data.enabled if form_data.enabled is not None else True,
                meta=form_data.meta,
                created_at=now,
                updated_at=now,
            )

            try:
                db.add(course)
                db.commit()
                db.refresh(course)
                return CourseModel.model_validate(course)
            except Exception as e:
                log.exception(e)
                return None

    def get_courses(self) -> List[CourseModel]:
        with get_db() as db:
            rows = db.query(Course).order_by(Course.code.asc()).all()
            return [CourseModel.model_validate(r) for r in rows]

    def get_course_by_id(self, id: str) -> Optional[CourseModel]:
        with get_db() as db:
            row = db.query(Course).filter_by(id=id).first()
            return CourseModel.model_validate(row) if row else None

    def update_course_by_id(self, id: str, form_data: CourseUpdateForm) -> Optional[CourseModel]:
        with get_db() as db:
            data = form_data.model_dump(exclude_none=True)
            data["updated_at"] = int(time.time())
            try:
                db.query(Course).filter_by(id=id).update(data)
                db.commit()
                return self.get_course_by_id(id)
            except Exception as e:
                log.exception(e)
                return None

    def delete_course_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Course).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


Courses = CourseTable()

# Make sure the table exists in the DB
Course.__table__.create(bind=engine, checkfirst=True)
