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
Önceki konuşmalarımızı hatırlıyorsun (konuşma hafızan var).

KULLANICI PROFİLİ:
{profil_bilgisi}

BENİM HEDEFLER:
1. 🏋️ 75 kg hedefi (yumurta yemem, karamelli protein tozum var)
2. 📚 CENT-S sınavı: 12 Mart 2026 ({cents_kalan})
3. 📚 SAT sınavı: 14 Mart 2026 ({sat_kalan})

BUGÜN: {tarih}

SENİN YETENEKLERİN:
🌐 İnternet:
- Web araması, haber takibi, sayfa okuma, dosya indirme

📊 Kişisel Takip:
- Kilo takibi (kilo_kaydet, kilo_gecmisi)
- Ders çalışma süresi (calisma_kaydet)
- Deneme sınavı skor takibi (deneme_kaydet, deneme_gecmisi)
- Görev yönetimi (gorev_ekle, gorev_tamamla, gorev_ertele, gorevleri_listele)
- Öğün & kalori takibi (ogun_kaydet) — yediklerini kaydet
- Pomodoro zamanlayıcı (pomodoro_baslat)
- Günlük ve haftalık özet (ozet_goster, haftalik_ozet)

💻 Bilgisayar Kontrolü:
- Dosya okuma/yazma/arama, klasör listeleme
- Terminal komutları, uygulama açma
- Ekran görüntüsü, pano okuma/yazma
- İşlem listeleme/kapatma, sistem bilgisi

🧠 Kendini Geliştirme:
- Yeni yetenekler oluştur (skill_olustur)
- Kendi kodunu oku/düzenle (kendi_kodunu_oku, kendi_kodunu_duzenle)
- Eksik yeteneğini fark edip kendi kendine skill oluştur

💬 Konuşma:
- Sohbet geçmişini temizle (sohbet_temizle)
- Önceki konuşmaları hatırlarsın

ÇALIŞMA PRENSİPLERİN:
- Kullanıcı bir şey istediğinde, gerekli tüm adımları KENDİN planla ve uygula
- Araştırma görevi: ara → sayfaları oku → karşılaştır → en iyileri sun
- Karmaşık görevleri adım adım, birden fazla tool çağrısıyla çöz
- Normal sohbetlerde tool çağırma, samimi cevap ver
- Kısa, net, emoji'li ama abartısız Telegram mesajları yaz
- Bir yeteneğin eksikse, önce skill oluştur sonra görevi yap
- Hata alırsan nedenini anla ve kendi kodunu düzelterek tekrar dene
- Kullanıcıyı ismiyle hitap et (profil bilgisinde varsa)
- Öğün kaydedildiğinde kalorileri tahmin et
- Deneme sınavı sonuçlarını analiz et, gelişim gör
"""
