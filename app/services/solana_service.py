import os
import json
from typing import Optional, Dict, Any
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.message import MessageV0
from solders.instruction import Instruction, AccountMeta
from solders.hash import Hash
from solders.signature import Signature
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Confirmed
from solana.rpc.types import TxOpts
from base58 import b58decode


class SolanaService:
    """Servicio para interactuar con la blockchain de Solana usando Helius RPC"""
    
    def __init__(self):
        self.helius_api_key = os.getenv("HELIUS_API_KEY")
        self.private_key = os.getenv("SOLANA_PRIVATE_KEY")
        
        if not self.helius_api_key:
            raise ValueError("HELIUS_API_KEY environment variable is not set")
        
        if not self.private_key:
            raise ValueError("SOLANA_PRIVATE_KEY environment variable is not set")
        
        # Construir URL de Helius RPC
        # Verificar si estamos usando mainnet o devnet
        network = os.getenv("SOLANA_NETWORK", "mainnet")
        if network == "devnet":
            self.rpc_url = f"https://devnet.helius-rpc.com/?api-key={self.helius_api_key}"
        else:
            self.rpc_url = f"https://mainnet.helius-rpc.com/?api-key={self.helius_api_key}"
        
        # Crear cliente RPC
        self.client = AsyncClient(self.rpc_url)
        
        # Crear Keypair desde la clave privada
        try:
            # La clave privada puede venir en formato base58 o como array JSON
            if isinstance(self.private_key, str):
                # Intentar decodificar como array JSON primero (formato común)
                try:
                    private_key_list = json.loads(self.private_key)
                    private_key_bytes = bytes(private_key_list)
                except (json.JSONDecodeError, TypeError, ValueError):
                    # Si falla, intentar como base58
                    try:
                        private_key_bytes = b58decode(self.private_key)
                    except Exception:
                        raise ValueError("SOLANA_PRIVATE_KEY debe ser un array JSON o base58 válido")
            else:
                private_key_bytes = bytes(self.private_key)
            
            self.keypair = Keypair.from_bytes(private_key_bytes)
        except Exception as e:
            raise ValueError(f"Error al crear Keypair desde SOLANA_PRIVATE_KEY: {str(e)}")
    
    async def register_hash(self, hash_value: str) -> Dict[str, Any]:
        """
        Registra un hash en Solana usando el programa Memo.
        
        Args:
            hash_value: Hash SHA-256 del documento
            
        Returns:
            Dict con signature, explorer_url y otros detalles de la transacción
            
        Raises:
            Exception: Si la transacción falla
        """
        network = os.getenv("SOLANA_NETWORK", "mainnet")

        try:
            # Crear el memo con el formato: DOCUMENT_HASH:<hash>
            memo_text = f"DOCUMENT_HASH:{hash_value}"
            memo_bytes = memo_text.encode('utf-8')
            
            # Obtener el pubkey del signer
            signer_pubkey = self.keypair.pubkey()
            
            # Crear la instrucción Memo
            # En Solana, el programa Memo es: MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr
            memo_program_id = Pubkey.from_string("MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr")
            
            # Crear la instrucción memo
            memo_instruction = Instruction(
                program_id=memo_program_id,
                data=memo_bytes,
                accounts=[AccountMeta(pubkey=signer_pubkey, is_signer=True, is_writable=False)]
            )
            
            # Obtener el último blockhash justo antes de crear y enviar la transacción
            recent_blockhash_resp = await self.client.get_latest_blockhash(commitment=Confirmed)
            
            if recent_blockhash_resp.value is None:
                raise Exception("No se pudo obtener el blockhash reciente: respuesta es None")
            
            recent_blockhash = recent_blockhash_resp.value.blockhash
            
            if recent_blockhash is None:
                raise Exception("Blockhash obtenido es None")
            
            # Convertir blockhash a Hash de solders si es necesario
            if isinstance(recent_blockhash, str):
                recent_blockhash = Hash.from_string(recent_blockhash)
            
            # Usar MessageV0 + VersionedTransaction (enfoque moderno, evita bugs de tipos)
            # MessageV0.try_compile maneja el blockhash y signers internamente
            message = MessageV0.try_compile(
                payer=signer_pubkey,
                instructions=[memo_instruction],
                address_lookup_table_accounts=[],
                recent_blockhash=recent_blockhash,
            )
            
            # Crear y firmar la VersionedTransaction pasando el keypair directamente.
            # Esto asegura que la firma cubra el prefijo de versión (0x80 para v0)
            # además del mensaje — firma manual con bytes(message) omite ese prefijo
            # y produce una firma inválida que los validadores descartan silenciosamente.
            transaction = VersionedTransaction(message, [self.keypair])
            
            # Enviar la transacción pre-firmada como bytes raw.
            # send_transaction() espera keypairs para firmar internamente, lo cual
            # es incompatible con una VersionedTransaction ya firmada.
            # send_raw_transaction() acepta la transacción serializada directamente.
            send_resp = await self.client.send_raw_transaction(
                bytes(transaction),
                opts=TxOpts(skip_preflight=False, preflight_commitment=Confirmed)
            )
            
            if send_resp.value is None:
                raise Exception("Error al enviar la transacción: respuesta vacía")
            
            # Mantener el objeto Signature para confirm_transaction (espera Signature, no str)
            tx_signature: Signature = send_resp.value
            signature_str = str(tx_signature)
            
            # Esperar confirmación (con timeout)
            import asyncio
            tx_status = "pending"
            try:
                confirmation_resp = await asyncio.wait_for(
                    self.client.confirm_transaction(tx_signature, commitment=Confirmed),
                    timeout=30.0
                )
                
                if confirmation_resp.value is None or len(confirmation_resp.value) == 0:
                    raise Exception("No se recibió confirmación de la transacción")
                
                if confirmation_resp.value[0].err:
                    raise Exception(f"Error en la transacción: {confirmation_resp.value[0].err}")
                
                tx_status = "confirmed"
            except asyncio.TimeoutError:
                # La transacción fue enviada pero no confirmada dentro del timeout.
                # Puede estar pendiente; el usuario puede verificar con la signature.
                tx_status = "pending"
            
            # Construir URL del explorador según la red
            if network == "devnet":
                explorer_url = f"https://solscan.io/tx/{signature_str}?cluster=devnet"
            else:
                explorer_url = f"https://solscan.io/tx/{signature_str}"
            
            return {
                "signature": signature_str,
                "explorer_url": explorer_url,
                "status": tx_status,
            }
            
        except Exception as e:
            raise Exception(f"Error al registrar hash en Solana: {str(e)}")
    
    async def close(self):
        """Cierra la conexión RPC"""
        await self.client.close()


# Instancia global del servicio (se inicializa cuando se necesite)
_solana_service: Optional[SolanaService] = None


def get_solana_service() -> SolanaService:
    """Obtiene o crea la instancia del servicio de Solana"""
    global _solana_service
    if _solana_service is None:
        _solana_service = SolanaService()
    return _solana_service
