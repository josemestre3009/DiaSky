from app.processing import extract_customer_details, extract_order, individual_record


def test_recognizes_ip_only_service_report() -> None:
    text = "✅ CONEJO\nMIGUEL ANGEL ZABALETA FONSECA\n192.168.85.52 no se conecta a la red"
    assert individual_record(text)
    assert extract_order(text)[0] == "revision"


def test_extracts_operation_types() -> None:
    assert extract_order("Cambiar ONU 5G Conejo")[0] == "cambio_onu"
    assert extract_order("Instalar IPTV en La Junta")[0] == "instalacion_iptv"
    assert extract_order("Fibra partida requiere reparación")[0] == "reparacion_fibra"


def test_extracts_customer_details() -> None:
    details = extract_customer_details("""✅ CONEJO
YEIMI MISHELL EPIAYU SOLANO
1120741529
CALLE 5 CARRERA 1A-9 CONEJO
3148528180
3206836286
epiayuyeimi671@gmail.com
Plan 50 MG $50.000
Valor instalacion $50.000""")
    assert details["customer_document"] == "1120741529"
    assert details["address"] == "CALLE 5 CARRERA 1A-9 CONEJO"
    assert details["phones"] == ["3148528180", "3206836286"]
    assert details["email"] == "epiayuyeimi671@gmail.com"
