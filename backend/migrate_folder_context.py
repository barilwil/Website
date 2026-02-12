from pathlib import Path
import sqlite3

# Path to your SQLite DB (from open_webui/env.py: DATA_DIR/webui.db)
BACKEND_DIR = Path(__file__).parent
db_path = BACKEND_DIR / "data" / "webui.db"

print(f"Using DB: {db_path}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# See current columns
cur.execute("PRAGMA table_info(folder);")
cols = [row[1] for row in cur.fetchall()]
print("Existing folder columns:", cols)

# 1) Add missing columns
if "context_type" not in cols:
    print("Adding column context_type...")
    cur.execute("ALTER TABLE folder ADD COLUMN context_type TEXT;")

if "course_id" not in cols:
    print("Adding column course_id...")
    cur.execute("ALTER TABLE folder ADD COLUMN course_id TEXT;")

if "lab_id" not in cols:
    print("Adding column lab_id...")
    cur.execute("ALTER TABLE folder ADD COLUMN lab_id TEXT;")

# 2) Backfill old rows to 'general'
print("Backfilling NULL/empty context_type to 'general'...")
cur.execute(
    """
    UPDATE folder
    SET context_type = 'general'
    WHERE context_type IS NULL OR context_type = '';
    """
)

conn.commit()
conn.close()
print("Done.")
