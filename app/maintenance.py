from sqlalchemy import select

from app.db import SessionLocal
from app.models import Message, Order
from app.service import assign_prior_team


def backfill_assignments() -> int:
    with SessionLocal.begin() as db:
        orders = db.scalars(select(Order)).all()
        for order in orders:
            source = db.scalar(select(Message).where(Message.whatsapp_id == order.source_message_id))
            if source:
                assign_prior_team(db, order, source.occurred_at)
        return len(orders)


if __name__ == "__main__":
    print(f"Processed {backfill_assignments()} orders")
