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
            "extracción", "descargando", "exportando", "enviando", "usb",
            "dispositivo", "externo", "correo", "email", "adjunto", "archivo",
            "masivo", "lote", "batch", "gran", "volumen", "confidencial",
            "secreto", "clasificado", "restringido", "sensible"
        ]
        
        self.high_risk_activities = [
            "EXPORTAR_DATOS", "DESCARGA_MASIVA", "COP
