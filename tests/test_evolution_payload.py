from app.main import quoted_id, text_from_message


def test_parses_real_evolution_conversation_reply() -> None:
    payload = {
        "message": {"conversation": "Listo"},
        "contextInfo": {
            "stanzaId": "3EB0276F266DB0A3879FE2",
            "quotedMessage": {"conversation": "hola buenos dias"},
        },
    }
    assert text_from_message(payload) == "Listo"
    assert quoted_id(payload) == "3EB0276F266DB0A3879FE2"
