from database import DatabaseManager
from acr122u_reader import ACR122UReader
import hashlib
import secrets

def register_my_card():
    """Registrar tarjeta NFC física con LECTURA REAL Y PIN"""
    
    # Inicializar base de datos
    db = DatabaseManager()
    
    print("=" * 50)
    print("🔐 REGISTRO DE TARJETA NFC")
    print("=" * 50)
    
    # Solicitar datos del usuario
    print("\n📝 Ingresa tus datos:")
    
    # LECTURA REAL DE TARJETA NFC
    print("\n🔰 Acerca la nueva tarjeta NFC...")
    print("   Tiene 30 segundos para acercar la tarjeta")
    
    try:
        nfc_reader = ACR122UReader()
        tarjeta_detectada = nfc_reader.wait_for_card(30)
        
        if not tarjeta_detectada:
            print("❌ Tiempo agotado - No se detectó tarjeta")
            return False
        
        print(f"✅ Tarjeta detectada: {tarjeta_detectada}")
        
    except Exception as e:
        print(f"❌ Error con el lector NFC: {e}")
        print("💡 Modo manual activado - Ingresa el UID manualmente")
        tarjeta_detectada = input("Ingresa el UID de tu tarjeta NFC: ").strip().upper()
        
        if not tarjeta_detectada:
            print("❌ UID requerido")
            return False
    
    # Verificar si la tarjeta ya está registrada
    usuario_existente = db.get_user_by_nfc(tarjeta_detectada)
    if usuario_existente:
        print(f"❌ La tarjeta {tarjeta_detectada} ya está registrada")
        print(f"   👤 Usuario: {usuario_existente['full_name']}")
        print(f"   🏢 Departamento: {usuario_existente['department']}")
        return False
    
    # Datos del usuario
    tu_nombre = input("Nombre completo: ").strip()
    if not tu_nombre:
        print("❌ Debes ingresar un nombre completo")
        return False
    
    tu_usuario = input("Usuario (sin espacios): ").strip().lower()
    if not tu_usuario:
        print("❌ Debes ingresar un nombre de usuario")
        return False
    
    tu_departamento = input("Departamento: ").strip()
    if not tu_departamento:
        tu_departamento = "General"
    
    # Nivel de seguridad
    print("\n🔒 Niveles de seguridad disponibles:")
    print("   1 - Básico (Acceso general)")
    print("   2 - Estándar (Acceso a áreas restringidas)")
    print("   3 - Alto (Acceso administrativo)")
    
    try:
        nivel_seguridad = int(input("Nivel de seguridad (1-3): ").strip())
        if nivel_seguridad not in [1, 2, 3]:
            print("⚠️  Nivel no válido. Usando nivel 1 por defecto")
            nivel_seguridad = 1
    except ValueError:
        print("⚠️  Nivel no válido. Usando nivel 1 por defecto")
        nivel_seguridad = 1
    
    # ¿Es administrador?
    es_admin_input = input("¿Es usuario administrador? (s/n): ").strip().lower()
    es_admin = es_admin_input in ['s', 'si', 'sí', 'y', 'yes']
    
    # PIN temporal
    pin_temporal = "0000"  # PIN por defecto para todos los usuarios nuevos
    
    # Confirmar registro
    print(f"\n📋 RESUMEN DEL REGISTRO:")
    print(f"   🎫 Tarjeta NFC: {tarjeta_detectada}")
    print(f"   👤 Nombre: {tu_nombre}")
    print(f"   👨‍💼 Usuario: {tu_usuario}")
    print(f"   🏢 Departamento: {tu_departamento}")
    print(f"   🔒 Nivel seguridad: {nivel_seguridad}")
    print(f"   🔑 Administrador: {'Sí' if es_admin else 'No'}")
    print(f"   🔐 PIN temporal: {pin_temporal}")
    
    confirmar = input("\n¿Confirmar registro? (s/n): ").strip().lower()
    
    if confirmar not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Registro cancelado")
        return False
    
    # Registrar usuario CON PIN
    if db.register_nfc_user_with_pin(
        nfc_id=tarjeta_detectada,
        username=tu_usuario,
        full_name=tu_nombre,
        department=tu_departamento,
        security_level=nivel_seguridad,
        is_admin=es_admin,
        pin=pin_temporal
    ):
        print(f"\n✅ REGISTRO EXITOSO")
        print(f"   🎫 Tarjeta: {tarjeta_detectada}")
        print(f"   👤 Usuario: {tu_nombre}")
        print(f"   🔑 Tipo: {'Administrador' if es_admin else 'Usuario estándar'}")
        print(f"   🔒 Nivel: {nivel_seguridad}")
        print(f"   🔐 PIN temporal: {pin_temporal}")
        print("   ⚠️  Cambia tu PIN después del primer acceso")
        
        # Mostrar información adicional
        usuario_registrado = db.get_user_by_nfc(tarjeta_detectada)
        if usuario_registrado:
            print(f"\n📊 Información del usuario:")
            print(f"   🆔 ID: {usuario_registrado['id']}")
            print(f"   📧 Usuario: {usuario_registrado['username']}")
            print(f"   🏢 Departamento: {usuario_registrado['department']}")
            print(f"   🔐 Nivel seguridad: {usuario_registrado['security_level']}")
            print(f"   🔑 Administrador: {'Sí' if usuario_registrado['is_admin'] else 'No'}")
            print(f"   🔐 PIN: {usuario_registrado['pin']}")
        
        return True
    else:
        print("❌ Error al registrar la tarjeta en la base de datos")
        return False

def register_multiple_cards():
    """Registrar múltiples tarjetas (para testing)"""
    db = DatabaseManager()
    
    # Tarjetas de ejemplo para registrar CON PIN
    tarjetas_ejemplo = [
        {"nfc_id": "04A1B2C3D4E5", "username": "analopez", "full_name": "Ana Lopez", "department": "Inteligencia", "security_level": 3, "is_admin": False, "pin": "0000"},
        {"nfc_id": "04F6G7H8I9J0", "username": "carlosruiz", "full_name": "Carlos Ruiz", "department": "Analisis", "security_level": 2, "is_admin": False, "pin": "0000"},
        {"nfc_id": "04K1L2M3N4O5", "username": "mariatorres", "full_name": "Maria Torres", "department": "Operaciones", "security_level": 2, "is_admin": False, "pin": "0000"},
    ]
    
    print("🔄 Registrando tarjetas de ejemplo...")
    
    for tarjeta in tarjetas_ejemplo:
        success = db.register_nfc_user_with_pin(
            nfc_id=tarjeta["nfc_id"],
            username=tarjeta["username"],
            full_name=tarjeta["full_name"],
            department=tarjeta["department"],
            security_level=tarjeta["security_level"],
            is_admin=tarjeta["is_admin"],
            pin=tarjeta["pin"]
        )
        
        if success:
            print(f"✅ {tarjeta['full_name']} - {tarjeta['nfc_id']} - PIN: {tarjeta['pin']}")
        else:
            print(f"❌ {tarjeta['full_name']} - YA REGISTRADO")
    
    print("✅ Proceso de registro completado")

def show_registered_users():
    """Mostrar todos los usuarios registrados CON PIN"""
    db = DatabaseManager()
    usuarios = db.get_all_users()
    
    print(f"\n👥 USUARIOS REGISTRADOS ({len(usuarios)}):")
    print("=" * 70)
    
    for usuario in usuarios:
        admin_status = " 🔑 ADMIN" if usuario['is_admin'] else ""
        print(f"   🎫 {usuario['nfc_id']}")
        print(f"   👤 {usuario['full_name']} ({usuario['username']})")
        print(f"   🏢 {usuario['department']} - Nivel {usuario['security_level']}{admin_status}")
        print(f"   🔐 PIN: {usuario['pin']}")
        print("   " + "-" * 50)

def change_user_pin():
    """Cambiar PIN de usuario existente ACERCANDO TARJETA"""
    db = DatabaseManager()
    
    print("\n🔄 CAMBIAR PIN DE USUARIO")
    print("=" * 40)
    
    print("🎫 Acerca la tarjeta del usuario al lector...")
    print("   Tiene 30 segundos para acercar la tarjeta")
    
    try:
        nfc_reader = ACR122UReader()
        nfc_id = nfc_reader.wait_for_card(30)
        
        if not nfc_id:
            print("❌ Tiempo agotado - No se detectó tarjeta")
            return False
        
        print(f"✅ Tarjeta detectada: {nfc_id}")
        
    except Exception as e:
        print(f"❌ Error con el lector NFC: {e}")
        print("💡 Modo manual activado")
        nfc_id = input("Ingresa el NFC ID del usuario: ").strip().upper()
        
        if not nfc_id:
            print("❌ NFC ID requerido")
            return False
    
    # Verificar si el usuario existe
    usuario = db.get_user_by_nfc(nfc_id)
    if not usuario:
        print(f"❌ No se encontró usuario con NFC: {nfc_id}")
        return False
    
    print(f"\n📋 USUARIO IDENTIFICADO:")
    print(f"   👤 Nombre: {usuario['full_name']}")
    print(f"   🏢 Departamento: {usuario['department']}")
    print(f"   🔒 Nivel seguridad: {usuario['security_level']}")
    print(f"   🔑 Administrador: {'Sí' if usuario['is_admin'] else 'No'}")
    print(f"   🔐 PIN actual: {usuario['pin']}")
    
    # Solicitar nuevo PIN
    nuevo_pin = input("\n🔐 Ingresa el nuevo PIN (4 dígitos): ").strip()
    
    # Validar PIN
    if not nuevo_pin or len(nuevo_pin) != 4 or not nuevo_pin.isdigit():
        print("❌ El PIN debe ser de 4 dígitos numéricos")
        return False
    
    if nuevo_pin == usuario['pin']:
        print("❌ El nuevo PIN no puede ser igual al actual")
        return False
    
    # Confirmar cambio
    print(f"\n📋 CONFIRMACIÓN:")
    print(f"   🎫 Tarjeta: {nfc_id}")
    print(f"   👤 Usuario: {usuario['full_name']}")
    print(f"   🔐 PIN actual: {usuario['pin']}")
    print(f"   🔐 Nuevo PIN: {nuevo_pin}")
    
    confirmar = input("\n¿Confirmar cambio de PIN? (s/n): ").strip().lower()
    
    if confirmar not in ['s', 'si', 'sí', 'y', 'yes']:
        print("❌ Cambio de PIN cancelado")
        return False
    
    # Actualizar PIN
    if db.update_user_pin(nfc_id, nuevo_pin):
        print(f"\n✅ PIN ACTUALIZADO CORRECTAMENTE")
        print(f"   👤 Usuario: {usuario['full_name']}")
        print(f"   🎫 Tarjeta: {nfc_id}")
        print(f"   🔐 Nuevo PIN: {nuevo_pin}")
        print("   💡 El usuario debe usar este nuevo PIN para iniciar sesión")
        return True
    else:
        print("❌ Error al actualizar el PIN en la base de datos")
        return False

if __name__ == "__main__":
    print("🔐 SISTEMA DE REGISTRO NFC")
    print("1. Registrar mi tarjeta")
    print("2. Registrar tarjetas de ejemplo")
    print("3. Mostrar usuarios registrados")
    print("4. Cambiar PIN de usuario")
    print("5. Salir")
    
    opcion = input("\nSelecciona una opción (1-5): ").strip()
    
    if opcion == "1":
        register_my_card()
    elif opcion == "2":
        register_multiple_cards()
    elif opcion == "3":
        show_registered_users()
    elif opcion == "4":
        change_user_pin()
    elif opcion == "5":
        print("👋 ¡Hasta pronto!")
    else:
        print("❌ Opción no válida")
    
    input("\nPresiona Enter para salir...")