import sqlite3
import secrets
from datetime import datetime
from database import DatabaseManager
from blockchain_simulated import BlockchainSimulated

class SessionManager:
    def __init__(self):
        self.db = DatabaseManager()
        self.blockchain = BlockchainSimulated()
    
    def create_session(self, user_id: int, device_id: str) -> str:
        """Crear nueva sesión para usuario"""
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        
        # Generar token único para la sesión
        session_token = secrets.token_hex(16)
        
        cursor.execute('''
            INSERT INTO user_sessions (user_id, session_token, device_id)
            VALUES (?, ?, ?)
        ''', (user_id, session_token, device_id))
        
        conn.commit()
        conn.close()
        
        print(f"✅ Sesión iniciada - Token: {session_token[:8]}...")
        return session_token
    
    def log_activity(self, session_token: str, activity_type: str, description: str):
        """Registrar actividad durante la sesión"""
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        
        # Obtener session_id
        cursor.execute('''
            SELECT id FROM user_sessions 
            WHERE session_token = ? AND is_active = TRUE
        ''', (session_token,))
        
        result = cursor.fetchone()
        if not result:
            print("❌ Sesión no encontrada o inactiva")
            return None
        
        session_id = result[0]
        
        # Registrar en blockchain
        tx_hash = self.blockchain.record_auth_attempt(
            user_id=f"session_{session_id}",
            timestamp=datetime.now().timestamp(),
            device_id="activity_log",
            nfc_id=activity_type,
            success=True
        )
        
        # Guardar actividad
        cursor.execute('''
            INSERT INTO session_activities 
            (session_id, activity_type, activity_description, blockchain_tx_hash)
            VALUES (?, ?, ?, ?)
        ''', (session_id, activity_type, description, tx_hash))
        
        conn.commit()
        conn.close()
        
        print(f"📝 Actividad registrada: {activity_type} - {description}")
        return tx_hash
    
    def logout_user(self, session_token: str) -> bool:
        """Cerrar sesión de usuario"""
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_sessions 
            SET logout_time = CURRENT_TIMESTAMP, is_active = FALSE
            WHERE session_token = ? AND is_active = TRUE
        ''', (session_token,))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            print(f"✅ Sesión cerrada - Token: {session_token[:8]}...")
            # Registrar cierre en blockchain
            self.blockchain.record_auth_attempt(
                user_id=f"logout_{session_token[:8]}",
                timestamp=datetime.now().timestamp(),
                device_id="session_management",
                nfc_id="logout",
                success=True
            )
        else:
            print("❌ No se pudo cerrar la sesión")
        
        return success
    
    def get_session_activities(self, session_token: str):
        """Obtener todas las actividades de una sesión"""
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                sa.activity_type,
                sa.activity_description,
                sa.timestamp,
                sa.blockchain_tx_hash
            FROM session_activities sa
            JOIN user_sessions us ON sa.session_id = us.id
            WHERE us.session_token = ?
            ORDER BY sa.timestamp DESC
        ''', (session_token,))
        
        activities = []
        for row in cursor.fetchall():
            activities.append({
                'activity_type': row[0],
                'description': row[1],
                'timestamp': row[2],
                'blockchain_tx': row[3]
            })
        
        conn.close()
        return activities
    
    def is_session_active(self, session_token: str) -> bool:
        """Verificar si una sesión está activa"""
        conn = sqlite3.connect(self.db.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM user_sessions 
            WHERE session_token = ? AND is_active = TRUE
        ''', (session_token,))
        
        result = cursor.fetchone()
        conn.close()
        
        return result is not None