import os

# Project root folder
PROJECT_DIR = r"C:\Users\ASUS\Desktop\PROJECTS\yt_dlp_backend\app"
OLD_FILENAME = "db.py"
NEW_FILENAME = "database.py"

# 1️⃣ Rename the file
old_path = os.path.join(PROJECT_DIR, OLD_FILENAME)
new_path = os.path.join(PROJECT_DIR, NEW_FILENAME)

if os.path.exists(old_path):
    os.rename(old_path, new_path)
    print(f"Renamed {OLD_FILENAME} -> {NEW_FILENAME}")
else:
    print(f"{OLD_FILENAME} not found!")

# 2️⃣ Update imports in all .py files
for root, dirs, files in os.walk(PROJECT_DIR):
    for file in files:
        if file.endswith(".py"):
            file_path = os.path.join(root, file)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            updated_content = content.replace("from app.db", "from app.database")
            updated_content = updated_content.replace("import db", "import database")
            if content != updated_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                print(f"Updated imports in {file_path}")
