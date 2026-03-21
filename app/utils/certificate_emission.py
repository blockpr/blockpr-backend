import os
from typing import Any, Dict, Optional
from uuid import UUID

# Campos de formulario que se guardan dentro de metadata (además del JSON "metadata").
EMISSION_METADATA_FORM_KEYS = frozenset(
    {
        "nombre",
        "apellido",
        "patente",
        "identificador_externo",
        "dni",
        "documento",
        "email",
        "telefono",
        "telefono_movil",
        "domicilio",
        "localidad",
        "provincia",
        "pais",
    }
)


def merge_emission_metadata(
    form_values: Dict[str, Any],
    metadata_from_json: Optional[dict],
) -> dict:
    """
    Combina el JSON `metadata` con campos de formulario estructurados.
    Los valores del formulario no vacíos pisan claves existentes en metadata.
    """
    out: dict = {}
    if metadata_from_json and isinstance(metadata_from_json, dict):
        out.update(metadata_from_json)

    for key in EMISSION_METADATA_FORM_KEYS:
        raw = form_values.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            val = raw.strip()
            if val:
                out[key] = val
        else:
            out[key] = raw

    return out


def build_certificate_verification_url(certificate_id: UUID) -> str:
    """
    URL pública de verificación en el sitio (frontend).
    PUBLIC_APP_URL tiene prioridad; si no existe, FRONTEND_URL.
    CERTIFICATE_VERIFICATION_PATH usa {id} como placeholder del UUID del certificado.
    """
    base = os.getenv("PUBLIC_APP_URL") or os.getenv("FRONTEND_URL", "http://localhost:3000")
    base = base.rstrip("/")
    path = os.getenv("CERTIFICATE_VERIFICATION_PATH", "/verify/{id}")
    path = path.format(id=certificate_id)
    if not path.startswith("/"):
        path = "/" + path
    return f"{base}{path}"
