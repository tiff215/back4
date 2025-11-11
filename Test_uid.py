from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.CardConnection import CardConnection

r = readers()
if not r:
    print("No hay lectores detectados. Revisa drivers o el servicio Smart Card.")
    exit(1)

reader = r[0]
print("Usando lector:", reader)
conn = reader.createConnection()
conn.connect(CardConnection.T1_protocol)

# Comando APDU para obtener el UID
apdu = [0xFF, 0xCA, 0x00, 0x00, 0x00]
data, sw1, sw2 = conn.transmit(apdu)

print("SW1 SW2:", hex(sw1), hex(sw2))
if (sw1, sw2) == (0x90, 0x00):
    print("UID de la tarjeta:", toHexString(data))
else:
    print("No se pudo leer el UID.")

