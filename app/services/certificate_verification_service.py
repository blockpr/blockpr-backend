from typing import Optional

from app.config.database import get_db_pool
from app.models.blockchain_transaction import BlockchainTransaction
from app.models.certificate import Certificate


async def verify_certificate_by_hash(document_hash: str) -> Optional[dict]:
    """
    Verifica si un hash de certificado existe en la base de datos y retorna
    información del certificado y su transacción blockchain asociada.
    
    Args:
        document_hash: Hash SHA-256 del documento PDF
        
    Returns:
        Diccionario con información del certificado y transacción, o None si no existe
        Formato:
        {
            "certificate": Certificate object (como dict),
            "blockchain_transaction": BlockchainTransaction object (como dict) o None
        }
    """
    pool = get_db_pool()
    async with pool.acquire() as conn:
        # Buscar el certificado por hash
        cert_row = await conn.fetchrow(
            """
            SELECT * FROM certificates
            WHERE document_hash = $1
            """,
            document_hash
        )
        
        if not cert_row:
            return None
        
        certificate = Certificate.from_dict(dict(cert_row))
        result = {
            "certificate": certificate.to_dict(),
            "blockchain_transaction": None,
        }
        
        # Si tiene blockchain_tx_id, buscar la transacción
        if certificate.blockchain_tx_id:
            tx_row = await conn.fetchrow(
                """
                SELECT * FROM blockchain_transactions
                WHERE id = $1
                """,
                certificate.blockchain_tx_id
            )
            
            if tx_row:
                blockchain_tx = BlockchainTransaction.from_dict(dict(tx_row))
                result["blockchain_transaction"] = blockchain_tx.to_dict()
        
        return result
