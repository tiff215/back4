import requests
import time
from datetime import datetime
from acr122u_reader import ACR122UReader

class CompleteAuthClient:
    def __init__(self, api_url: str, device_id: str):
        self.api_url = api_url
        self.device_id = device_id
        self.nfc_reader = ACR122UReader()
    
    def start_auth_flow(self):
        print("\n" + "="*60)
        print("       SISTEMA DE AUTENTICACIÓN MFA COMPLETO")
        print("="*60)
         
        # Verificar conexión con servidor
        if not self.check_server_health():
            return False
        
        # Paso 1: Lectura NFC FÍSICA
        print("\n🎫 COLOCAR TARJETA NFC EN EL LECTOR ACR122U...")
        nfc_id = self.nfc_reader.wait_for_card(30)
        
        if not nfc_id:
            print("❌ No se detectó tarjeta NFC")
            return False
        
        # Obtener información del usuario
        user_info = self.get_user_info(nfc_id)
        if not user_info:
            print("❌ Tarjeta no registrada en el sistema")
            return False
        
        print(f"✅ USUARIO DETECTADO: {user_info['full_name']}")
        print(f"   Departamento: {user_info['department']}")
        
        # Paso 2: Ingreso de PIN
        print("\n🔒 INGRESE SU PIN:")
        pin = input("   PIN: ").strip()
        
        if not pin:
            print("❌ PIN requerido")
            return False
        
        # Paso 3: Autenticación COMPLETA
        print("\n⏳ VERIFICANDO CREDENCIALES...")
        auth_result = self.authenticate(pin, nfc_id)
        
        if auth_result.get('success'):
            self.show_success_message(auth_result)
            return True
        else:
            self.show_error_message(auth_result)
            return False
    
    def check_server_health(self):
        """Verificar que el servidor esté funcionando"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                print("✅ Servidor conectado correctamente")
                return True
            else:
                print("❌ Servidor no responde correctamente")
                return False
        except:
            print("❌ No se puede conectar al servidor")
            print("   Ejecute primero: python main.py")
            return False
    
    def get_user_info(self, nfc_id: str):
        try:
            response = requests.get(f"{self.api_url}/user/{nfc_id}", timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def authenticate(self, pin: str, nfc_id: str):
        try:
            auth_data = {
                "pin": pin,
                "nfc_id": nfc_id,
                "device_id": self.device_id
            }
            
            response = requests.post(
                f"{self.api_url}/authenticate",
                json=auth_data,
                timeout=10
            )
            
            return response.json()
            
        except Exception as e:
            return {"success": False, "message": f"Error de conexión: {str(e)}"}
    
    def show_success_message(self, auth_result: dict):
        print("\n" + "🎉" * 25)
        print("        ✅ AUTENTICACIÓN EXITOSA")
        print("🎉" * 25)
        print(f"   👤 Usuario: {auth_result['user']['full_name']}")
        print(f"   🏢 Departamento: {auth_result['user']['department']}")
        print(f"   🔐 Nivel Seguridad: {auth_result['user']['security_level']}")
        print(f"   🔗 Blockchain: {auth_result['blockchain_tx']}")
        print(f"   🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n   🚀 ACCESO CONCEDIDO AL SISTEMA")
    
    def show_error_message(self, auth_result: dict):
        print("\n" + "🚫" * 25)
        print("        ❌ AUTENTICACIÓN FALLIDA")
        print("🚫" * 25)
        print(f"   📛 Razón: {auth_result.get('message', 'Error desconocido')}")
        if auth_result.get('blockchain_tx'):
            print(f"   🔗 Transacción: {auth_result['blockchain_tx']}")
        print(f"   🕐 Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("\n   ⚠️  ACCESO DENEGADO")

if __name__ == "__main__":
    client = CompleteAuthClient("http://localhost:8000", "ACR122U-STATION-01")
    
    try:
        while True:
            success = client.start_auth_flow()
            
            if success:
                continuar = input("\n¿Autenticar otro usuario? (s/n): ").strip().lower()
            else:
                continuar = input("\n¿Reintentar? (s/n): ").strip().lower()
            
            if continuar != 's':
                break
            print("\n" + "-"*60)
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Aplicación interrumpida por el usuario")