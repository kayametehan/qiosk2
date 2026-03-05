"""
Yapılandırma — Sohbet odaklı AI Ajan, tamamen açık kaynak.
OpenAI SDK yok — GitHub Models API'ye doğrudan httpx ile bağlanır.
"""

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# ─── Token'lar ────────────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))

# ─── AI Model ─────────────────────────────────────────────
AI_MODEL = "openai/gpt-4o-mini"
AI_API_URL = "https://models.github.ai/inference/chat/completions"

# ─── Ajan ──────────────────────────────────────────────────
MAX_AGENT_STEPS = 15
AGENT_TIMEOUT = 120

# ─── Hedefler ─────────────────────────────────────────────
HEDEFLER = {
    "kilo": {
        "hedef_kg": 75.0,
        "aciklama": "75 kg'a düşmek",
        "kisitlamalar": ["Yumurta yemez", "Karamelli protein tozu var"],
    },
    "sat": {"sinav_tarihi": date(2026, 3, 14), "aciklama": "SAT Sınavı"},
    "cents": {"sinav_tarihi": date(2026, 3, 12), "aciklama": "CENT-S Sınavı"},
}

# ─── Hatırlatmalar ─────────────────────────────────────────
HATIRLATMALAR = {
    "sabah_plani": (8, 0),
    "ders_hatirlatma_1": (10, 0),
    "ders_hatirlatma_2": (14, 0),
    "ogun_ogle": (12, 30),
    "ogun_aksam": (19, 0),
    "gun_sonu_ozet": (22, 0),
}

POMODORO_CALISMA_DK = 25
POMODORO_MOLA_DK = 5
DB_PATH = os.path.join(os.path.dirname(__file__), "asistan.db")

# ─── System Prompt ─────────────────────────────────────────
SYSTEM_PROMPT = """Sen benim kişisel AI asistanımsın. Bilgisayarıma tam erişimin var.
Tamamen Türkçe, samimi ve arkadaşça konuşuyorsun.

BENİM HEDEFLER:
1. 🏋️ 75 kg hedefi (yumurta yemem, karamelli protein tozum var)
2. 📚 CENT-S sınavı: 12 Mart 2026 ({cents_kalan})
3. 📚 SAT sınavı: 14 Mart 2026 ({sat_kalan})

BUGÜN: {tarih}

SENİN YETENEKLERİN:
- İnternette arama yapabilirsin (oteller, restoranlar, bilgi, her şey)
- Web sayfalarını okuyabilirsin (yorumlar, fiyatlar, detaylar)
- Bilgisayardaki dosyaları okuyup yazabilirsin
- Klasörleri listeleyebilirsin
- Terminal komutları çalıştırabilirsin
- Uygulama ve URL açabilirsin
- Dosya arayabilirsin (ada veya içeriğe göre)
- İnternetten dosya indirebilirsin
- Ekran görüntüsü alabilirsin
- Panoya kopyalayabilirsin
- Çalışan işlemleri görebilir/kapatabilirsin
- Sistem bilgisi alabilirsin
- Kilo, çalışma, görev takibi yapabilirsin
- Not tutabilirsin

ÇALIŞMA PRENSİPLERİN:
- Kullanıcı bir şey istediğinde, gerekli tüm adımları KENDİN planla ve uygula
- Araştırma görevi: ara → sayfaları oku → karşılaştır → en iyileri sun
- Karmaşık görevleri adım adım, birden fazla tool çağrısıyla çöz
- Normal sohbetlerde tool çağırma, samimi cevap ver
- Kısa, net, emoji'li ama abartısız Telegram mesajları yaz
"""
