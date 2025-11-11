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

    # ... [El resto del código se mantiene igual] ...

if __name__ == "__main__":
    print("🔒 SISTEMA DE ACCESO SEGURO")
    print("1. Iniciar sesión de trabajo")
    print("2. Monitor de administración")
    
    opcion = input("\nSeleccione opción: ").strip()
    
    if opcion == "1":
        # Aquí cambiamos la URL
        client = SessionAuthClient("https://nfcblockchain.vercel.app/", "ACR122U-ANTIFUGA-01")
        
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
