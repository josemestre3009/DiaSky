import re
import json
import logging
from dataclasses import dataclass

import httpx

from app.config import settings

from app.models import OrderStatus

logger = logging.getLogger("diasky.openrouter")

SENSITIVE = re.compile(r"https?://\S+|\b\d{7,}\b|[\w.+-]+@[\w.-]+|\b(?:\d{1,3}\.){3}\d{1,3}\b", re.I)
REASON_CODES = (
    "CLIENTE_AUSENTE", "MENOR_SIN_ADULTO", "ACCESO_NO_AUTORIZADO", "SIN_ENERGIA",
    "CLIMA", "SIN_CUPO", "PAGO_PENDIENTE", "REPROGRAMACION", "MATERIAL_FALTANTE",
    "OBRA_EXTERNA", "RIESGO_SEGURIDAD", "CLIENTE_CANCELO", "OTRO",
)
PENDING_REASON_CODES = set(REASON_CODES) - {"CLIENTE_CANCELO", "OTRO"}


@dataclass
class Classification:
    status: OrderStatus
    reason_code: str | None = None
    reason_text: str | None = None
    confidence: float = 1.0
    source: str = "rule"


def redact(text: str) -> str:
    return SENSITIVE.sub("[REDACTED]", text)


def classify(text: str) -> Classification:
    normalized = " ".join(text.lower().split())
    if re.search(r"queda pendiente.*(iptv|onu|router|cable)|no se pudo dejar.*(iptv|onu|router|cable)", normalized):
        return Classification(OrderStatus.COMPLETADA_PARCIAL, "MATERIAL_FALTANTE", "La actividad principal se realizó; queda un componente pendiente.")
    if re.search(r"\b(listo|se le instal[oó]|se (le )?retir[oaó]|se (le )?cambi[aoó]|se restablec|se repar[oó]|se solucion[oó]|qued[oó] (funcionando|trabajando|con servicio)|servicio restablecido)\b", normalized):
        return Classification(OrderStatus.COMPLETADA)
    if re.search(r"no hay adulto|solo (esta|hay) (un |el )?(ni[nñ]o|menor)|menores de edad", normalized):
        return Classification(OrderStatus.PENDIENTE, "MENOR_SIN_ADULTO", "No había un adulto responsable para autorizar la operación.")
    if re.search(r"no hay nadie|no se encuentra nadie|no contesta", normalized):
        return Classification(OrderStatus.PENDIENTE, "CLIENTE_AUSENTE", "Cliente no disponible en el lugar.")
    if re.search(r"no hay luz|no hay energia|sin energ[ií]a", normalized):
        return Classification(OrderStatus.PENDIENTE, "SIN_ENERGIA", "No hay energía disponible para realizar la operación.")
    if re.search(r"lluvia|relampague|tormenta", normalized):
        return Classification(OrderStatus.PENDIENTE, "CLIMA", "Condiciones climáticas impiden realizar la operación con seguridad.")
    if re.search(r"no hay cupo|llevar otro hilo|otra caja", normalized):
        return Classification(OrderStatus.PENDIENTE, "SIN_CUPO", "No hay capacidad de red disponible; requiere ampliación técnica.")
    if re.search(r"no tienen la plata|no tiene(n)? dinero|pago pendiente|esperando.*pagar", normalized):
        return Classification(OrderStatus.PENDIENTE, "PAGO_PENDIENTE", "Pago pendiente para continuar con la operación.")
    if re.search(r"aceras|trabajadores.*no permiten|afinia.*trabajando|obra", normalized):
        return Classification(OrderStatus.PENDIENTE, "OBRA_EXTERNA", "Obras externas impiden intervenir hasta que el área esté disponible.")
    if re.search(r"energisa|alta tensi[oó]n|electricidad.*alta|riesgo", normalized):
        return Classification(OrderStatus.PENDIENTE, "RIESGO_SEGURIDAD", "Existe un riesgo de seguridad que requiere control antes de intervenir.")
    if re.search(r"no tenemos.*(material|fusionadora)|falta.*(material|equipo|cable|router|poe)", normalized):
        return Classification(OrderStatus.PENDIENTE, "MATERIAL_FALTANTE", "Faltan materiales o equipos para terminar la operación.")
    if re.search(r"no (deja|dejaba|permiten|autoriza).*entrar|sin (el |la )?(marido|esposa|propietari[oa])|(marido|esposa|propietari[oa]).{0,80}no.{0,30}(deja|dejaba|permiten|autoriza).{0,30}entrar", normalized):
        return Classification(OrderStatus.PENDIENTE, "ACCESO_NO_AUTORIZADO", "No se autorizó el acceso; requiere coordinación con la persona responsable.")
    if re.search(r"queda pendiente|para ma[nñ]ana|despu[eé]s de", normalized):
        return Classification(OrderStatus.PENDIENTE, "REPROGRAMACION", redact(text))
    if re.search(r"no quiere|cancel", normalized):
        return Classification(OrderStatus.CANCELADA, "CLIENTE_CANCELO", "El cliente canceló o rechazó la operación.")
    if re.search(r"no es posible", normalized):
        return Classification(OrderStatus.FALLIDA, "OTRO", redact(text))
    if re.search(r"vamos|ya estamos|para all[aá]", normalized):
        return Classification(OrderStatus.EN_PROGRESO)
    return Classification(OrderStatus.REQUIERE_REVISION, "OTRO", None, 0.0, "review")


def classify_with_openrouter(text: str) -> Classification:
    config = settings()
    if not config.openrouter_api_key:
        return classify(text)
    safe_text = redact(text)
    schema = {"type": "object", "properties": {
        "status": {"type": "string", "enum": [s.value for s in OrderStatus if s not in {OrderStatus.REQUIERE_REVISION}]},
        "reason_code": {"type": ["string", "null"], "enum": [*REASON_CODES, None]},
        "reason_text": {"type": ["string", "null"]},
        "confidence": {"type": "number"},
    }, "required": ["status", "reason_code", "reason_text", "confidence"], "additionalProperties": False}
    payload = {"model": config.openrouter_model, "response_format": {"type": "json_schema", "json_schema": {"name": "operation", "strict": True, "schema": schema}},
               "messages": [{"role": "system", "content": "Classify this redacted Colombian telecom operation update. Temporary access, availability, permission, weather, or payment blockers are pendiente, not fallida. Use CLIENTE_AUSENTE for customer unavailable; MENOR_SIN_ADULTO for no responsible adult; ACCESO_NO_AUTORIZADO for denied permission; SIN_ENERGIA for power outage; CLIMA for weather; SIN_CUPO for network capacity; PAGO_PENDIENTE for payment; REPROGRAMACION for scheduling; MATERIAL_FALTANTE for missing equipment; OBRA_EXTERNA for construction or utility works; RIESGO_SEGURIDAD for electrical or physical danger; CLIENTE_CANCELO only when customer cancels; OTRO otherwise. reason_text must be one short factual Spanish sentence without PII."}, {"role": "user", "content": safe_text}]}
    try:
        response = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers={"Authorization": f"Bearer {config.openrouter_api_key}"}, json=payload, timeout=15)
        response.raise_for_status()
        result = json.loads(response.json()["choices"][0]["message"]["content"])
        confidence = float(result["confidence"])
        if confidence < config.openrouter_min_confidence:
            raise ValueError("low confidence")
        reason_code = result["reason_code"]
        status = OrderStatus(result["status"])
        # Model output cannot turn a temporary blocker into a definitive failure.
        if reason_code in PENDING_REASON_CODES:
            status = OrderStatus.PENDIENTE
        if reason_code == "CLIENTE_CANCELO":
            status = OrderStatus.CANCELADA
        return Classification(status, reason_code, result["reason_text"], confidence, "openrouter")
    except httpx.HTTPStatusError as error:
        logger.warning("OpenRouter classification unavailable: HTTP %s", error.response.status_code)
        return Classification(OrderStatus.REQUIERE_REVISION, "OTRO", None, 0.0, "review")
    except (httpx.HTTPError, KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        logger.warning("OpenRouter classification unavailable: %s", type(error).__name__)
        return Classification(OrderStatus.REQUIERE_REVISION, "OTRO", None, 0.0, "review")


def individual_record(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    has_operation = bool(re.search(r"instal|retir|traslado|revisi[oó]n|onu|iptv|falla", text, re.I))
    has_ip = bool(re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text))
    has_identifier = bool(re.search(r"\b\d{7,}\b", text)) or has_ip
    has_record_shape = bool(re.match(r"^\s*✅\s*[^\n]+\n[^\n]{4,}", text))
    # Field reports commonly contain only client, IP, and a service symptom.
    has_symptom = bool(re.search(r"no se conect|sin internet|no enciende|navegaci[oó]n lenta|cable", text, re.I))
    # Authorized coordinators use an individual record format; accept it even when
    # the activity wording is new, while still requiring a customer/IP identifier.
    return (has_operation or has_record_shape or (has_ip and has_symptom)) and has_identifier and len(lines) >= 2


def extract_order(text: str) -> tuple[str, str | None, str | None]:
    lowered = text.lower()
    operation = next((kind for kind in ("instalacion_iptv", "cambio_onu", "reparacion_fibra", "incidencia_nodo", "instalacion", "retiro", "traslado", "revision", "mejora") if kind.replace("_", " ") in lowered), "operacion")
    if "iptv" in lowered and "instal" in lowered:
        operation = "instalacion_iptv"
    elif re.search(r"cambio.*onu|onu.*5g", lowered):
        operation = "cambio_onu"
    elif re.search(r"fibra.*(partida|ca[ií]da|repar)|repar.*fibra", lowered):
        operation = "reparacion_fibra"
    elif "nodo" in lowered:
        operation = "incidencia_nodo"
    elif re.search(r"\bretir", lowered):
        operation = "retiro"
    if operation == "operacion" and re.search(r"no se conect|sin internet|no enciende|navegaci[oó]n lenta|cable", lowered):
        operation = "revision"
    locality = None
    match = re.search(r"(?:✅\s*)?([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]{2,})", text)
    if match:
        locality = match.group(1).strip()
    names = [line.strip() for line in text.splitlines() if re.fullmatch(r"[A-ZÁÉÍÓÚÑ ]{6,}", line.strip())]
    return operation, locality, names[0] if names else None


def extract_customer_details(text: str) -> dict[str, object]:
    lines = [" ".join(line.split()) for line in text.splitlines() if line.strip()]
    email_match = re.search(r"[\w.+-]+@[\w.-]+", text)
    document = next((line for line in lines if re.fullmatch(r"\d{6,12}", line.replace(" ", ""))), None)
    phones = list(dict.fromkeys(re.findall(r"(?<!\d)(?:\d[ -]?){10}(?!\d)", text)))
    address = next((line for line in lines if re.search(r"\b(calle|carrera|manzana|casa|diagonal|transversal|lote)\b", line, re.I)), None)
    plan = next((line for line in lines if re.search(r"\bplan\b", line, re.I)), None)
    installation_value = next((line for line in lines if re.search(r"valor\s*(de )?instal", line, re.I)), None)
    document = document.replace(" ", "") if document else None
    normalized_phones = [re.sub(r"\D", "", phone) for phone in phones]
    return {"customer_document": document, "address": address,
            "phones": [phone for phone in normalized_phones if phone != document], "email": email_match.group(0) if email_match else None,
            "plan": plan, "installation_value": installation_value}


def availability(text: str) -> tuple[str | None, bool]:
    normalized = " ".join(text.lower().split())
    if re.search(r"avisa|no est[aá] disponible|sal[ií]o de viaje|hospitaliz|permiso", normalized):
        return redact(text), True
    if re.search(r"disponible.*(despu[eé]s|tarde|ma[nñ]ana|s[aá]bado|domingo)|despu[eé]s de \d", normalized):
        return redact(text), False
    return None, False


def assigned_names(text: str) -> list[str]:
    lowered = text.lower()
    if not re.search(r"para que vayan|para ir|vamos (para|con)|pasa.*datos", lowered):
        return []
    known = ("wilson", "carlos", "oscar", "ever", "yeison", "mauricio", "palomino")
    return [name.title() for name in known if re.search(rf"\b{name}\b", lowered)]
