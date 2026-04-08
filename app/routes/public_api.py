from quart import Blueprint, request, jsonify
from uuid import uuid4, UUID
import json
import os
import inspect

from app.services.hash_service import calculate_pdf_hash
from app.services.solana_service import get_solana_service
from app.config.database import get_db_pool
from app.models.certificate import Certificate
from app.services.api_key_service import validate_api_key
from app.utils.api_key_auth import require_api_key
from app.utils.certificate_emission import (
    merge_emission_metadata,
    build_certificate_verification_url,
)

bp = Blueprint("public_api", __name__, url_prefix="/public")


@bp.route("/certificates/<certificate_id>", methods=["GET"])
async def get_public_certificate(certificate_id: str):
    """
    Consulta pública de una emisión por ID (sin API key).
    No expone user_id ni datos sensibles del usuario más allá del nombre de empresa emisora.
    """
    try:
        cert_uuid = UUID(certificate_id)
    except ValueError:
        return jsonify({"error": "not_found"}), 404

    pool = get_db_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                c.id,
                c.external_id,
                c.certificate_type,
                c.document_hash,
                c.metadata,
                c.verification_url,
                c.created_at,
                u.company_name AS issuer_company_name,
                bt.tx_hash AS transaction_signature,
                bt.explorer_url,
                bt.blockchain,
                bt.network,
                bt.status AS blockchain_status,
                bt.confirmed_at
            FROM certificates c
            INNER JOIN users u ON u.id = c.user_id
            LEFT JOIN blockchain_transactions bt ON bt.id = c.blockchain_tx_id
            WHERE c.id = $1
            """,
            cert_uuid,
        )

    if not row:
        return jsonify({"error": "not_found"}), 404

    metadata = row["metadata"]
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except json.JSONDecodeError:
            metadata = None

    return jsonify(
        {
            "certificate": {
                "id": str(row["id"]),
                "external_id": row["external_id"],
                "certificate_type": row["certificate_type"],
                "document_hash": row["document_hash"],
                "metadata": metadata,
                "verification_url": row["verification_url"],
                "created_at": row["created_at"].isoformat(),
            },
            "issuer": {
                "company_name": row["issuer_company_name"] or "",
            },
            "blockchain": {
                "transaction_signature": row["transaction_signature"],
                "explorer_url": row["explorer_url"],
                "blockchain": row["blockchain"],
                "network": row["network"],
                "status": row["blockchain_status"],
                "confirmed_at": row["confirmed_at"].isoformat() if row["confirmed_at"] else None,
            },
        }
    ), 200


@bp.route("/certificates/list", methods=["POST"])
async def list_certificates():
    """Lista certificados del usuario asociado a la API key enviada en body."""
    data = await request.get_json(silent=True) or {}
    print(data)
    api_key = data.get("api_key")
    if not api_key:
        return jsonify({"error": "api_key is required"}), 400

    result = await validate_api_key(api_key)
    if not result:
        return jsonify({"error": "Invalid API key"}), 401

    user_id, _api_key_id = result

    pool = get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                c.id,
                c.external_id,
                c.certificate_type,
                c.document_hash,
                c.metadata,
                c.verification_url,
                c.created_at,
                u.company_name AS issuer_company_name,
                bt.tx_hash AS transaction_signature,
                bt.explorer_url,
                bt.blockchain,
                bt.network,
                bt.status AS blockchain_status,
                bt.confirmed_at
            FROM certificates c
            INNER JOIN users u ON u.id = c.user_id
            LEFT JOIN blockchain_transactions bt ON bt.id = c.blockchain_tx_id
            WHERE c.user_id = $1
            ORDER BY c.created_at DESC
            """,
            user_id,
        )

    results = []
    for row in rows:
        metadata = row["metadata"]
        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                metadata = None

        results.append(
            {
                "certificate": {
                    "id": str(row["id"]),
                    "external_id": row["external_id"],
                    "certificate_type": row["certificate_type"],
                    "document_hash": row["document_hash"],
                    "metadata": metadata,
                    "verification_url": row["verification_url"],
                    "created_at": row["created_at"].isoformat(),
                },
                "issuer": {
                    "company_name": row["issuer_company_name"] or "",
                },
                "blockchain": {
                    "transaction_signature": row["transaction_signature"],
                    "explorer_url": row["explorer_url"],
                    "blockchain": row["blockchain"],
                    "network": row["network"],
                    "status": row["blockchain_status"],
                    "confirmed_at": row["confirmed_at"].isoformat() if row["confirmed_at"] else None,
                },
            }
        )

    return jsonify({"certificates": results}), 200


@bp.route("/certificates/hash", methods=["POST"])
@require_api_key
async def create_certificate_hash():
    """
    Endpoint público para calcular el hash SHA-256 de un PDF, registrarlo en Solana y guardarlo en la base de datos.
    Requiere autenticación por API key.
    
    Este endpoint es equivalente a /certificates/hash pero usa API key en lugar de JWT.
    """
    try:
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
        form_dict = dict(form_data)
        external_id = form_dict.get("external_id")
        if external_id is not None and isinstance(external_id, str):
            external_id = external_id.strip() or None
        if not external_id:
            id_ext = form_dict.get("identificador_externo")
            if id_ext is not None and str(id_ext).strip():
                external_id = str(id_ext).strip()

        certificate_type = form_dict.get("certificate_type")
        if certificate_type is not None and isinstance(certificate_type, str):
            certificate_type = certificate_type.strip() or None

        metadata_from_json = None
        metadata_str = form_dict.get("metadata")
        if metadata_str:
            try:
                metadata_from_json = json.loads(metadata_str)
                if not isinstance(metadata_from_json, dict):
                    return jsonify({
                        "success": False,
                        "error": "El campo 'metadata' debe ser un objeto JSON"
                    }), 400
            except json.JSONDecodeError:
                return jsonify({
                    "success": False,
                    "error": "El campo 'metadata' debe ser un JSON válido"
                }), 400

        metadata = merge_emission_metadata(form_dict, metadata_from_json)
        
        # Obtener user_id del API key autenticado
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
        
        # Guardar en base de datos
        pool = get_db_pool()
        async with pool.acquire() as conn:
            certificate_id = uuid4()
            verification_url = build_certificate_verification_url(certificate_id)
            blockchain_tx_id = None
            
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
                    uuid4(),
                    "solana",
                    network,
                    transaction_signature,
                    explorer_url,
                    tx_status
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
                blockchain_tx_id,
                verification_url
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
            "verification_url": certificate.verification_url,
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
