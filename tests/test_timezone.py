from datetime import UTC, datetime

from app.service import operation_date


def test_operation_date_uses_bogota_not_vps_utc_date() -> None:
    assert operation_date(datetime(2026, 9, 7, 2, 30, tzinfo=UTC)).isoformat() == "2026-09-06"
