from quart import Blueprint, request, jsonify
from uuid import uuid4, UUID
import json
import os

from app.services.hash_service import calculate_pdf_hash
from app.services.solana_service import get_solana_service
from app.config.database import get_db_pool
from app.models.certificate import Certificate
from app.utils.jwt_utils import require_auth

bp = Blueprint("certificates", __name__, url_prefix="/certificates")


@bp.route("/hash", methods=["POST"])
@require_auth
async def create_certificate_hash():
    """
    Endpoint para calcular el hash SHA-256 de un PDF, registrarlo en Solana y guardarlo en la base de datos.
    
    Este endpoint forma parte del flujo del sistema:
    1. PDF generado
    2. Calcular SHA-256
    3. Registrar hash en Solana usando programa Memo
    4. Guardar hash y transacción en la base de datos
    
    Response:
        {
            "success": true,
            "hash": "sha256_hash",
            "transaction_signature": "solana_tx_signature",
            "explorer_url": "https://solscan.io/tx/...",
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
        
        # Obtener user_id del token autenticado
        user_id = UUID(request.user_id)
        
        # Registrar hash en Solana
        transaction_signature = None
        explorer_url = None
        solana_error = None
        solana_result = None
        
        try:
            solana_service = get_solana_service()
            solana_result = await solana_service.register_hash(hash_value)
            transaction_signature = solana_result["signature"]
            explorer_url = solana_result["explorer_url"]
        except Exception as e:
            # Guardar el error pero continuar con el guardado en BD
            solana_error = str(e)
            # No retornamos error aquí, solo lo registramos para que el usuario sepa
        
        # Guardar en base de datos
        pool = get_db_pool()
        async with pool.acquire() as conn:
            certificate_id = uuid4()
            blockchain_tx_id = None
            
            # Actualizar metadata para incluir información de Solana
            if metadata is None:
                metadata = {}
            
            # Si hay transacción de Solana, crear registro en blockchain_transactions
            if transaction_signature and solana_result:
                network = os.getenv("SOLANA_NETWORK", "mainnet")
                tx_status = solana_result.get("status", "confirmed")
                
                # Crear registro en blockchain_transactions
                # Para transacciones individuales, batch_id es NULL
                blockchain_tx_row = await conn.fetchrow(
                    """
                    INSERT INTO blockchain_transactions (
                        id, batch_id, blockchain, network, tx_hash,
                        explorer_url, status, created_at, confirmed_at
                    ) VALUES (
                        $1, NULL, $2, $3, $4,
                        $5, $6, NOW(), CASE WHEN $6 = 'confirmed' THEN NOW() ELSE NULL END
                    ) RETURNING id
                    """,
                    uuid4(),              # id de blockchain_transaction
                    "solana",             # blockchain
                    network,              # network
                    transaction_signature, # tx_hash
                    explorer_url,         # explorer_url
                    tx_status             # status
                )
                blockchain_tx_id = blockchain_tx_row["id"]
                
                metadata["solana_transaction"] = {
                    "signature": transaction_signature,
                    "explorer_url": explorer_url,
                    "status": tx_status
                }
            if solana_error:
                metadata["solana_error"] = solana_error
            
            row = await conn.fetchrow(
                """
                INSERT INTO certificates (
                    id, user_id, external_id, certificate_type, document_hash,
                    metadata, batch_id, merkle_proof, blockchain_tx_id,
                    verification_url
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, NULL, NULL, $7,
                    $8
                ) RETURNING *
                """,
                certificate_id, user_id, external_id, certificate_type, hash_value,
                json.dumps(metadata) if metadata else None,
                blockchain_tx_id,  # blockchain_tx_id
                explorer_url  # Guardar explorer_url en verification_url
            )
            
            certificate = Certificate.from_dict(dict(row))
        
        # Construir respuesta según formato esperado
        if not transaction_signature:
            # Si falla Solana, devolver error pero con hash calculado
            return jsonify({
                "success": False,
                "hash": hash_value,
                "error": f"No se pudo registrar en Solana: {solana_error}",
                "transaction_signature": None,
                "explorer_url": None
            }), 500
        
        # Respuesta exitosa
        response = {
            "success": True,
            "hash": hash_value,
            "transaction_signature": transaction_signature,
            "explorer_url": explorer_url,
            "certificate": certificate.to_dict()
        }
        
        return jsonify(response), 201
        
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


@bp.route("", methods=["GET"])
@require_auth
async def list_certificates():
    """
    Lista todas las emisiones del usuario autenticado, con datos de la transacción blockchain.

    Query params:
        page (int): Página (default 1)
        limit (int): Resultados por página (default 20, max 100)

    Response:
        {
            "success": true,
            "data": [...],
            "pagination": { "page": 1, "limit": 20, "total": 50, "pages": 3 }
        }
    """
    try:
        user_id = UUID(request.user_id)

        page = max(1, int(request.args.get("page", 1)))
        limit = min(100, max(1, int(request.args.get("limit", 20))))
        offset = (page - 1) * limit

        pool = get_db_pool()
        async with pool.acquire() as conn:
            total = await conn.fetchval(
                "SELECT COUNT(*) FROM certificates WHERE user_id = $1",
                user_id
            )

            rows = await conn.fetch(
                """
                SELECT
                    c.id,
                    c.user_id,
                    c.external_id,
                    c.certificate_type,
                    c.document_hash,
                    c.verification_url,
                    c.created_at,
                    bt.tx_hash        AS transaction_signature,
                    bt.explorer_url,
                    bt.blockchain,
                    bt.network,
                    bt.status         AS blockchain_status,
                    bt.confirmed_at
                FROM certificates c
                LEFT JOIN blockchain_transactions bt ON bt.id = c.blockchain_tx_id
                WHERE c.user_id = $1
                ORDER BY c.created_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_id, limit, offset
            )

        data = []
        for row in rows:
            data.append({
                "id": str(row["id"]),
                "external_id": row["external_id"],
                "certificate_type": row["certificate_type"],
                "document_hash": row["document_hash"],
                "created_at": row["created_at"].isoformat(),
                "blockchain": {
                    "transaction_signature": row["transaction_signature"],
                    "explorer_url": row["explorer_url"] or row["verification_url"],
                    "blockchain": row["blockchain"],
                    "network": row["network"],
                    "status": row["blockchain_status"],
                    "confirmed_at": row["confirmed_at"].isoformat() if row["confirmed_at"] else None,
                }
            })

        pages = (total + limit - 1) // limit

        return jsonify({
            "success": True,
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": pages,
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
