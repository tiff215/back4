from web3 import Web3
import json
from datetime import datetime
import hashlib

class BlockchainSimulated:
    """Simulador de Blockchain para desarrollo"""
    
    def __init__(self):
        print("🔗 Blockchain SIMULADA iniciada")
        self.records = []
    
    def record_auth_attempt(self, user_id: str, timestamp: float, 
                          device_id: str, nfc_id: str, success: bool):
        """Registrar autenticación en blockchain simulada"""
        
        # Crear hash único para la transacción
        tx_data = f"{user_id}{timestamp}{device_id}{nfc_id}{success}"
        tx_hash = hashlib.sha256(tx_data.encode()).hexdigest()[:20]
        
        record = {
            'user_id': user_id,
            'timestamp': timestamp,
            'device_id': device_id,
            'nfc_id': nfc_id,
            'success': success,
            'tx_hash': f"0x{tx_hash}",
            'block_number': len(self.records) + 1
        }
        
        self.records.append(record)
        print(f"✅ Registro en blockchain simulada: {record['tx_hash']}")
        
        return record['tx_hash']
    
    def verify_transaction(self, tx_hash: str):
        """Verificar transacción"""
        for record in self.records:
            if record['tx_hash'] == tx_hash:
                return True
        return False

# Prueba rápida
if __name__ == "__main__":
    blockchain = BlockchainSimulated()
    tx = blockchain.record_auth_attempt("test_user", datetime.now().timestamp(), "device_01", "NFC123", True)
    print(f"Transacción: {tx}")