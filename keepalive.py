import threading
import time
from sqlalchemy import text
from models import db  # or wherever your db object is

def keep_db_alive():
    while True:
        try:
            db.session.execute(text("SELECT 1"))
            db.session.commit()
        except Exception:
            pass
        time.sleep(300)  # run every 5 minutes (safe for Azure Serverless)
