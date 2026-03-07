from quart import Blueprint, request, jsonify
from app.services.hash_service import calculate_pdf_hash

bp = Blueprint("hash_test", __name__)


@bp.route("/test/hash-pdf", methods=["POST"])
async def test_hash_pdf():
    """
    Endpoint de prueba para calcular el hash SHA-256 de un PDF.
    
    Recibe un archivo PDF mediante multipart/form-data y devuelve su hash.
    
    Request:
        - Method: POST
        - Content-Type: multipart/form-data
        - Body: archivo PDF en el campo 'pdf' o 'file'
    
    Response:
        {
            "success": true,
            "hash": "9f2c7a8e1e8d0a3c5cdbb9d6c3d6e9bcb84f6f2c3c4f1e0d3b3e2b1a0c9d8e7",
            "file_size": 12345
        }
    
    Example using curl:
        curl -X POST http://localhost:5000/test/hash-pdf \
             -F "pdf=@certificado.pdf"
    """
    try:
        # Obtener el archivo del request
        files = await request.files
        
        # Intentar obtener el archivo con diferentes nombres de campo comunes
        pdf_file = files.get("pdf") or files.get("file") or files.get("document")
        
        if not pdf_file:
            return jsonify({
                "success": False,
                "error": "No se encontró ningún archivo. Envía el PDF en el campo 'pdf', 'file' o 'document'"
            }), 400
        
        # Leer el contenido del archivo
        pdf_bytes = await pdf_file.read()
        
        if not pdf_bytes:
            return jsonify({
                "success": False,
                "error": "El archivo está vacío"
            }), 400
        
        # Verificar que sea un PDF (básico: debe empezar con %PDF)
        if not pdf_bytes.startswith(b"%PDF"):
            return jsonify({
                "success": False,
                "error": "El archivo no parece ser un PDF válido (debe empezar con %PDF)"
            }), 400
        
        # Calcular el hash
        hash_value = calculate_pdf_hash(pdf_bytes)
        
        return jsonify({
            "success": True,
            "hash": hash_value,
            "file_size": len(pdf_bytes),
            "filename": pdf_file.filename
        }), 200
        
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
