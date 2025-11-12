from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import uvicorn
from typing import Optional
import hashlib
from fastapi.middleware.cors import CORSMiddleware

from database import DatabaseManager
from blockchain_simulated import BlockchainSimulated
from session_manager import SessionManager

# ------------------- App y CORS -------------------
app = FastAPI(title="Sistema de Autenticación NFC + Blockchain")

# Habilitar CORS para que el frontend pueda hacer fetch
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción reemplaza "*" con la URL de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------- Modelos -------------------
class AuthRequest(BaseModel):
    pin: str
    nfc_id: str
    device_id: str

class AuthResponse(BaseModel):
    success: bool
    message: str
    user: Optional[dict]
    blockchain_tx: Optional[str]

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

class AdminRegisterRequest(BaseModel):
    username: str
    password: str
    nfc_id: str
    full_name: str

# ------------------- Inicialización -------------------
database = DatabaseManager()  # Base de datos local
blockchain = BlockchainSimulated()
session_manager = SessionManager()

# Simulador de Active Directory
active_directory_users = {
    "analopez": {"pin": "1234", "full_name": "Ana Lopez", "department": "Inteligencia"},
    "carlosruiz": {"pin": "5678", "full_name": "Carlos Ruiz", "department": "Analisis"},
    "mariatorres": {"pin": "9012", "full_name": "Maria Torres", "department": "Operaciones"},
    "aimee": {"pin": "0000", "full_name": "Aimee", "department": "Desarrollo"}  
}

# ------------------- ENDPOINTS -------------------
@app.post("/admin/register-card")
async def register_admin_card(admin_data: AdminRegisterRequest):
    try:
        nfc_id = admin_data.nfc_id
        full_name = admin_data.full_name

        existing_user = database.get_user_by_nfc(nfc_id)
        if existing_user:
            database.update_user_as_admin(nfc_id, full_name)
        else:
            database.register_nfc_user_with_pin(
                nfc_id, admin_data.username, full_name, "Administración",
                security_level=3, is_admin=True, pin="0000"
            )

        # Actualizar simulador de AD
        active_directory_users[admin_data.username.lower()] = {
            "pin": "0000",
            "full_name": full_name,
            "department": "Administración"
        }

        return {"success": True, "message": f"Tarjeta de administrador registrada para {full_name}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}

# ------------------- AUTENTICACIÓN -------------------
@app.post("/authenticate", response_model=AuthResponse)
async def authenticate_user(auth_request: AuthRequest):
    try:
        # -------------------- Logs para depuración --------------------
        print("✅ Llega al endpoint /authenticate")
        print("📥 Request recibido:", auth_request)

        nfc_user = database.get_user_by_nfc(auth_request.nfc_id)
        print("🔎 Usuario NFC encontrado:", nfc_user)

        if not nfc_user:
            tx_hash = blockchain.record_auth_attempt(
                "unknown", datetime.now().timestamp(),
                auth_request.device_id, auth_request.nfc_id, False
            )
            database.log_auth_attempt(0, auth_request.nfc_id, auth_request.device_id, False, tx_hash, "Tarjeta no registrada")
            return AuthResponse(success=False, message="Tarjeta NFC no registrada en el sistema", blockchain_tx=tx_hash)

        ad_user = active_directory_users.get(nfc_user.get('username', ''))
        if not ad_user or ad_user.get('pin') != auth_request.pin:
            tx_hash = blockchain.record_auth_attempt(
                nfc_user.get('username', 'unknown'), datetime.now().timestamp(),
                auth_request.device_id, auth_request.nfc_id, False
            )
            database.log_auth_attempt(nfc_user.get('id', 0), auth_request.nfc_id, auth_request.device_id, False, tx_hash, "PIN incorrecto")
            return AuthResponse(success=False, message="Credenciales inválidas", blockchain_tx=tx_hash)

        # -------------------- Autenticación exitosa --------------------
        tx_hash = blockchain.record_auth_attempt(
            nfc_user.get('username'), datetime.now().timestamp(),
            auth_request.device_id, auth_request.nfc_id, True
        )
        database.log_auth_attempt(nfc_user.get('id', 0), auth_request.nfc_id, auth_request.device_id, True, tx_hash)

        return AuthResponse(
            success=True,
            message="Autenticación exitosa",
            user={
                "username": nfc_user.get('username', 'No disponible'),
                "full_name": ad_user.get('full_name', 'No disponible'),
                "department": ad_user.get('department', 'No disponible'),
                "security_level": nfc_user.get('security_level', 0)
            },
            blockchain_tx=tx_hash
        )

    except Exception as e:
        print("⚠️ Error interno en /authenticate:", str(e))
        return AuthResponse(success=False, message=f"Error interno: {str(e)}", blockchain_tx=None)

# ------------------- SESIONES -------------------
@app.post("/session/start")
async def start_session(session_request: SessionStartRequest):
    nfc_user = database.get_user_by_nfc(session_request.nfc_id)
    if not nfc_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    ad_user = active_directory_users.get(nfc_user.get('username', ''))
    if not ad_user or ad_user.get('pin') != session_request.pin:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    session_token = session_manager.create_session(nfc_user.get('id', 0), session_request.device_id)
    session_manager.log_activity(session_token, "LOGIN", f"Inicio de sesión - {nfc_user.get('full_name', 'Desconocido')}")

    return {"success": True, "session_token": session_token, "user": {
        "username": nfc_user.get('username', 'No disponible'),
        "full_name": ad_user.get('full_name', 'No disponible'),
        "department": ad_user.get('department', 'No disponible'),
        "security_level": nfc_user.get('security_level', 0)
    }, "message": "Sesión iniciada correctamente"}

# ------------------- Health y root -------------------
@app.get("/health")
async def health_check():
    return {"status": "healthy",
            "nfc_reader": "simulated",
            "database": "connected",
            "blockchain": "simulated",
            "session_manager": "active"}

@app.get("/")
async def root():
    return {"message": "Sistema NFC + Blockchain", "version": "1.0",
            "endpoints": {"authentication": "/authenticate",
                          "sessions": "/session/start, /session/activity, /session/logout",
                          "admin": "/admin/register-card",
                          "users": "/user/{nfc_id}",
                          "logs": "/logs",
                          "health": "/health"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
