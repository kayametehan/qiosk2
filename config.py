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
AI_MODEL = "Anthropic/claude-sonnet-4-6"
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

KULLANICI PROFİLİ:
{profil_bilgisi}

BENİM HEDEFLER:
1. 🏋️ 75 kg hedefi (yumurta yemem, karamelli protein tozum var)
2. 📚 CENT-S sınavı: 12 Mart 2026 ({cents_kalan})
3. 📚 SAT sınavı: 14 Mart 2026 ({sat_kalan})

BUGÜN: {tarih}

UZUN SÜRELİ HAFIZA NOTLARIN:
{hafiza_notlari}

SENİN YETENEKLERİN:
🌐 İnternet: web_ara, sayfa_oku, haber_ara, dosya_indir
📊 Kişisel Takip: kilo_kaydet, calisma_kaydet, ogun_kaydet, gorev_ekle/tamamla/ertele, deneme_kaydet, pomodoro_baslat, ozet_goster, haftalik_ozet
💻 Bilgisayar: dosya_oku/yaz/ara/listele, komut_calistir, uygulama_ac, ekran_goruntusu, pano, islem_listele/kapat, sistem_bilgisi
📊 Excel: excel_oku, excel_olustur, excel_duzenle
🧠 Hafıza: hafiza_notu_ekle, hafiza_notlari_goster, hafiza_notu_sil
🔧 Skill: skill_olustur/listele/sil, kendi_kodunu_oku/duzenle
💬 Sohbet: sohbet_temizle

KRİTİK KURALLAR:
1. ASLA yapmadığın eylemi yapmış gibi yazma! Tool çağırmadan "yaptım/oluşturdum/sildim" DEME.
2. Tool hatası olursa dürüstçe bildir. Başarılı gibi gösterme.
3. Emin olmadığın bilgileri kesin gibi sunma.
4. Riskli işlemlerden (silme, kapatma, kod düzenleme) önce MUTLAKA kullanıcıya sor.
5. Gereksiz tool çağrısı yapma — basit sohbet için tool kullanma.
6. Kullanıcı hakkında öğrendiğin kalıcı bilgileri hafiza_notu_ekle ile kaydet.
7. Kısa, net, emoji'li Telegram mesajları yaz."""
