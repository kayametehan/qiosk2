"""
Kişisel Asistan Bot - Yapılandırma Dosyası
Tüm sabitler, hedefler ve ayarlar burada tanımlı.
"""

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# ─── Bot Token'ları ───────────────────────────────────────
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
TELEGRAM_USER_ID = int(os.getenv("TELEGRAM_USER_ID", "0"))

# ─── AI Model Ayarları ────────────────────────────────────
AI_MODEL = "openai/gpt-4o-mini"
AI_BASE_URL = "https://models.github.ai/inference"

# ─── Kişisel Hedefler ────────────────────────────────────
HEDEFLER = {
    "kilo": {
        "hedef_kg": 75.0,
        "aciklama": "75 kg'a düşmek",
        "kisitlamalar": [
            "Yumurta yemez",
            "Karamelli protein tozu var",
        ],
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

# ─── Hatırlatma Saatleri (saat, dakika) ───────────────────
HATIRLATMALAR = {
    "sabah_plani": (8, 0),
    "ders_hatirlatma_1": (10, 0),
    "ders_hatirlatma_2": (14, 0),
    "ogun_ogle": (12, 30),
    "ogun_aksam": (19, 0),
    "gun_sonu_ozet": (22, 0),
}

# ─── Pomodoro Ayarları ────────────────────────────────────
POMODORO_CALISMA_DK = 25
POMODORO_MOLA_DK = 5

# ─── Veritabanı ──────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "asistan.db")

# ─── AI System Prompt ────────────────────────────────────
SYSTEM_PROMPT = """Sen bir kişisel asistan botsun. Tamamen Türkçe konuşuyorsun. 
Kullanıcının şu hedefleri var:

1. 🏋️ KİLO VERME: 75 kg hedefi var. Yumurta yiyemez, karamelli protein tozu mevcut.
   Yüksek proteinli, düşük kalorili yemek önerilerinde bulun. Protein tozu tariflerini öner.

2. 📚 CENT-S SINAVI: 12 Mart 2026'da. Bu sınav daha yakın, öncelikli.

3. 📚 SAT SINAVI: 14 Mart 2026'da.

Bugünün tarihi: {tarih}
CENT-S sınavına kalan gün: {cents_kalan}
SAT sınavına kalan gün: {sat_kalan}

Kurallar:
- Kısa, motive edici ve samimi cevaplar ver
- Emoji kullan ama abartma  
- Pratik ve uygulanabilir öneriler sun
- Sınav yakınsa stres yapmadan motive et
- Diyet önerilerinde yumurtasız tarifler ver, protein tozu kullanımını teşvik et
- Cevaplarını Telegram mesajı formatında tut (kısa paragraflar, maddeler)
"""
