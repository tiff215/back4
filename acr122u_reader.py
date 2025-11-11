import time
from typing import Optional, Callable

from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.CardConnection import CardConnection
import smartcard

class ACR122UReader:
    def __init__(self):
        self.reader = None
        self.connection = None
        self.monitoring = False
        self.current_card_uid = None
        self.card_removed_callback = None
        
        # Base de datos de usuarios
        self.registered_users = {
            "04A1B2C3D4E5": "Ana Lopez",
            "04F6G7H8I9J0": "Carlos Ruiz", 
            "04K1L2M3N4O5": "Maria Torres",
            "A0F9001E": "Aimee"
        }
        self.initialize_reader()

    # ---------- util ----------
    @staticmethod
    def _normalize_uid(uid_bytes) -> str:
        return ''.join(f'{b:02X}' for b in uid_bytes)

    def _get_user_name(self, uid: str) -> str:
        """Obtener nombre del usuario sin mostrar el UID"""
        return self.registered_users.get(uid, "Usuario No Registrado")

    # ---------- setup ----------
    def initialize_reader(self) -> bool:
        """Detecta el lector y selecciona el primero disponible."""
        try:
            available_readers = readers()
            if not available_readers:
                print("❌ No se encontraron lectores ACR122U conectados")
                return False

            print(f"✅ Lector NFC detectado")
            self.reader = available_readers[0]
            return True
        except Exception as e:
            print(f"❌ Error inicializando lector: {e}")
            return False

    def connect_to_reader(self) -> bool:
        """Conecta al lector ACR122U usando T=1 (contactless)."""
        try:
            if not self.reader:
                print("❌ Lector no inicializado")
                return False

            self.connection = self.reader.createConnection()
            self.connection.connect(CardConnection.T1_protocol)
            return True

        except smartcard.Exceptions.NoCardException:
            return False
        except Exception as e:
            print(f"❌ Error conectando al lector: {e}")
            return False

    # ---------- lectura ----------
    def read_nfc_card(self) -> Optional[str]:
        """Lee una tarjeta NFC (UID). Devuelve None si no hay tarjeta."""
        try:
            if not self.connection:
                if not self.connect_to_reader():
                    return None

            # APDU para obtener UID (ACR122U)
            get_uid = [0xFF, 0xCA, 0x00, 0x00, 0x00]
            data, sw1, sw2 = self.connection.transmit(get_uid)

            if (sw1, sw2) == (0x90, 0x00):
                uid_hex = self._normalize_uid(data)
                return uid_hex
            else:
                return None

        except smartcard.Exceptions.NoCardException:
            return None
        except smartcard.Exceptions.CardConnectionException as e:
            self.connection = None
            return None
        except Exception as e:
            print(f"⚠️  Error leyendo tarjeta: {e}")
            return None

    def wait_for_card(self, timeout: int = 30) -> Optional[str]:
        """Espera una tarjeta hasta 'timeout' segundos con mensajes de progreso."""
        print(f"\n🎫 TIENE {timeout} SEGUNDOS PARA ACERCAR LA TARJETA NFC")
        print("   (Coloque la tarjeta sobre el lector)")
        
        start_time = time.time()
        last_progress = 0
        
        while time.time() - start_time < timeout:
            elapsed = int(time.time() - start_time)
            remaining = timeout - elapsed
            
            # Mostrar progreso cada 5 segundos
            if elapsed != last_progress and elapsed % 5 == 0:
                print(f"⏰ Tiempo restante: {remaining} segundos...")
                last_progress = elapsed
            
            # Intentar conectar si no hay conexión
            if not self.connection:
                if not self.connect_to_reader():
                    time.sleep(0.5)
                    continue

            # Intentar leer tarjeta
            uid = self.read_nfc_card()
            if uid:
                user_name = self._get_user_name(uid)
                print(f"✅ Tarjeta detectada: {user_name}")
                self.current_card_uid = uid
                return uid

            time.sleep(0.3)  # Pequeña pausa entre intentos

        print(f"⏰ Timeout: No se detectó tarjeta en {timeout} segundos")
        return None

    # ---------- monitoreo continuo ----------
    def start_card_monitoring(self, card_removed_callback: Callable = None):
        """Inicia el monitoreo continuo de la tarjeta"""
        if not self.connection:
            print("❌ No hay conexión al lector para monitorear")
            return False
        
        self.card_removed_callback = card_removed_callback
        self.monitoring = True
        print("🔍 Monitoreo activo - Detectando remoción de tarjeta...")
        return True

    def check_card_presence(self) -> bool:
        """Verifica si la tarjeta sigue presente"""
        try:
            if not self.connection or not self.monitoring:
                return False

            # Intentar leer la tarjeta actual
            current_uid = self.read_nfc_card()
            
            # Si no hay tarjeta o la tarjeta cambió
            if not current_uid or current_uid != self.current_card_uid:
                if self.current_card_uid:  # Solo si había una tarjeta antes
                    print("⚠️  ¡TARJETA REMOVIDA!")
                    if self.card_removed_callback:
                        self.card_removed_callback()
                self.current_card_uid = None
                self.monitoring = False
                return False
            
            return True

        except Exception as e:
            print(f"⚠️  Error en monitoreo: {e}")
            return False

    def stop_monitoring(self):
        """Detiene el monitoreo de la tarjeta"""
        self.monitoring = False
        self.current_card_uid = None
        print("🔍 Monitoreo desactivado")

    # ---------- métodos adicionales ----------
    def get_user_by_uid(self, uid: str) -> str:
        """Obtener nombre del usuario por UID"""
        return self._get_user_name(uid)

    # ---------- pruebas / cierre ----------
    def test_connection(self) -> bool:
        """Prueba de conexión básica"""
        if not self.reader:
            return False
        try:
            self.connection = self.reader.createConnection()
            self.connection.connect()
            return True
        except:
            return False

    def disconnect(self):
        try:
            if self.connection:
                self.connection.disconnect()
                self.connection = None
                self.stop_monitoring()
        except:
            pass
