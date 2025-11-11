from acr122u_reader import ACR122UReader

def test_lector():
    print("🔍 TESTEO DE LECTOR NFC")
    print("═" * 30)
    
    nfc_reader = ACR122UReader()
    
    print("🎫 Acerca una tarjeta NFC al lector...")
    print("   Tiene 30 segundos")
    
    nfc_id = nfc_reader.wait_for_card(30)
    
    if nfc_id:
        print(f"✅ Tarjeta detectada: {nfc_id}")
        print("🎯 El lector NFC funciona correctamente")
    else:
        print("❌ No se detectó tarjeta")
        print("💡 Verifica:")
        print("   - El lector está conectado")
        print("   - Los drivers están instalados")
        print("   - La tarjeta está en buen estado")

if __name__ == "__main__":
    test_lector()
    input("\nPresiona Enter para salir...")