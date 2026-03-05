"""
Kişisel Asistan Bot - Yapılandırma
Tamamen sohbet odaklı, tam yerel erişimli AI ajan.
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
AI_BASE_URL = "https://models.github.ai/inference"

# ─── Ajan Ayarları ─────────────────────────────────────────
MAX_AGENT_STEPS = 15  # Bir görevde maksimum adım sayısı
AGENT_TIMEOUT = 120   # Saniye cinsinden timeout

# ─── Kişisel Hedefler ─────────────────────────────────────
HEDEFLER = {
    "kilo": {
        "hedef_kg": 75.0,
        "aciklama": "75 kg'a düşmek",
        "kisitlamalar": ["Yumurta yemez", "Karamelli protein tozu var"],
    },
    "sat": {
        "sinav_tarihi": date(2026, 3, 14),
        "aciklama": "SAT Sınavı",
    },
    "cents": {
        "sinav_tarihi": date(2026, 3, 12),
        "aciklama": "CENT-S Sınavı",
    },
}

# ─── Hatırlatma Saatleri ───────────────────────────────────
HATIRLATMALAR = {
    "sabah_plani": (8, 0),
    "ders_hatirlatma_1": (10, 0),
    "ders_hatirlatma_2": (14, 0),
    "ogun_ogle": (12, 30),
    "ogun_aksam": (19, 0),
    "gun_sonu_ozet": (22, 0),
}

# ─── Pomodoro ──────────────────────────────────────────────
POMODORO_CALISMA_DK = 25
POMODORO_MOLA_DK = 5

# ─── Veritabanı ───────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "asistan.db")

# ─── System Prompt ─────────────────────────────────────────
SYSTEM_PROMPT = """Sen benim kişisel AI asistanımsın. Bilgisayarıma tam erişimin var.
Türkçe konuşuyorsun. Samimi, doğal ve arkadaşça davranıyorsun.

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
- Kilo, çalışma, görev takibi yapabilirsin

ÇALIŞMA PRENSİPLERİN:
- Kullanıcı bir şey istediğinde, gerekli tüm adımları KENDIN planla ve uygula
- Bir araştırma görevi geldiğinde: ara → sayfaları oku → karşılaştır → en iyi sonuçları sun
- Tek seferde birden fazla tool çağrısı yapabilirsin, karmaşık görevleri adım adım çöz
- Her adımda ne yaptığını kısaca açıkla
- Sonuçları düzenli ve okunabilir şekilde sun
- Normal sohbetlerde tool çağırma, sadece doğal cevap ver
- Kısa, net, emoji'li ama abartısız mesajlar yaz
"""
