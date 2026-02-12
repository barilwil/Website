#!/usr/bin/env python3
import os
import shutil
import sqlite3
import sys
import time

TOOL_ID = "circuit_analyzer"
NEW_DEFAULT = "http://127.0.0.1:8080/api/v1/spice"

def patch_content(content: str) -> str:
    c = content
    # Change default base URL
    c = c.replace('default="http://localhost:8000",', f'default="{NEW_DEFAULT}",')
    # Update docker hint + any remaining references
    c = c.replace("http://host.docker.internal:8000", "http://host.docker.internal:8080/api/v1/spice")
    c = c.replace("localhost:8000", "127.0.0.1:8080/api/v1/spice")
    # Make description a bit clearer (optional)
    c = c.replace(
        "Base URL of your SPICE Lab Assistant API (api.py). ",
        "Base URL of the mounted SPICE API inside OpenWebUI. ",
    )
    # Update health help text
    c = c.replace(
        "http://host.docker.internal:8080/api/v1/spice).",
        "http://host.docker.internal:8080/api/v1/spice).",
    )
    return c

def main() -> int:
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join("backend", "data", "webui.db")
    db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        print(f"ERROR: webui.db not found at: {db_path}")
        print("Run: python patch_circuit_tool_db.py path\\to\\backend\\data\\webui.db")
        return 2

    backup_path = db_path + f".bak.{int(time.time())}"
    shutil.copy2(db_path, backup_path)
    print(f"Backup created: {backup_path}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT content FROM tool WHERE id=?", (TOOL_ID,))
    row = cur.fetchone()
    if not row:
        print(f"ERROR: tool id '{TOOL_ID}' not found in DB.")
        conn.close()
        return 3

    old_content = row[0]
    new_content = patch_content(old_content)

    if old_content == new_content:
        print("No changes needed (tool already patched or patterns not found).")
        conn.close()
        return 0

    cur.execute(
        "UPDATE tool SET content=?, updated_at=? WHERE id=?",
        (new_content, int(time.time()), TOOL_ID),
    )
    conn.commit()
    conn.close()

    print("Patched Circuit Analyzer tool successfully.")
    print(f"New default Valves.API_BASE = {NEW_DEFAULT}")
    print("Restart OpenWebUI after this.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
