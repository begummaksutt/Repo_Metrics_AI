"""
Gemini API Test Scripti
Çalıştır: python test_gemini.py
"""

import os
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

def test_api_key():
    """API key varlığını kontrol et."""
    key = os.getenv("GOOGLE_API_KEY")
    
    if not key:
        print("❌ GOOGLE_API_KEY bulunamadı!")
        print("   .env dosyasına ekleyin: GOOGLE_API_KEY=AIzaSyXXXXX")
        return False
    
    print(f"✅ API Key bulundu: {key[:15]}...")
    return True


def test_gemini_connection():
    """Gemini bağlantısını test et."""
    try:
        import google.generativeai as genai
    except ImportError:
        print("❌ google-generativeai paketi yüklü değil!")
        print("   Yükleyin: pip install google-generativeai")
        return False
    
    key = os.getenv("GOOGLE_API_KEY")
    genai.configure(api_key=key)
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content("Sadece 'Merhaba, çalışıyorum!' yaz.")
        
        print(f"✅ Gemini bağlantısı başarılı!")
        print(f"   Yanıt: {response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Gemini hatası: {e}")
        return False


def test_llm_module():
    """analytics/llm.py modülünü test et."""
    try:
        from analytics.llm import LLMClient, generate_quality_report
        
        # LLMClient ile test
        client = LLMClient(
            provider="gemini",
            api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        response = client.generate("Merhaba, kısa bir test yanıtı ver.")
        
        if response.success:
            print(f"✅ LLM modülü çalışıyor!")
            print(f"   Yanıt: {response.content[:100]}...")
            return True
        else:
            print(f"❌ LLM hatası: {response.error}")
            return False
            
    except Exception as e:
        print(f"❌ LLM modül hatası: {e}")
        return False


if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Gemini API Test")
    print("=" * 50)
    print()
    
    # Test 1: API Key
    print("1️⃣ API Key Kontrolü...")
    if not test_api_key():
        exit(1)
    print()
    
    # Test 2: Gemini Bağlantısı
    print("2️⃣ Gemini Bağlantı Testi...")
    if not test_gemini_connection():
        exit(1)
    print()
    
    # Test 3: LLM Modülü
    print("3️⃣ LLM Modülü Testi...")
    test_llm_module()
    print()
    
    print("=" * 50)
    print("✅ Tüm testler tamamlandı!")
    print("=" * 50)

