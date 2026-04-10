import os
import shutil
from pymongo import MongoClient

# 1. Delete SQLite Database
db_path = os.path.join(os.path.dirname(__file__), 'intellicredit.db')
if os.path.exists(db_path):
    try:
        os.remove(db_path)
        print("Deleted SQLite DB: intellicredit.db")
    except Exception as e:
        print(f"Could not delete SQLite DB: {e}")

# 2. Clear MongoDB cases
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["intellicredit"]
    db.cases.drop()
    print("Dropped MongoDB collection: intellicredit.cases")
except Exception as e:
    print(f"Could not drop MongoDB cases: {e}")

# 3. Clear Uploads folder
uploads_path = os.path.join(os.path.dirname(__file__), 'uploads')
if os.path.exists(uploads_path):
    try:
        for filename in os.listdir(uploads_path):
            file_path = os.path.join(uploads_path, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)
        print("Cleared uploads folder.")
    except Exception as e:
        print(f"Could not clear uploads: {e}")
