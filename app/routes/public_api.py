from quart import Blueprint, request, jsonify
from uuid import uuid4, UUID
import json
import os
import inspect

from app.services.hash_service import calculate_pdf_hash
from app.services.solana_service import get_solana_service
from app.config.database import get_db_pool
from app.models.certificate import Certificate
from app.services.certificate_verification_service import verify_certificate_by_hash
from app.utils.api_key_auth import require_api_key

bp = Blueprint("public_api", __name__, url_prefix="/public")


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
            blockchain_tx_id = None
            
            # Actualizar metadata para incluir información de Solana
            if metadata is None:
                metadata = {}
            
            # Si hay transacción de Solana, crear registro en blockchain_transactions
            if transaction_signature and solana_result:
                network = os.getenv("SOLANA_NETWORK", "mainnet")
                tx_status = solana_result.get("status", "confirmed")
                
                # Crear registro en blockchain_transactions
                blockchain_tx_row = await conn.fetchrow(
                    """
                    INSERT INTO blockchain_transactions (
                        id, batch_id, blockchain, network, tx_hash,
                        explorer_url, status, created_at, confirmed_at
                    ) VALUES (
                        $1, $2, $3, $4, $5,
                        $6, $7, NOW(), CASE WHEN $7 = 'confirmed' THEN NOW() ELSE NULL END
                    ) RETURNING id
                    """,
                    uuid4(),
                    certificate_id,
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
                explorer_url
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


@bp.route("/certificates/verify", methods=["POST"])
@require_api_key
async def verify_certificate():
    """
    Endpoint público para validar un certificado subiendo un archivo PDF.
    Calcula el hash del archivo y verifica si existe en la base de datos,
    retornando información del certificado y su transacción blockchain asociada.
    
    Requiere autenticación por API key.
    """
    try:
        files = request.files
        if inspect.iscoroutine(files):
            files = await files
        
        pdf_file = files.get("pdf") or files.get("file") or files.get("document")
        
        if not pdf_file:
            return jsonify({
                "valid": False,
                "error": "No se encontró ningún archivo. Envía el PDF en el campo 'pdf', 'file' o 'document'"
            }), 400
        
        pdf_file.stream.seek(0)
        pdf_bytes = pdf_file.read()
        
        if not pdf_bytes:
            return jsonify({
                "valid": False,
                "error": "El archivo está vacío"
            }), 400
        
        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({
                "valid": False,
                "error": "El archivo no parece ser un PDF válido (debe empezar con %PDF)"
            }), 400
        
        # Calcular hash SHA-256 del archivo
        document_hash = calculate_pdf_hash(pdf_bytes)
        
        # Verificar si el certificado existe
        verification_result = await verify_certificate_by_hash(document_hash)
        
        if not verification_result:
            return jsonify({
                "valid": False,
                "message": "Certificate not found",
                "document_hash": document_hash
            }), 200
        
        certificate = verification_result["certificate"]
        blockchain_transaction = verification_result["blockchain_transaction"]
        
        # Construir respuesta
        response = {
            "valid": True,
            "certificate": certificate,
        }
        
        if blockchain_transaction:
            response["blockchain_transaction"] = blockchain_transaction
        else:
            response["blockchain_transaction"] = None
            response["message"] = "Certificate found but not registered on blockchain"
        
        return jsonify(response), 200
        
    except ValueError as e:
        return jsonify({
            "valid": False,
            "error": str(e)
        }), 400
    except Exception as e:
        return jsonify({
            "valid": False,
            "error": f"Error al procesar el archivo: {str(e)}"
        }), 500
