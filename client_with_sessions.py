import requests
import time
from datetime import datetime
from threading import Thread
import random
import re
import sqlite3
import os
import sys
import select
import hashlib
from acr122u_reader import ACR122UReader

class SessionAuthClient:
    def __init__(self, api_url: str, device_id: str):
        self.api_url = api_url
        self.device_id = device_id
        self.nfc_reader = ACR122UReader()
        self.current_session = None
        self.current_user = None
        self.monitor_thread = None
        self.activity_thread = None
        self.session_active = False
        self.activity_log = []
        self.security_alerts = []
        self.session_start_time = None
        
        # Sistema de monitoreo SILENCIOSO
        self.stealth_mode = True
        self.stealth_log_file = "security_audit.log"
        
        # Inicializar base de datos si no existe
        self._init_database()
        
        # Patrones de detección
        self.suspicious_keywords = [
            "exportar", "descargar", "copiar", "transferir", "compartir", 
            "enviar", "extraer", "backup", "respaldo", "descarga", "upload",
            "subir", "enviar", "mandar", "compartir", "transferencia", "copia",
            "extracción", "descargando", "exportando", "enviando", "USB",
            "dispositivo", "externo", "correo", "email", "adjunto", "archivo",
            "masivo", "lote", "batch", "gran", "volumen", "confidencial",
            "secreto", "clasificado", "restringido", "sensible"
        ]
        
        self.high_risk_activities = [
            "EXPORTAR_DATOS", "DESCARGA_MASIVA", "COPIA_SEGURIDAD",
            "TRANSFERENCIA_ARCHIVOS", "COMPARTIR_DOCUMENTOS", "ENVIO_CORREO",
            "BACKUP_EXTERNO", "EXTRACCION_DATOS", "UPLOAD_CLOUD",
            "ACCESO_EXTERNO", "CONEXION_REMOTA", "DESCARGAR_ARCHIVOS"
        ]

    def _init_database(self):
        """Inicializar tablas de la base de datos si no existen"""
        try:
            conn = sqlite3.connect('sessions.db')
            cursor = conn.cursor()
            
            # Tabla de sesiones
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_token TEXT PRIMARY KEY,
                    user_name TEXT,
                    department TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    device_id TEXT
                )
            ''')
            
            # Tabla de actividades
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_token TEXT,
                    activity_type TEXT,
                    description TEXT,
                    timestamp TEXT,
                    is_suspicious BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_token) REFERENCES sessions (session_token)
                )
            ''')
            
            # Tabla de alertas de seguridad
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_token TEXT,
                    alert_type TEXT,
                    description TEXT,
                    severity TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (session_token) REFERENCES sessions (session_token)
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"❌ Error inicializando base de datos: {e}")

    def check_server_health(self):
        """Verificar que el servidor esté funcionando"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Sistema listo")
                return True
            else:
                print("❌ Servidor no disponible")
                return False
        except Exception as e:
            print("❌ Error de conexión al servidor")
            print(f"   Ejecute primero: python main.py")
            return False

    def get_user_info(self, nfc_id: str):
        """Obtener información del usuario desde la base de datos"""
        try:
            response = requests.get(f"{self.api_url}/user/{nfc_id}", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    def start_session(self, pin: str, nfc_id: str):
        """Iniciar sesión en el servidor"""
        try:
            auth_data = {
                "pin": pin,
                "nfc_id": nfc_id,
                "device_id": self.device_id
            }
            
            response = requests.post(
                f"{self.api_url}/session/start",
                json=auth_data,
                timeout=10
            )
            
            return response.json()
            
        except Exception as e:
            return {"success": False, "message": f"Error: {str(e)}"}

    def card_removed_handler(self):
        """Manejador cuando se detecta que la tarjeta fue removida"""
        if self.session_active:
            print("\n🔒 Sesión cerrada por seguridad")
            self.emergency_logout()
    
    def start_card_monitor(self):
        """Inicia el hilo de monitoreo continuo"""
        if hasattr(self.nfc_reader, 'start_card_monitoring'):
            if self.nfc_reader.start_card_monitoring(self.card_removed_handler):
                self.monitor_thread = Thread(target=self._monitor_loop, daemon=True)
                self.monitor_thread.start()
    
    def _monitor_loop(self):
        """Loop de monitoreo continuo en segundo plano"""
        while self.session_active:
            if hasattr(self.nfc_reader, 'check_card_presence'):
                if not self.nfc_reader.check_card_presence():
                    break
            time.sleep(1)

    def start_automatic_activities(self):
        """Inicia el registro automático de actividades en segundo plano"""
        self.activity_thread = Thread(target=self._automatic_activity_loop, daemon=True)
        self.activity_thread.start()

    def _stealth_log(self, message: str, alert_level: str = "INFO"):
        """Registro silencioso en archivo de auditoría"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] [{alert_level}] {message}\n"
            
            with open(self.stealth_log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        except Exception:
            pass

    def _detect_suspicious_activity(self, activity_type: str, description: str) -> bool:
        """Detección avanzada de posibles fugas de información"""
        description_lower = description.lower()
        alert_detected = False
        
        # 1. Detección por keywords
        for keyword in self.suspicious_keywords:
            if keyword in description_lower:
                alert_message = f"Keyword sospechoso detectado: '{keyword}' en actividad: {description}"
                self._log_security_alert("KEYWORD_SOSPECHOSO", alert_message, "ALTO")
                alert_detected = True
        
        # 2. Detección por tipo de actividad de alto riesgo
        if activity_type in self.high_risk_activities:
            alert_message = f"Actividad de alto riesgo ejecutada: {activity_type} - {description}"
            self._log_security_alert("ACTIVIDAD_ALTO_RIESGO", alert_message, "CRITICO")
            alert_detected = True
        
        # 3. Detección por patrones de comportamiento
        if self._detect_behavior_patterns(activity_type, description):
            alert_detected = True
        
        # 4. Detección por volumen de actividades similares
        if self._detect_volume_pattern(activity_type):
            alert_message = f"Volumen alto de actividades similares: {activity_type}"
            self._log_security_alert("VOLUMEN_SOSPECHOSO", alert_message, "MEDIO")
            alert_detected = True
        
        return alert_detected

    def _detect_behavior_patterns(self, activity_type: str, description: str) -> bool:
        """Detección de patrones de comportamiento sospechoso"""
        current_time = datetime.now()
        alert_detected = False
        
        # Patrón: Actividades en horario no laboral
        if current_time.hour < 8 or current_time.hour > 18:
            if activity_type in self.high_risk_activities:
                alert_message = f"Actividad de alto riesgo en horario no laboral: {activity_type}"
                self._log_security_alert("HORARIO_SOSPECHOSO", alert_message, "ALTO")
                alert_detected = True
        
        # Patrón: Múltiples exportaciones en corto tiempo
        recent_exports = [a for a in self.activity_log[-10:] 
                         if any(keyword in a['description'].lower() 
                               for keyword in ['exportar', 'descargar', 'extraer'])]
        
        if len(recent_exports) >= 3:
            alert_message = f"Múltiples operaciones de exportación detectadas: {len(recent_exports)} en los últimos 10 registros"
            self._log_security_alert("EXPORTACION_MULTIPLE", alert_message, "CRITICO")
            alert_detected = True
        
        return alert_detected

    def _detect_volume_pattern(self, activity_type: str) -> bool:
        """Detección de patrones por volumen de actividades"""
        recent_activities = self.activity_log[-20:] if len(self.activity_log) >= 20 else self.activity_log
        same_activity_count = sum(1 for activity in recent_activities if activity['type'] == activity_type)
        
        if same_activity_count >= 5:
            return True
        
        return False

    def _log_security_alert(self, alert_type: str, message: str, severity: str):
        """Registrar alerta de seguridad"""
        alert_data = {
            "session_token": self.current_session,
            "activity_type": f"ALERTA_SEGURIDAD_{severity}",
            "description": f"[{alert_type}] {message}",
            "severity": severity,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        self.security_alerts.append(alert_data)
        self._stealth_log(f"{alert_type}: {message}", severity)
        
        # Guardar en base de datos
        self._save_alert_to_db(alert_type, message, severity)
        
        # Registrar en blockchain también
        self._log_activity_silent(
            f"ALERTA_SEGURIDAD_{severity}", 
            f"[{alert_type}] {message}"
        )

    def _save_alert_to_db(self, alert_type: str, message: str, severity: str):
        """Guardar alerta en base de datos"""
        try:
            conn = sqlite3.connect('sessions.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO security_alerts 
                (session_token, alert_type, description, severity, timestamp)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.current_session,
                alert_type,
                message,
                severity,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _log_activity_silent(self, activity_type: str, description: str):
        """Registro silencioso de actividad"""
        try:
            # Primero verificar si es actividad sospechosa
            is_suspicious = self._detect_suspicious_activity(activity_type, description)
            
            activity_data = {
                "session_token": self.current_session,
                "activity_type": activity_type,
                "description": description
            }
            
            response = requests.post(
                f"{self.api_url}/session/activity",
                json=activity_data,
                timeout=3
            )
            
            # Registrar internamente
            log_entry = {
                'type': activity_type,
                'description': description,
                'timestamp': datetime.now().strftime('%H:%M:%S'),
                'suspicious': is_suspicious,
                'success': response.json().get('success', False)
            }
            
            self.activity_log.append(log_entry)
            
            # Guardar en base de datos local
            self._save_activity_to_db(activity_type, description, is_suspicious)
                
        except Exception:
            pass

    def _save_activity_to_db(self, activity_type: str, description: str, is_suspicious: bool):
        """Guardar actividad en base de datos local"""
        try:
            conn = sqlite3.connect('sessions.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO activities 
                (session_token, activity_type, description, timestamp, is_suspicious)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.current_session,
                activity_type,
                description,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                is_suspicious
            ))
            
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _automatic_activity_loop(self):
        """Registro automático TOTALMENTE SILENCIOSO"""
        normal_activities = [
            ("INICIO_SESION", "Inicio de sesión en el sistema"),
            ("ACCESO_SISTEMA_PRINCIPAL", "Acceso al dashboard principal"),
            ("CONSULTA_BASE_DATOS", "Consulta de registros en base de datos"),
            ("GENERACION_REPORTE", "Generación automática de reporte diario"),
            ("ANALISIS_DATOS", "Análisis de métricas del sistema"),
            ("REVISION_SEGURIDAD", "Revisión de logs de seguridad"),
            ("ACTUALIZACION_SISTEMA", "Actualización de configuraciones"),
            ("BACKUP_DATOS", "Copia de seguridad automática"),
            ("MONITOREO_RED", "Monitoreo de tráfico de red"),
            ("AUDITORIA_ACCESOS", "Auditoría de accesos recientes"),
            ("OPTIMIZACION_SISTEMA", "Optimización de recursos del sistema"),
            ("REVISION_DOCUMENTOS", "Revisión de documentos corporativos"),
            ("ANALISIS_SEGURIDAD", "Análisis de vulnerabilidades"),
            ("CONFIGURACION_RED", "Configuración de parámetros de red"),
            ("REVISION_LOGS", "Revisión de logs del sistema"),
        ]
        
        potential_risk_activities = [
            ("EXPORTAR_DATOS", "Exportando datos confidenciales a Excel"),
            ("DESCARGA_MASIVA", "Descargando archivos del sistema"),
            ("COPIA_SEGURIDAD", "Creando copia de seguridad externa"),
            ("TRANSFERENCIA_ARCHIVOS", "Transferiendo archivos a dispositivo USB"),
            ("ENVIO_CORREO", "Enviando correo con archivos adjuntos"),
            ("BACKUP_EXTERNO", "Realizando backup en almacenamiento externo"),
            ("ACCESO_REMOTO", "Estableciendo conexión remota a servidores"),
            ("EXTRACCION_DATOS", "Extrayendo datos de bases de datos sensibles"),
        ]
        
        activity_index = 0
        risk_activity_chance = 0.15
        
        while self.session_active:
            # Seleccionar actividad (normal o de riesgo)
            if random.random() < risk_activity_chance and potential_risk_activities:
                activity_type, description = random.choice(potential_risk_activities)
            else:
                activity_type, description = normal_activities[activity_index % len(normal_activities)]
            
            # Registrar SILENCIOSAMENTE
            self._log_activity_silent(activity_type, description)
            
            activity_index += 1
            time.sleep(random.randint(30, 90))

    def _stealth_monitor_loop(self):
        """Monitoreo silencioso en segundo plano"""
        last_activity_count = 0
        last_alert_count = 0
        
        while self.session_active:
            try:
                # Verificar nuevas actividades
                current_activities = len(self.activity_log)
                if current_activities > last_activity_count:
                    new_activities = current_activities - last_activity_count
                    self._stealth_log(f"Nuevas actividades detectadas: {new_activities} (Total: {current_activities})")
                    last_activity_count = current_activities
                
                # Verificar nuevas alertas
                current_alerts = len(self.security_alerts)
                if current_alerts > last_alert_count:
                    new_alerts = current_alerts - last_alert_count
                    critical_alerts = len([a for a in self.security_alerts if a['severity'] in ['ALTO', 'CRITICO']])
                    self._stealth_log(f"Nuevas alertas: {new_alerts} (Críticas: {critical_alerts})", "ALERT")
                    last_alert_count = current_alerts
                
                # Estadísticas periódicas cada 5 minutos
                if int(time.time()) % 300 == 0:
                    elapsed_minutes = int((datetime.now() - self.session_start_time).total_seconds() / 60)
                    suspicious_count = len([a for a in self.activity_log if a.get('suspicious', False)])
                    self._stealth_log(f"Estadísticas periódicas - Duración: {elapsed_minutes}min, Actividades: {current_activities}, Sospechosas: {suspicious_count}")
                
                time.sleep(10)
                
            except Exception:
                pass

    def start_stealth_monitor(self):
        """Iniciar monitoreo silencioso"""
        self.monitor_thread = Thread(target=self._stealth_monitor_loop, daemon=True)
        self.monitor_thread.start()
        self._stealth_log("Sistema de monitoreo stealth iniciado", "SYSTEM")

    def start_auth_flow(self):
        """MÉTODO PRINCIPAL DE AUTENTICACIÓN"""
        print("\n" + "="*50)
        print("       SISTEMA DE ACCESO SEGURO")
        print("="*50)
        
        if not self.check_server_health():
            return False
        
        print("\n🔰 Iniciando autenticación...")
        print("   Tiene 30 segundos para acercar la tarjeta")
        
        # Esperar tarjeta NFC
        nfc_id = self.nfc_reader.wait_for_card(30)
        
        if not nfc_id:
            print("❌ Tiempo agotado - No se detectó tarjeta")
            return False
        
        user_info = self.get_user_info(nfc_id)
        if not user_info:
            print("❌ Usuario no registrado en el sistema")
            return False
        
        self.current_user = user_info['full_name']
        print(f"✅ Usuario identificado: {user_info['full_name']}")
        print(f"   Departamento: {user_info['department']}")
        
        # Ingreso de PIN
        pin = input("\n🔒 Ingrese su PIN: ").strip()
        
        if not pin:
            print("❌ PIN requerido")
            return False
        
        # Iniciar sesión
        print("\n⏳ Verificando credenciales...")
        session_result = self.start_session(pin, nfc_id)
        
        if session_result.get('success'):
            self.current_session = session_result['session_token']
            self.session_active = True
            self.session_start_time = datetime.now()
            self.activity_log = []
            self.security_alerts = []
            
            # Guardar sesión en base de datos local
            self._save_session_to_db(session_result)
            
            self.show_session_start(session_result)
            
            # INICIAR SISTEMAS DE SEGURIDAD EN SEGUNDO PLANO
            self.start_card_monitor()
            self.start_automatic_activities()
            self.start_stealth_monitor()
            
            self.automatic_session_workflow()
            return True
        else:
            self.show_error_message(session_result)
            return False

    def _save_session_to_db(self, session_result: dict):
        """Guardar sesión en base de datos local"""
        try:
            conn = sqlite3.connect('sessions.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO sessions 
                (session_token, user_name, department, start_time, device_id)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                self.current_session,
                session_result['user']['full_name'],
                session_result['user']['department'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                self.device_id
            ))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"⚠️  Error guardando sesión: {e}")

    def _check_for_quit_key(self):
        """Verificar si se presionó la tecla 'q' para cerrar sesión"""
        try:
            # Para Windows
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch().decode('utf-8').lower()
                return key == 'q'
        except:
            try:
                # Para Linux/Mac
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1).lower()
                    return key == 'q'
            except:
                pass
        return False

    def automatic_session_workflow(self):
        """Flujo de trabajo COMPLETAMENTE TRANSPARENTE para el usuario"""
        if not self.session_active:
            return
        
        # Mensaje normal al usuario (sin revelar monitoreo)
        print("\n💼 Sesión iniciada - Puede trabajar normalmente")
        print("💡 Mantenga la tarjeta en el lector durante su jornada")
        print("   💡 **Presione 'q' para cerrar sesión**")
        
        # Bucle principal CON DETECCIÓN DE TECLA SECRETA
        session_start = time.time()
        max_session_duration = 8 * 60 * 60  # 8 horas
        
        while self.session_active:
            try:
                # Verificar si se presionó 'q' para salir
                if self._check_for_quit_key():
                    print("\n⏳ Cerrando sesión...")
                    break
                
                # Simplemente esperar sin interacción
                time.sleep(1)
                
                # Finalizar después de 8 horas automáticamente
                elapsed = time.time() - session_start
                if elapsed >= max_session_duration:
                    print("\n🕒 Jornada laboral completada")
                    break
                    
            except KeyboardInterrupt:
                print("\n🛑 Interrupción detectada...")
                break
            except Exception:
                continue
        
        # Cierre normal
        if self.session_active:
            self.manual_logout()

    def show_session_start(self, session_result: dict):
        """Mostrar inicio de sesión normal SIN revelar seguridad"""
        print(f"\n✅ Bienvenido/a {session_result['user']['full_name']}")
        print(f"🏢 Departamento: {session_result['user']['department']}")
        print("⏰ Sesión iniciada correctamente")
        print("\n💡 Puede comenzar a trabajar")

    def show_error_message(self, result: dict):
        """Mostrar mensaje de error"""
        print(f"\n❌ Error: {result.get('message', 'Error desconocido')}")

    def manual_logout(self):
        """Cierre manual de sesión iniciado por el usuario"""
        if not self.session_active:
            print("❌ No hay sesión activa")
            return False
        
        print("\n⏳ Cerrando sesión...")
        
        # Registrar actividad de cierre manual
        self._log_activity_silent("CIERRE_MANUAL", "Usuario solicitó cierre de sesión manual")
        
        self.session_active = False
        
        try:
            logout_data = {
                "session_token": self.current_session
            }
            
            response = requests.post(
                f"{self.api_url}/session/logout",
                json=logout_data,
                timeout=5
            )
            
            # Mensaje al usuario
            print("✅ Sesión cerrada correctamente")
            
            # Registrar en log de auditoría
            session_duration = int((datetime.now() - self.session_start_time).total_seconds() / 60)
            total_activities = len(self.activity_log)
            suspicious_count = len([a for a in self.activity_log if a.get('suspicious', False)])
            
            self._stealth_log(f"Sesión cerrada manualmente - Duración: {session_duration}min, Actividades: {total_activities}, Sospechosas: {suspicious_count}", "MANUAL_LOGOUT")
            
            # Mostrar resumen discreto
            self._show_quick_summary(session_duration, total_activities, suspicious_count)
            
            return True
            
        except Exception as e:
            print(f"⚠️  Error al cerrar sesión: {e}")
            return False
        finally:
            self.current_session = None

    def _show_quick_summary(self, duration: int, activities: int, suspicious: int):
        """Mostrar resumen rápido y discreto"""
        print(f"\n📊 Resumen de jornada:")
        print(f"   ⏰ Duración: {duration} minutos")
        print(f"   📋 Actividades: {activities}")
        print(f"   ✅ Sesión guardada correctamente")

    def emergency_logout(self):
        """Cierre de emergencia por remoción de tarjeta"""
        if not self.session_active:
            return
        
        self.session_active = False
        
        try:
            if self.current_session:
                self._log_activity_silent("SESION_INTERRUMPIDA", "Sesión interrumpida por seguridad - Tarjeta removida")
                
                logout_data = {
                    "session_token": self.current_session
                }
                
                requests.post(
                    f"{self.api_url}/session/logout",
                    json=logout_data,
                    timeout=5
                )
                
                print("\n🔒 Sesión cerrada por seguridad")
                self._stealth_log("Sesión interrumpida por remoción de tarjeta", "EMERGENCY")
                
        except Exception:
            pass
        
        self.current_session = None

def authenticate_admin():
    """Autenticación para administradores"""
    print("\n🔐 AUTENTICACIÓN DE ADMINISTRADOR")
    print("═" * 40)
    
    username = input("Usuario: ").strip()
    password = input("Contraseña: ").strip()
    
    if not username or not password:
        print("❌ Usuario y contraseña requeridos")
        return False
    
    try:
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            SELECT * FROM admins WHERE username = ? AND password_hash = ?
        ''', (username, password_hash))
        
        admin = cursor.fetchone()
        conn.close()
        
        if admin:
            print("✅ Acceso concedido")
            return True
        else:
            print("❌ Credenciales incorrectas")
            return False
            
    except Exception as e:
        print(f"❌ Error de autenticación: {e}")
        return False

def admin_monitor():
    """Sistema de monitoreo para administradores MEJORADO"""
    
    if not authenticate_admin():
        print("⏹️  Acceso denegado")
        time.sleep(2)
        return
    
    def clear_screen():
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def show_live_dashboard():
        """Dashboard en tiempo real para admins - CORREGIDO"""
        try:
            clear_screen()
            print("🛡️  DASHBOARD DE SEGURIDAD - MONITOREO EN TIEMPO REAL")
            print("═" * 80)
            
            conn = sqlite3.connect('sessions.db')
            cursor = conn.cursor()
            
            # Estadísticas del día
            cursor.execute('''
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN is_suspicious = 1 THEN 1 ELSE 0 END) as suspicious
                FROM activities 
                WHERE DATE(timestamp) = DATE('now')
            ''')
            today_stats = cursor.fetchone()
            total_activities = today_stats[0] if today_stats else 0
            suspicious_activities = today_stats[1] if today_stats else 0
            
            # Sesiones activas
            cursor.execute('''
                SELECT user_name, department, start_time 
                FROM sessions 
                WHERE end_time IS NULL
            ''')
            active_sessions = cursor.fetchall()
            
            # Últimas alertas
            cursor.execute('''
                SELECT timestamp, description, severity 
                FROM security_alerts 
                ORDER BY timestamp DESC 
                LIMIT 10
            ''')
            recent_alerts = cursor.fetchall()
            
            conn.close()
            
            print(f"📊 ESTADÍSTICAS HOY: {total_activities} actividades | {suspicious_activities} sospechosas")
            print(f"🔴 SESIONES ACTIVAS: {len(active_sessions)}")
            
            if active_sessions:
                print(f"\n👥 SESIONES ACTIVAS ACTUALES:")
                for session in active_sessions:
                    user_name, department, start_time = session
                    duration = int((datetime.now() - datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')).total_seconds() / 60)
                    print(f"   👤 {user_name} - {duration} min - {department}")
            
            print("\n🚨 ÚLTIMAS ALERTAS DE SEGURIDAD:")
            
            if recent_alerts:
                for alert in recent_alerts:
                    timestamp, description, severity = alert
                    icon = "🔴" if severity in ['ALTO', 'CRITICO'] else "🟡"
                    print(f"   {icon} [{timestamp}] {severity}: {description[:70]}...")
            else:
                print("   ✅ No hay alertas recientes")
            
            print("\n" + "═" * 80)
            print("💡 Presiona 'r' para actualizar, 'q' para volver al menú")
            
        except Exception as e:
            print(f"❌ Error en dashboard: {e}")
            print("💡 Presiona 'r' para actualizar, 'q' para volver al menú")

    def show_security_report():
        """Reporte de seguridad detallado - CORREGIDO"""
        try:
            clear_screen()
            print("📄 REPORTE DE SEGURIDAD - DETALLADO")
            print("═" * 80)
            
            conn = sqlite3.connect('sessions.db')
            cursor = conn.cursor()
            
            # Estadísticas generales
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_sessions,
                    COUNT(DISTINCT user_name) as unique_users,
                    COUNT(*) as total_activities,
                    SUM(CASE WHEN is_suspicious = 1 THEN 1 ELSE 0 END) as suspicious_activities
                FROM activities a
                JOIN sessions s ON a.session_token = s.session_token
                WHERE DATE(a.timestamp) = DATE('now')
            ''')
            stats = cursor.fetchone()
            
            total_sessions = stats[0] if stats else 0
            unique_users = stats[1] if stats else 0
            total_activities = stats[2] if stats else 0
            suspicious_activities = stats[3] if stats else 0
            
            # Alertas por severidad
            cursor.execute('''
                SELECT severity, COUNT(*) 
                FROM security_alerts 
                WHERE DATE(timestamp) = DATE('now')
                GROUP BY severity
            ''')
            alert_stats = cursor.fetchall()
            
            # Actividades más sospechosas
            cursor.execute('''
                SELECT activity_type, COUNT(*) 
                FROM activities 
                WHERE is_suspicious = 1 AND DATE(timestamp) = DATE('now')
                GROUP BY activity_type 
                ORDER BY COUNT(*) DESC 
                LIMIT 5
            ''')
            top_suspicious = cursor.fetchall()
            
            conn.close()
            
            print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d')}")
            print(f"📋 Sesiones hoy: {total_sessions}")
            print(f"👥 Usuarios únicos: {unique_users}")
            print(f"📊 Actividades totales: {total_activities}")
            print(f"🚨 Actividades sospechosas: {suspicious_activities}")
            
            print("\n🔴 ALERTAS POR GRAVEDAD:")
            if alert_stats:
                for severity, count in alert_stats:
                    print(f"   {severity}: {count}")
            else:
                print("   ✅ No hay alertas hoy")
            
            if top_suspicious:
                print("\n📋 ACTIVIDADES MÁS SOSPECHOSAS:")
                for activity, count in top_suspicious:
                    print(f"   {activity}: {count}")
            
            print("\n" + "═" * 80)
            
        except Exception as e:
            print(f"❌ Error generando reporte: {e}")

    def show_audit_log():
        """Mostrar archivo de auditoría - MEJORADO"""
        try:
            clear_screen()
            print("📋 ARCHIVO DE AUDITORÍA - ACTIVIDADES RECIENTES")
            print("═" * 80)
            
            if not os.path.exists("security_audit.log"):
                print("❌ Archivo de auditoría no encontrado")
                print("💡 Se creará automáticamente al iniciar sesiones")
                return
            
            # Mostrar solo las últimas 50 líneas para evitar sobrecarga
            with open("security_audit.log", "r", encoding="utf-8") as f:
                lines = f.readlines()
                recent_lines = lines[-50:] if len(lines) > 50 else lines
                
                if not recent_lines:
                    print("📭 El archivo de auditoría está vacío")
                    return
                
                for line in recent_lines:
                    print(line.strip())
            
            print("\n" + "═" * 80)
            print(f"📄 Mostrando {len(recent_lines)} líneas más recientes")
            
        except Exception as e:
            print(f"❌ Error leyendo archivo de auditoría: {e}")

    # Bucle principal del monitor admin - MEJORADO
    while True:
        clear_screen()
        print("🛡️  SISTEMA DE MONITOREO PARA ADMINISTRADORES")
        print("═" * 50)
        print("1. Dashboard en tiempo real")
        print("2. Reporte de seguridad detallado")
        print("3. Ver archivo de auditoría")
        print("4. Salir")
        
        opcion = input("\nSeleccione opción (1-4): ").strip()
        
        if opcion == "1":
            while True:
                show_live_dashboard()
                cmd = input().strip().lower()
                if cmd == 'q':
                    break
                elif cmd == 'r':
                    continue
        elif opcion == "2":
            show_security_report()
            input("\n💡 Presiona Enter para continuar...")
        elif opcion == "3":
            show_audit_log()
            input("\n💡 Presiona Enter para continuar...")
        elif opcion == "4":
            print("\n👋 Saliendo del monitor de administración...")
            break
        else:
            print("❌ Opción no válida. Por favor seleccione 1-4")
            time.sleep(2)

if __name__ == "__main__":
    print("🔒 SISTEMA DE ACCESO SEGURO")
    print("1. Iniciar sesión de trabajo")
    print("2. Monitor de administración")
    
    opcion = input("\nSeleccione opción: ").strip()
    
    if opcion == "1":
        client = SessionAuthClient("http://localhost:8000", "ACR122U-ANTIFUGA-01")
        
        try:
            while True:
                success = client.start_auth_flow()
                
                if success:
                    continuar = input("\n¿Iniciar nueva sesión? (s/n): ").strip().lower()
                else:
                    continuar = input("\n¿Reintentar acceso? (s/n): ").strip().lower()
                
                if continuar != 's':
                    print("\nSistema finalizado")
                    break
                    
        except KeyboardInterrupt:
            if client.session_active:
                client.emergency_logout()
            print("\nSistema interrumpido")
            
    elif opcion == "2":
        admin_monitor()
        
    else:
        print("❌ Opción no válida")