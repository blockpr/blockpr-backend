from quart import Blueprint, request, jsonify
from uuid import uuid4, UUID
import json

from app.services.hash_service import calculate_pdf_hash
from app.config.database import get_db_pool
from app.models.certificate import Certificate
from app.utils.jwt_utils import require_auth

bp = Blueprint("certificates", __name__, url_prefix="/certificates")


@bp.route("/hash", methods=["POST"])
@require_auth
async def create_certificate_hash():
    """
    Endpoint para calcular el hash SHA-256 de un PDF y guardarlo en la base de datos.
    
    Este endpoint forma parte del flujo del sistema:
    1. PDF generado
    2. Calcular SHA-256
    3. Guardar hash en la base de datos
    4. (Posteriormente) Incluir el certificado en un batch
    5. (Posteriormente) Registrar el Merkle root en blockchain
    
    Response:
        {
            "success": true,
            "certificate": {
                "id": "uuid",
                "user_id": "uuid",
                "document_hash": "sha256_hash",
                "external_id": "optional",
                "certificate_type": "optional",
                "created_at": "iso_datetime"
            }
        }
    """
    try:
        import inspect
        files = request.files
        if inspect.iscoroutine(files):
            files = await files
        
        pdf_file = files.get("pdf") or files.get("file") or files.get("document")
        
        if not pdf_file:
            return jsonify({
                "success": False,
                "error": "No se encontró ningún archivo. Envía el PDF en el campo 'pdf', 'file' o 'document'"
            }), 400
        
        pdf_file.stream.seek(0) 
        pdf_bytes = pdf_file.read()
        
        if not pdf_bytes:
            return jsonify({
                "success": False,
                "error": "El archivo está vacío"
            }), 400
        
        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({
                "success": False,
                "error": "El archivo no parece ser un PDF válido (debe empezar con %PDF)"
            }), 400
        
        hash_value = calculate_pdf_hash(pdf_bytes)
        
        form_data = await request.form
        external_id = form_data.get("external_id")
        certificate_type = form_data.get("certificate_type")
        
        metadata = None
        metadata_str = form_data.get("metadata")
        if metadata_str:
            try:
                metadata = json.loads(metadata_str)
            except json.JSONDecodeError:
                return jsonify({
                    "success": False,
                    "error": "El campo 'metadata' debe ser un JSON válido"
                }), 400
        
        user_id = UUID(request.user_id)
        
        pool = get_db_pool()
        async with pool.acquire() as conn:
            certificate_id = uuid4()
            
            row = await conn.fetchrow(
                """
                INSERT INTO certificates (
                    id, user_id, external_id, certificate_type, document_hash,
                    metadata, batch_id, merkle_proof, blockchain_tx_id,
                    verification_url
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, NULL, NULL, NULL,
                    NULL
                ) RETURNING *
                """,
                certificate_id, user_id, external_id, certificate_type, hash_value,
                metadata
            )
            
            certificate = Certificate.from_dict(dict(row))
        
        return jsonify({
            "success": True,
            "certificate": certificate.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error al procesar el archivo: {str(e)}"
        }), 500
