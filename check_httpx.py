"""
Script pour vérifier si httpx est installé correctement
"""
import sys

try:
    import httpx
    print(f"✅ httpx est installé - Version: {httpx.__version__}")
    print(f"✅ Import réussi")
    
    # Test basique
    import asyncio
    
    async def test_httpx():
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://httpbin.org/get")
            print(f"✅ Test de requête HTTP réussi - Status: {response.status_code}")
    
    asyncio.run(test_httpx())
    print("\n✅ Tous les tests sont passés!")
    
except ImportError as e:
    print(f"❌ httpx n'est pas installé: {e}")
    print("\n💡 Pour installer httpx:")
    print("   pip install httpx")
    sys.exit(1)
except Exception as e:
    print(f"❌ Erreur lors du test: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
