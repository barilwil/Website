"""
One-time script to backfill Folder.context_type = 'general'
for any rows where it is NULL or empty.

Run from the backend directory:

    cd backend
    python backfill_folders_context.py
"""

import logging
from sqlalchemy import or_

from open_webui.internal.db import get_db
from open_webui.models.folders import Folder

log = logging.getLogger(__name__)


def backfill_folder_context():
    with get_db() as db:
        # UPDATE folder SET context_type = 'general' WHERE context_type IS NULL OR context_type = '';
        updated = (
            db.query(Folder)
            .filter(
                or_(Folder.context_type == None, Folder.context_type == "")  # noqa: E711
            )
            .update({Folder.context_type: "general"}, synchronize_session=False)
        )
        db.commit()
        print(f"Backfilled {updated} folders with context_type='general'")


if __name__ == "__main__":
    backfill_folder_context()
