import time
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Job, Message
from app.service import claim_job, process_message
from app.config import settings
from app.reporting import scheduled_report


def run() -> None:
    last_report_minute = None
    while True:
        with SessionLocal.begin() as db:
            job = claim_job(db)
            if job:
                job.status = "processing"
                try:
                    message = db.scalar(select(Message).where(Message.id == job.message_id))
                    process_message(db, message)
                    job.status = "done"
                except Exception as error:
                    job.attempts += 1
                    job.error = str(error)[:500]
                    job.status = "pending" if job.attempts < 3 else "failed"
            now = datetime.now(ZoneInfo(settings().timezone))
            minute_key = now.strftime("%Y-%m-%d-%H-%M")
            if now.hour == 19 and now.minute == 0 and minute_key != last_report_minute:
                try:
                    scheduled_report(db)
                except Exception:
                    pass
                last_report_minute = minute_key
        time.sleep(1)


if __name__ == "__main__":
    run()
