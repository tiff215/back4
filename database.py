import sqlite3
from datetime import datetime
import hashlib
import os

class DatabaseManager:
    def __init__(self, db_name="nfc_auth_system.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Inicializar la base de datos con todas las tablas"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Tabla de usuarios NFC (versión actualizada CON PIN)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nfc_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nfc_id TEXT UNIQUE NOT NULL,
                username TEXT NOT NULL,
                full_name TEXT NOT NULL,
                department TEXT NOT NULL,
                security_level INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                is_admin BOOLEAN DEFAULT FALSE,
                pin TEXT DEFAULT '0000',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Verificar y agregar columnas si no existen
        self._add_column_if_not_exists(cursor, 'nfc_users', 'is_admin', 'BOOLEAN DEFAULT FALSE')
        self._add_column_if_not_exists(cursor, 'nfc_users', 'pin', 'TEXT DEFAULT "0000"')
        
        # Tabla de registros de autenticación
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                nfc_id TEXT NOT NULL,
                device_id TEXT NOT NULL,
                auth_success BOOLEAN NOT NULL,
                auth_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blockchain_tx_hash TEXT,
                failure_reason TEXT,
                FOREIGN KEY (user_id) REFERENCES nfc_users (id)
            )
        ''')
        
        # Tabla de sesiones de usuario
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_token TEXT UNIQUE NOT NULL,
                device_id TEXT NOT NULL,
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                logout_time TIMESTAMP NULL,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES nfc_users (id)
            )
        ''')
        
        # Tabla de actividades durante la sesión
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS session_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_description TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                blockchain_tx_hash TEXT,
                FOREIGN KEY (session_id) REFERENCES user_sessions (id)
            )
        ''')
        
        conn.commit()
        
        # Insertar usuarios de prueba después de crear las tablas
        self._insert_test_users(cursor)
        
        conn.commit()
        conn.close()
        print("✅ Base de datos inicializada correctamente")
    
    def _add_column_if_not_exists(self, cursor, table_name, column_name, column_definition):
        """Agregar columna si no existe en la tabla"""
        try:
            # Verificar si la columna ya existe
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [column[1] for column in cursor.fetchall()]
            
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")
                print(f"✅ Columna '{column_name}' agregada a la tabla {table_name}")
        except sqlite3.Error as e:
            print(f"⚠️  Error verificando/agregando columna {column_name}: {e}")
    
    def _insert_test_users(self, cursor):
        """Insertar usuarios de prueba"""
        test_users = [
            ("04A1B2C3D4E5", "analopez", "Ana Lopez", "Inteligencia", 3, False, "0000"),
            ("04F6G7H8I9J0", "carlosruiz", "Carlos Ruiz", "Analisis", 2, False, "0000"),
            ("04K1L2M3N4O5", "mariatorres", "Maria Torres", "Operaciones", 2, False, "0000"),
            ("A0F9001E", "aimee", "Aimee", "Desarrollo", 2, False, "0000"),
        ]
        
        for nfc_id, username, full_name, department, security_level, is_admin, pin in test_users:
            try:
                # Verificar si el usuario ya existe
                cursor.execute('SELECT id FROM nfc_users WHERE nfc_id = ?', (nfc_id,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    # Actualizar usuario existente
                    cursor.execute('''
                        UPDATE nfc_users 
                        SET username = ?, full_name = ?, department = ?, security_level = ?, is_admin = ?, pin = ?
                        WHERE nfc_id = ?
                    ''', (username, full_name, department, security_level, is_admin, pin, nfc_id))
                else:
                    # Insertar nuevo usuario
                    cursor.execute('''
                        INSERT INTO nfc_users (nfc_id, username, full_name, department, security_level, is_admin, pin)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (nfc_id, username, full_name, department, security_level, is_admin, pin))
                    
            except sqlite3.Error as e:
                print(f"⚠️  Error insertando usuario {full_name}: {e}")
    
    def register_nfc_user(self, nfc_id: str, username: str, full_name: str, 
                         department: str, security_level: int = 1, is_admin: bool = False) -> bool:
        """Registrar nuevo usuario NFC (mantener compatibilidad)"""
        return self.register_nfc_user_with_pin(nfc_id, username, full_name, department, security_level, is_admin, "0000")
    
    def register_nfc_user_with_pin(self, nfc_id: str, username: str, full_name: str, 
                                 department: str, security_level: int = 1, 
                                 is_admin: bool = False, pin: str = "0000") -> bool:
        """Registrar nuevo usuario NFC CON PIN"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO nfc_users (nfc_id, username, full_name, department, security_level, is_admin, pin)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (nfc_id, username, full_name, department, security_level, is_admin, pin))
            
            conn.commit()
            admin_status = " (ADMIN)" if is_admin else ""
            print(f"✅ Usuario {full_name}{admin_status} registrado con NFC: {nfc_id}")
            print(f"🔐 PIN temporal asignado: {pin}")
            return True
            
        except sqlite3.IntegrityError:
            print(f"❌ Error: La tarjeta NFC {nfc_id} ya está registrada")
            return False
        except sqlite3.Error as e:
            print(f"❌ Error de base de datos: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_by_nfc(self, nfc_id: str):
        """Obtener usuario por ID NFC"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, nfc_id, username, full_name, department, security_level, is_active, is_admin, pin
                FROM nfc_users 
                WHERE nfc_id = ? AND is_active = TRUE
            ''', (nfc_id,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'id': result[0],
                    'nfc_id': result[1],
                    'username': result[2],
                    'full_name': result[3],
                    'department': result[4],
                    'security_level': result[5],
                    'is_active': bool(result[6]),
                    'is_admin': bool(result[7]),
                    'pin': result[8]  # Nuevo campo PIN
                }
            return None
            
        except sqlite3.Error as e:
            print(f"❌ Error consultando usuario: {e}")
            return None
        finally:
            conn.close()
    
    def update_user_pin(self, nfc_id: str, new_pin: str) -> bool:
        """Actualizar PIN de usuario"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE nfc_users 
                SET pin = ?, updated_at = CURRENT_TIMESTAMP
                WHERE nfc_id = ? AND is_active = TRUE
            ''', (new_pin, nfc_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                print(f"✅ PIN actualizado para tarjeta: {nfc_id}")
            else:
                print(f"❌ No se encontró usuario activo con NFC: {nfc_id}")
            
            return success
            
        except sqlite3.Error as e:
            print(f"❌ Error actualizando PIN: {e}")
            return False
        finally:
            conn.close()
    
    def get_user_pin(self, nfc_id: str) -> str:
        """Obtener PIN de usuario"""
        user = self.get_user_by_nfc(nfc_id)
        return user['pin'] if user and 'pin' in user else "0000"
    
    def verify_pin(self, nfc_id: str, pin: str) -> bool:
        """Verificar si el PIN es correcto"""
        user = self.get_user_by_nfc(nfc_id)
        if user and 'pin' in user:
            return user['pin'] == pin
        return False
    
    def update_user_as_admin(self, nfc_id: str, full_name: str, department: str = "Administración"):
        """Actualizar usuario como administrador"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE nfc_users 
                SET full_name = ?, department = ?, security_level = 3, is_admin = TRUE, updated_at = CURRENT_TIMESTAMP
                WHERE nfc_id = ?
            ''', (full_name, department, nfc_id))
            
            success = cursor.rowcount > 0
            conn.commit()
            
            if success:
                print(f"✅ Usuario {full_name} actualizado como administrador")
            else:
                print(f"❌ No se encontró usuario con NFC: {nfc_id}")
            
            return success
            
        except sqlite3.Error as e:
            print(f"❌ Error actualizando usuario: {e}")
            return False
        finally:
            conn.close()
    
    def get_admin_users(self):
        """Obtener todos los usuarios administradores"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT nfc_id, username, full_name, department, security_level, pin
                FROM nfc_users 
                WHERE is_admin = TRUE AND is_active = TRUE
            ''')
            
            admins = []
            for row in cursor.fetchall():
                admins.append({
                    'nfc_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'department': row[3],
                    'security_level': row[4],
                    'pin': row[5]
                })
            
            return admins
            
        except sqlite3.Error as e:
            print(f"❌ Error obteniendo administradores: {e}")
            return []
        finally:
            conn.close()
    
    def log_auth_attempt(self, user_id: int, nfc_id: str, device_id: str, 
                        success: bool, blockchain_tx_hash: str = None, 
                        failure_reason: str = None):
        """Registrar intento de autenticación"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO auth_logs 
                (user_id, nfc_id, device_id, auth_success, blockchain_tx_hash, failure_reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, nfc_id, device_id, success, blockchain_tx_hash, failure_reason))
            
            conn.commit()
            status = "EXITOSA" if success else "FALLIDA"
            print(f"📝 Autenticación {status} registrada para NFC: {nfc_id}")
            
        except sqlite3.Error as e:
            print(f"❌ Error registrando autenticación: {e}")
        finally:
            conn.close()
    
    def get_auth_logs(self, limit: int = 50):
        """Obtener últimos registros de autenticación"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    al.auth_timestamp,
                    u.full_name,
                    u.department,
                    al.nfc_id,
                    al.device_id,
                    al.auth_success,
                    al.blockchain_tx_hash,
                    al.failure_reason
                FROM auth_logs al
                JOIN nfc_users u ON al.user_id = u.id
                ORDER BY al.auth_timestamp DESC
                LIMIT ?
            ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'timestamp': row[0],
                    'full_name': row[1],
                    'department': row[2],
                    'nfc_id': row[3],
                    'device_id': row[4],
                    'success': bool(row[5]),
                    'blockchain_tx': row[6],
                    'failure_reason': row[7]
                })
            
            return logs
            
        except sqlite3.Error as e:
            print(f"❌ Error obteniendo logs: {e}")
            return []
        finally:
            conn.close()

    # --- MÉTODOS PARA SESIONES ---
    
    def create_session(self, user_id: int, device_id: str, session_token: str):
        """Crear nueva sesión para usuario"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO user_sessions (user_id, session_token, device_id)
                VALUES (?, ?, ?)
            ''', (user_id, session_token, device_id))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error creando sesión: {e}")
            return False
        finally:
            conn.close()
    
    def log_session_activity(self, session_id: int, activity_type: str, 
                           description: str, blockchain_tx_hash: str = None):
        """Registrar actividad durante la sesión"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO session_activities 
                (session_id, activity_type, activity_description, blockchain_tx_hash)
                VALUES (?, ?, ?, ?)
            ''', (session_id, activity_type, description, blockchain_tx_hash))
            
            conn.commit()
            return True
            
        except sqlite3.Error as e:
            print(f"❌ Error registrando actividad: {e}")
            return False
        finally:
            conn.close()
    
    def get_session_by_token(self, session_token: str):
        """Obtener sesión por token"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT id, user_id, device_id, login_time, is_active
                FROM user_sessions 
                WHERE session_token = ?
            ''', (session_token,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'id': result[0],
                    'user_id': result[1],
                    'device_id': result[2],
                    'login_time': result[3],
                    'is_active': bool(result[4])
                }
            return None
            
        except sqlite3.Error as e:
            print(f"❌ Error obteniendo sesión: {e}")
            return None
        finally:
            conn.close()
    
    def close_session(self, session_token: str):
        """Cerrar sesión"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE user_sessions 
                SET logout_time = CURRENT_TIMESTAMP, is_active = FALSE
                WHERE session_token = ? AND is_active = TRUE
            ''', (session_token,))
            
            success = cursor.rowcount > 0
            conn.commit()
            return success
            
        except sqlite3.Error as e:
            print(f"❌ Error cerrando sesión: {e}")
            return False
        finally:
            conn.close()
    
    def get_session_activities(self, session_token: str):
        """Obtener todas las actividades de una sesión"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
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
            
            return activities
            
        except sqlite3.Error as e:
            print(f"❌ Error obteniendo actividades: {e}")
            return []
        finally:
            conn.close()

    def get_all_users(self):
        """Obtener todos los usuarios"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT nfc_id, username, full_name, department, security_level, is_admin, pin
                FROM nfc_users 
                WHERE is_active = TRUE
                ORDER BY full_name
            ''')
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    'nfc_id': row[0],
                    'username': row[1],
                    'full_name': row[2],
                    'department': row[3],
                    'security_level': row[4],
                    'is_admin': bool(row[5]),
                    'pin': row[6]  # Nuevo campo PIN
                })
            
            return users
            
        except sqlite3.Error as e:
            print(f"❌ Error obteniendo usuarios: {e}")
            return []
        finally:
            conn.close()

    def backup_database(self):
        """Crear backup de la base de datos"""
        import shutil
        from datetime import datetime
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"backup_{timestamp}_{self.db_name}"
            
            if os.path.exists(self.db_name):
                shutil.copy2(self.db_name, backup_name)
                print(f"✅ Backup creado: {backup_name}")
                return True
            else:
                print("ℹ️  No existe base de datos para hacer backup")
                return False
                
        except Exception as e:
            print(f"❌ Error creando backup: {e}")
            return False

if __name__ == "__main__":
    # Crear backup antes de modificar
    db = DatabaseManager()
    db.backup_database()
    
    # Mostrar usuarios registrados CON PIN
    users = db.get_all_users()
    print(f"\n👥 Usuarios registrados ({len(users)}):")
    for user in users:
        admin_status = " 🔑 ADMIN" if user['is_admin'] else ""
        print(f"   👤 {user['full_name']} - {user['department']} - Nivel {user['security_level']}{admin_status}")
        print(f"   🔐 PIN: {user['pin']}")
        print("   " + "-" * 40)
    
    print("✅ Base de datos actualizada exitosamente")