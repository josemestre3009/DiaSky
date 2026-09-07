from app.config import Settings


def test_parses_multiple_operation_groups() -> None:
    config = Settings(
        database_url="postgresql+psycopg://x:x@localhost/x",
        admin_token="test",
        webhook_secret="",
        webhook_path_token="test",
        evolution_api_url="https://example.test",
        operation_group_jids="first@g.us, second@g.us",
        authorized_creator_jids="creator@s.whatsapp.net",
        report_recipient_jid="573001234567@s.whatsapp.net",
    )
    assert config.operation_groups == {"first@g.us", "second@g.us"}
