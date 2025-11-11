from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uvicorn
from typing import Optional
import hashlib
import sqlite3

from acr122u_reader import ACR122UReader
from database import DatabaseManager
from blockchain_simulated import BlockchainSimulated
from session_manager import SessionManager

app = FastAPI(title="Sistema de Autenticación NFC + Blockchain")

# Modelos de datos
class AuthRequest(BaseModel):
    pin: str
    nfc_id: str
    device_id: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict]
    blockchain_tx: Optional[str]

# Modelos para sesiones
class SessionStartRequest(BaseModel):
    pin: str
    nfc_id: str
    device_id: str

class ActivityRequest(BaseModel):
    session_token: str
    activity_type: str
    description: str

class LogoutRequest(BaseModel):
    session_token: str

# Modelo para registro de tarjetas admin
class AdminRegisterRequest(BaseModel):
    username: str
    password: str
    nfc_id: str
    full_name: str

# Inicializar componentes
nfc_reader = ACR122UReader()
database = DatabaseManager()
blockchain = BlockchainSimulated()
session_manager = SessionManager()

# Simulador de Active Directory (para pruebas)
active_directory_users = {
    "analopez": {"pin": "1234", "full_name": "Ana Lopez", "department": "Inteligencia"},
    "carlosruiz": {"pin": "5678", "full_name": "Carlos Ruiz", "department": "Analisis"},
    "mariatorres": {"pin": "9012", "full_name": "Maria Torres", "department": "Operaciones"},
    "aimee": {"pin": "0000", "full_name": "Aimee", "department": "Desarrollo"}  
}

# ================== RUTA NUEVA PARA REGISTRAR TARJETAS ADMIN ==================

@app.post("/admin/register-card")
async def register_admin_card(admin_data: AdminRegisterRequest):
    """Registrar una nueva tarjeta NFC para administrador"""
    try:
        admin_username = admin_data.username
        admin_password = admin_data.password
        nfc_id = admin_data.nfc_id
        full_name = admin_data.full_name
        
        print(f"🎫 Intentando registrar tarjeta admin: {nfc_id} para {full_name}")
        
        # Verificar credenciales de admin en la base de datos local
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (admin_username,))
        admin = cursor.fetchone()
        
        if not admin:
            conn.close()
            return {"success": False, "message": "Credenciales de administrador inválidas"}
        
        # Verificar contraseña
        password_hash = hashlib.sha256(admin_password.encode()).hexdigest()
        if admin[0] != password_hash:
            conn.close()
            return {"success": False, "message": "Contraseña incorrecta"}
        
        # Registrar la tarjeta como administrador en la base de datos principal
        try:
            # Primero verificar si ya existe un usuario con este NFC ID
            existing_user = database.get_user_by_nfc(nfc_id)
            if existing_user:
                # Actualizar usuario existente como admin
                cursor.execute('''
                    UPDATE users SET 
                    full_name = ?, department = ?, security_level = ?, pin = ?, is_admin = ?
                    WHERE nfc_id = ?
                ''', (full_name, "Administración", "ALTO", "0000", 1, nfc_id))
            else:
                # Insertar nuevo usuario admin
                cursor.execute('''
                    INSERT INTO users (nfc_id, full_name, department, security_level, pin, is_admin)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (nfc_id, full_name, "Administración", "ALTO", "0000", 1))
            
            conn.commit()
            conn.close()
            
            # También actualizar el simulador de Active Directory
            active_directory_users[admin_username.lower()] = {
                "pin": "0000", 
                "full_name": full_name, 
                "department": "Administración"
            }
            
            print(f"✅ Tarjeta de administrador registrada: {full_name} - {nfc_id}")
            
            return {
                "success": True, 
                "message": f"Tarjeta de administrador registrada para {full_name}"
            }
            
        except Exception as e:
            conn.close()
            return {"success": False, "message": f"Error al registrar en base de datos: {str(e)}"}
        
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

@app.post("/authenticate", response_model=AuthResponse)
async def authenticate_user(auth_request: AuthRequest):
    try:
        print(f"🔐 Intento de autenticación: NFC={auth_request.nfc_id}")
        
        # 1. Verificar tarjeta NFC en base de datos
        nfc_user = database.get_user_by_nfc(auth_request.nfc_id)
        if not nfc_user:
            # Registrar intento fallido
            tx_hash = blockchain.record_auth_attempt(
                user_id="unknown",
                timestamp=datetime.now().timestamp(),
                device_id=auth_request.device_id,
                nfc_id=auth_request.nfc_id,
                success=False
            )
            database.log_auth_attempt(0, auth_request.nfc_id, auth_request.device_id, False, tx_hash, "Tarjeta no registrada")
            return AuthResponse(
                success=False,
                message="Tarjeta NFC no registrada en el sistema",
                blockchain_tx=tx_hash
            )
        
        # 2. Verificar PIN con Active Directory (simulado)
        ad_user = active_directory_users.get(nfc_user['username'])
        if not ad_user or ad_user['pin'] != auth_request.pin:
            # Registrar intento fallido
            tx_hash = blockchain.record_auth_attempt(
                user_id=nfc_user['username'],
                timestamp=datetime.now().timestamp(),
                device_id=auth_request.device_id,
                nfc_id=auth_request.nfc_id,
                success=False
            )
            database.log_auth_attempt(nfc_user['id'], auth_request.nfc_id, auth_request.device_id, False, tx_hash, "PIN incorrecto")
            return AuthResponse(
                success=False,
                message="Credenciales inválidas",
                blockchain_tx=tx_hash
            )
        
        # 3. Autenticación exitosa
        tx_hash = blockchain.record_auth_attempt(
            user_id=nfc_user['username'],
            timestamp=datetime.now().timestamp(),
            device_id=auth_request.device_id,
            nfc_id=auth_request.nfc_id,
            success=True
        )
        
        database.log_auth_attempt(nfc_user['id'], auth_request.nfc_id, auth_request.device_id, True, tx_hash)
        
        return AuthResponse(
            success=True,
            message="Autenticación exitosa",
            user={
                "username": nfc_user['username'],
                "full_name": ad_user['full_name'],
                "department": ad_user['department'],
                "security_level": nfc_user['security_level']
            },
            blockchain_tx=tx_hash
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ================== RUTAS PARA SESIONES ==================

@app.post("/session/start")
async def start_session(session_request: SessionStartRequest):
    """Iniciar sesión después de autenticación exitosa"""
    try:
        print(f"🔐 Iniciando sesión: NFC={session_request.nfc_id}")
        
        # Verificar autenticación primero
        nfc_user = database.get_user_by_nfc(session_request.nfc_id)
        if not nfc_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        ad_user = active_directory_users.get(nfc_user['username'])
        if not ad_user or ad_user['pin'] != session_request.pin:
            raise HTTPException(status_code=401, detail="Credenciales inválidas")
        
        # Crear sesión
        session_token = session_manager.create_session(
            nfc_user['id'], 
            session_request.device_id
        )
        
        # Registrar inicio de sesión como actividad
        session_manager.log_activity(
            session_token, 
            "LOGIN", 
            f"Inicio de sesión - {nfc_user['full_name']}"
        )
        
        return {
            "success": True,
            "session_token": session_token,
            "user": {
                "username": nfc_user['username'],
                "full_name": ad_user['full_name'],
                "department": ad_user['department'],
                "security_level": nfc_user['security_level']
            },
            "message": "Sesión iniciada correctamente"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.post("/session/activity")
async def log_activity(activity_request: ActivityRequest):
    """Registrar actividad durante la sesión"""
    session_token = activity_request.session_token
    activity_type = activity_request.activity_type
    description = activity_request.description
    
    if not all([session_token, activity_type, description]):
        raise HTTPException(status_code=400, detail="Datos incompletos")
    
    if not session_manager.is_session_active(session_token):
        raise HTTPException(status_code=401, detail="Sesión no activa")
    
    tx_hash = session_manager.log_activity(session_token, activity_type, description)
    
    if tx_hash:
        return {
            "success": True,
            "activity_logged": True,
            "blockchain_tx": tx_hash,
            "message": "Actividad registrada correctamente"
        }
    else:
        raise HTTPException(status_code=500, detail="Error al registrar actividad")

@app.post("/session/logout")
async def logout_session(logout_request: LogoutRequest):
    """Cerrar sesión"""
    session_token = logout_request.session_token
    
    if not session_token:
        raise HTTPException(status_code=400, detail="Token de sesión requerido")
    
    success = session_manager.logout_user(session_token)
    
    if success:
        return {
            "success": True,
            "message": "Sesión cerrada correctamente"
        }
    else:
        raise HTTPException(status_code=400, detail="Error al cerrar sesión o sesión ya cerrada")

@app.get("/session/activities/{session_token}")
async def get_session_activities(session_token: str):
    """Obtener actividades de una sesión"""
    activities = session_manager.get_session_activities(session_token)
    
    return {
        "success": True,
        "activities": activities,
        "count": len(activities),
        "message": f"Se encontraron {len(activities)} actividades"
    }

@app.get("/session/check/{session_token}")
async def check_session(session_token: str):
    """Verificar si una sesión está activa"""
    is_active = session_manager.is_session_active(session_token)
    
    return {
        "success": True,
        "is_active": is_active,
        "message": "Sesión activa" if is_active else "Sesión inactiva"
    }

@app.get("/sessions/active")
async def get_active_sessions():
    """Obtener todas las sesiones activas"""
    try:
        conn = sqlite3.connect('sessions.db')
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT session_token, user_name, department, start_time 
            FROM sessions 
            WHERE end_time IS NULL
        ''')
        
        active_sessions = []
        for row in cursor.fetchall():
            session_token, user_name, department, start_time = row
            active_sessions.append({
                "session_token": session_token,
                "user_name": user_name,
                "department": department,
                "start_time": start_time
            })
        
        conn.close()
        
        return {
            "success": True,
            "sessions": active_sessions,
            "count": len(active_sessions)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ================== RUTAS EXISTENTES ==================

@app.get("/user/{nfc_id}")
async def get_user_by_nfc(nfc_id: str):
    user = database.get_user_by_nfc(nfc_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user

@app.get("/logs")
async def get_auth_logs(limit: int = 20):
    return database.get_auth_logs(limit)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "nfc_reader": "connected" if nfc_reader.reader else "disconnected",
        "database": "connected",
        "blockchain": "simulated",
        "session_manager": "active"
    }

@app.get("/")
async def root():
    return {
        "message": "Sistema de Autenticación NFC + Blockchain",
        "version": "1.0",
        "endpoints": {
            "authentication": "/authenticate",
            "sessions": "/session/start, /session/activity, /session/logout",
            "admin": "/admin/register-card",
            "users": "/user/{nfc_id}",
            "logs": "/logs",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    print("🚀 Iniciando Servidor de Autenticación NFC + Blockchain")
    print("📍 Servidor disponible en: http://localhost:8000")
    print("📚 Documentación API: http://localhost:8000/docs")
    print("🆕 SISTEMA DE SESIONES ACTIVADO")
    print("👑 ENDPOINT DE ADMIN DISPONIBLE: /admin/register-card")
    uvicorn.run(app, host="0.0.0.0", port=8000)