# backend/open_webui/models/labs.py
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
# Lab DB Schema
####################

class Lab(Base):
    __tablename__ = "lab"

    id = Column(String, primary_key=True)
    user_id = Column(String, nullable=True)

    course_id = Column(String, nullable=False)

    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)

    enabled = Column(Boolean, default=True)

    # Links into existing systems
    channel_id = Column(String, nullable=True)    # channels.Channel.id
    knowledge_id = Column(String, nullable=True)  # knowledge.Knowledge.id

    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


####################
# Pydantic models
####################

class LabModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: Optional[str] = None
    course_id: str

    name: str
    description: Optional[str] = None

    enabled: bool = True

    channel_id: Optional[str] = None
    knowledge_id: Optional[str] = None

    meta: Optional[dict] = None

    created_at: int
    updated_at: int


class LabForm(BaseModel):
    course_id: str
    name: str
    description: Optional[str] = None
    enabled: Optional[bool] = True
    channel_id: Optional[str] = None
    knowledge_id: Optional[str] = None
    meta: Optional[dict] = None


class LabUpdateForm(BaseModel):
    course_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    channel_id: Optional[str] = None
    knowledge_id: Optional[str] = None
    meta: Optional[dict] = None


####################
# Table helper
####################

class LabTable:
    def insert_new_lab(self, user_id: str, form_data: LabForm) -> Optional[LabModel]:
        with get_db() as db:
            now = int(time.time())
            lab = Lab(
                id=str(uuid.uuid4()),
                user_id=user_id,
                course_id=form_data.course_id,
                name=form_data.name,
                description=form_data.description,
                enabled=form_data.enabled if form_data.enabled is not None else True,
                channel_id=form_data.channel_id,
                knowledge_id=form_data.knowledge_id,
                meta=form_data.meta,
                created_at=now,
                updated_at=now,
            )
            try:
                db.add(lab)
                db.commit()
                db.refresh(lab)
                return LabModel.model_validate(lab)
            except Exception as e:
                log.exception(e)
                return None

    def get_lab_by_id(self, id: str) -> Optional[LabModel]:
        with get_db() as db:
            row = db.query(Lab).filter_by(id=id).first()
            return LabModel.model_validate(row) if row else None

    def get_labs_by_course_id(self, course_id: str) -> List[LabModel]:
        with get_db() as db:
            rows = (
                db.query(Lab)
                .filter_by(course_id=course_id)
                .order_by(Lab.name.asc())
                .all()
            )
            return [LabModel.model_validate(r) for r in rows]

    def update_lab_by_id(self, id: str, form_data: LabUpdateForm) -> Optional[LabModel]:
        with get_db() as db:
            data = form_data.model_dump(exclude_none=True)
            data["updated_at"] = int(time.time())
            try:
                db.query(Lab).filter_by(id=id).update(data)
                db.commit()
                return self.get_lab_by_id(id)
            except Exception as e:
                log.exception(e)
                return None

    def delete_lab_by_id(self, id: str) -> bool:
        try:
            with get_db() as db:
                db.query(Lab).filter_by(id=id).delete()
                db.commit()
                return True
        except Exception:
            return False


Labs = LabTable()

# Ensure the table exists
Lab.__table__.create(bind=engine, checkfirst=True)
