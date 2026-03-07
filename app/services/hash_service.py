"""
Servicio para calcular hashes criptográficos de documentos PDF.

Este módulo proporciona funciones para calcular hashes SHA-256 de archivos PDF
de manera determinística y eficiente, garantizando la integridad de los certificados.
"""
import hashlib
from typing import Union, BinaryIO
import io


def calculate_pdf_hash(pdf_data: Union[bytes, BinaryIO, io.BytesIO]) -> str:
    """
    Calcula el hash SHA-256 de un documento PDF.
    
    Esta función calcula el hash sobre los bytes exactos del archivo PDF,
    garantizando que el mismo PDF siempre genere el mismo hash (determinístico).
    El hash se calcula directamente sobre el contenido binario, sin procesar
    texto ni metadata externa.
    
    Args:
        pdf_data: Los bytes del PDF o un objeto file-like (stream) que contenga
                  el contenido binario del PDF. Puede ser:
                  - bytes: contenido del PDF como bytes
                  - BinaryIO: objeto file abierto en modo binario
                  - io.BytesIO: buffer de bytes en memoria
    
    Returns:
        str: Hash SHA-256 del PDF en formato hexadecimal (64 caracteres).
             Ejemplo: "9f2c7a8e1e8d0a3c5cdbb9d6c3d6e9bcb84f6f2c3c4f1e0d3b3e2b1a0c9d8e7"
    
    Raises:
        ValueError: Si pdf_data está vacío o es None.
        TypeError: Si pdf_data no es de un tipo soportado.
    
    Example:
        >>> # Con bytes
        >>> with open('certificado.pdf', 'rb') as f:
        ...     pdf_bytes = f.read()
        >>> hash_value = calculate_pdf_hash(pdf_bytes)
        >>> print(hash_value)
        '9f2c7a8e1e8d0a3c5cdbb9d6c3d6e9bcb84f6f2c3c4f1e0d3b3e2b1a0c9d8e7'
        
        >>> # Con file stream
        >>> with open('certificado.pdf', 'rb') as f:
        ...     hash_value = calculate_pdf_hash(f)
        >>> print(hash_value)
        '9f2c7a8e1e8d0a3c5cdbb9d6c3d6e9bcb84f6f2c3c4f1e0d3b3e2b1a0c9d8e7'
        
        >>> # Con BytesIO
        >>> pdf_buffer = io.BytesIO(pdf_bytes)
        >>> hash_value = calculate_pdf_hash(pdf_buffer)
        >>> print(hash_value)
        '9f2c7a8e1e8d0a3c5cdbb9d6c3d6e9bcb84f6f2c3c4f1e0d3b3e2b1a0c9d8e7'
    """
    if pdf_data is None:
        raise ValueError("pdf_data no puede ser None")
    
    # Inicializar el objeto hash SHA-256
    sha256_hash = hashlib.sha256()
    
    # Manejar diferentes tipos de entrada
    if isinstance(pdf_data, bytes):
        # Si ya tenemos los bytes, calcular el hash directamente
        if len(pdf_data) == 0:
            raise ValueError("pdf_data no puede estar vacío")
        sha256_hash.update(pdf_data)
    
    elif isinstance(pdf_data, (io.BytesIO, BinaryIO)) or hasattr(pdf_data, 'read'):
        # Si es un stream, leer en chunks para eficiencia de memoria
        # Esto es importante para archivos grandes (varios MB)
        # Guardar la posición actual del stream (si es posible)
        try:
            current_position = pdf_data.tell()
        except (AttributeError, OSError):
            current_position = 0
        
        # Ir al inicio del stream (si es posible)
        try:
            pdf_data.seek(0)
        except (AttributeError, OSError):
            # Si no se puede hacer seek, asumimos que está al inicio
            pass
        
        try:
            # Leer en chunks de 64KB para balancear eficiencia y uso de memoria
            chunk_size = 64 * 1024  # 64 KB
            bytes_read = 0
            while True:
                chunk = pdf_data.read(chunk_size)
                if not chunk:
                    break
                bytes_read += len(chunk)
                sha256_hash.update(chunk)
            
            # Verificar que se leyó al menos algún dato
            if bytes_read == 0:
                raise ValueError("El stream del PDF está vacío")
        finally:
            # Restaurar la posición original del stream (si es posible)
            try:
                pdf_data.seek(current_position)
            except (AttributeError, OSError):
                pass
    
    else:
        raise TypeError(
            f"pdf_data debe ser bytes, BinaryIO o io.BytesIO, "
            f"pero se recibió: {type(pdf_data).__name__}"
        )
    
    # Retornar el hash en formato hexadecimal
    # Nota: El hash SHA-256 siempre tendrá 64 caracteres hexadecimales (32 bytes)
    return sha256_hash.hexdigest()


async def calculate_pdf_hash_async(pdf_data: Union[bytes, BinaryIO, io.BytesIO]) -> str:
    """
    Versión asíncrona de calculate_pdf_hash.
    
    Esta función es útil cuando se trabaja en un contexto asíncrono (async/await)
    y se necesita calcular el hash sin bloquear el event loop.
    
    Args:
        pdf_data: Los bytes del PDF o un objeto file-like (stream) que contenga
                  el contenido binario del PDF.
    
    Returns:
        str: Hash SHA-256 del PDF en formato hexadecimal (64 caracteres).
    
    Raises:
        ValueError: Si pdf_data está vacío o es None.
        TypeError: Si pdf_data no es de un tipo soportado.
    
    Note:
        Aunque esta función es async, el cálculo del hash en sí es una operación
        CPU-bound. Para archivos muy grandes, considera usar un executor thread
        para evitar bloquear el event loop.
    """
    # Para operaciones CPU-bound como SHA-256, podemos ejecutarla en el thread pool
    # si es necesario, pero para la mayoría de casos, ejecutarla directamente es suficiente
    return calculate_pdf_hash(pdf_data)
