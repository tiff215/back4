from database import DatabaseManager
from acr122u_reader import ACR122UReader
import time
import os

def check_card():
    """Verificar tarjeta NFC - Con LECTURA REAL"""
    
    print("=" * 50)
    print("🔍 VERIFICACIÓN DE TARJETA NFC")
    print("=" * 50)
    
    # Inicializar base de datos
    db = DatabaseManager()
    
    print("\n🎫 Acerca la tarjeta NFC al lector...")
    print("   Tiene 30 segundos para acercar la tarjeta")
    
    # LECTURA REAL DE TARJETA NFC
    try:
        nfc_reader = ACR122UReader()
        tarjeta_detectada = nfc_reader.wait_for_card(30)
        
        if not tarjeta_detectada:
            print("❌ Tiempo agotado - No se detectó tarjeta")
            return
        
        print(f"✅ Tarjeta detectada: {tarjeta_detectada}")
        
    except Exception as e:
        print(f"❌ Error con el lector NFC: {e}")
        print("💡 Modo manual activado")
        tarjeta_detectada = input("Ingresa el UID de la tarjeta: ").strip().upper()
        
        if not tarjeta_detectada:
            print("❌ UID requerido")
            return
    
    # Verificar en base de datos
    usuario = db.get_user_by_nfc(tarjeta_detectada)
    
    if usuario:
        print(f"\n✅ USUARIO REGISTRADO")
        print(f"   👤 Nombre: {usuario['full_name']}")
        print(f"   🏢 Departamento: {usuario['department']}")
        print(f"   🔒 Nivel seguridad: {usuario['security_level']}")
        print(f"   🔑 Administrador: {'Sí' if usuario['is_admin'] else 'No'}")
        print(f"   ✅ Estado: {'Activo' if usuario['is_active'] else 'Inactivo'}")
    else:
        print(f"\n❌ TARJETA NO REGISTRADA")
        print(f"   🎫 NFC ID: {tarjeta_detectada}")
        print(f"   💡 Contacte al administrador para registrar esta tarjeta")

def check_multiple_cards():
    """Verificar múltiples tarjetas de prueba"""
    db = DatabaseManager()
    
    tarjetas_prueba = [
        "04A1B2C3D4E5",  # Ana Lopez
        "04F6G7H8I9J0",  # Carlos Ruiz  
        "04K1L2M3N4O5",  # Maria Torres
        "A0F9001E",      # Aimee
        "6C15001E",      # Adrián Bautista
        "INVALIDO123"    # Tarjeta no registrada
    ]
    
    print("\n🧪 VERIFICANDO TARJETAS DE PRUEBA")
    print("=" * 50)
    
    for tarjeta in tarjetas_prueba:
        usuario = db.get_user_by_nfc(tarjeta)
        
        if usuario:
            admin_status = " 🔑 ADMIN" if usuario['is_admin'] else ""
            print(f"✅ {tarjeta}: {usuario['full_name']} - Nivel {usuario['security_level']}{admin_status}")
        else:
            print(f"❌ {tarjeta}: NO REGISTRADA")
    
    print(f"\n📊 Resumen: {len([t for t in tarjetas_prueba if db.get_user_by_nfc(t)])} registradas de {len(tarjetas_prueba)}")

def show_all_users():
    """Mostrar todos los usuarios registrados (solo para verificación)"""
    db = DatabaseManager()
    usuarios = db.get_all_users()
    
    print(f"\n👥 USUARIOS REGISTRADOS EN EL SISTEMA ({len(usuarios)})")
    print("=" * 60)
    
    for usuario in usuarios:
        admin_status = " 🔑 ADMIN" if usuario['is_admin'] else ""
        estado = "✅ Activo" if usuario.get('is_active', True) else "❌ Inactivo"
        print(f"   🎫 {usuario['nfc_id']}")
        print(f"   👤 {usuario['full_name']} ({usuario['username']})")
        print(f"   🏢 {usuario['department']} - Nivel {usuario['security_level']}{admin_status}")
        print(f"   {estado}")
        print("   " + "-" * 40)

if __name__ == "__main__":
    print("🔍 SISTEMA DE VERIFICACIÓN NFC")
    print("1. Verificar tarjeta (LECTURA REAL)")
    print("2. Verificar tarjetas de prueba")
    print("3. Mostrar todos los usuarios")
    print("4. Salir")
    
    opcion = input("\nSeleccione opción (1-4): ").strip()
    
    if opcion == "1":
        check_card()
    elif opcion == "2":
        check_multiple_cards()
    elif opcion == "3":
        show_all_users()
    elif opcion == "4":
        print("👋 ¡Hasta pronto!")
    else:
        print("❌ Opción no válida")
    
    input("\nPresiona Enter para salir...")