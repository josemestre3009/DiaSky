from app.models import OrderStatus
from app.processing import classify, redact


def test_classifies_customer_absence() -> None:
    result = classify("No hay nadie en la casa")
    assert result.status == OrderStatus.PENDIENTE
    assert result.reason_code == "CLIENTE_AUSENTE"


def test_classifies_completion() -> None:
    assert classify("listo se le cambio el cable").status == OrderStatus.COMPLETADA


def test_classifies_technical_closures_without_listo() -> None:
    for text in ("Se cambio ONU 5G", "Se retiró el equipo", "Se reparó la fibra", "Quedó funcionando el servicio"):
        assert classify(text).status == OrderStatus.COMPLETADA


def test_classifies_temporary_access_blocker_as_pending() -> None:
    result = classify("No se pudo porque sin el marido no dejaba entrar")
    assert result.status == OrderStatus.PENDIENTE
    assert result.reason_code == "ACCESO_NO_AUTORIZADO"


def test_classifies_recurring_operational_blockers() -> None:
    cases = {
        "No hay adulto, solo hay un niño menor": "MENOR_SIN_ADULTO",
        "Está relampagueando mucho": "CLIMA",
        "No hay cupo disponible, toca llevar otro hilo": "SIN_CUPO",
        "No tienen la plata para la instalación": "PAGO_PENDIENTE",
        "Los trabajadores están haciendo las aceras y no permiten intervenir": "OBRA_EXTERNA",
        "La fibra está energizada con electricidad de alta": "RIESGO_SEGURIDAD",
        "No tenemos fusionadora para realizar más pruebas": "MATERIAL_FALTANTE",
    }
    for text, reason_code in cases.items():
        result = classify(text)
        assert result.status == OrderStatus.PENDIENTE
        assert result.reason_code == reason_code


def test_classifies_partial_completion() -> None:
    result = classify("Se le cambió la ONU, no se pudo dejar la IPTV y queda pendiente")
    assert result.status == OrderStatus.COMPLETADA_PARCIAL


def test_redacts_sensitive_values() -> None:
    safe = redact("IP 192.168.1.20 https://example.com 3001234567 a@b.com")
    assert "192.168" not in safe
    assert "example.com" not in safe
    assert "3001234567" not in safe
    assert "a@b.com" not in safe
