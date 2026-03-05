# 🤖 Kişisel Asistan Telegram Botu

AI destekli, haftalık plan oluşturan ve hedeflerini takip eden kişisel Telegram asistanı.

## 🎯 Özellikler

- **📅 AI ile Günlük Plan** — GPT-4o-mini ile kişiselleştirilmiş günlük program
- **⚖️ Kilo Takibi** — Günlük kilo kaydı, trend analizi, hedef takibi
- **📚 Çalışma Takibi** — SAT & CENT-S sınavlarına çalışma kaydı ve istatistik
- **🍽️ Diyet Önerileri** — Yumurtasız, protein tozlu öğün planları (AI ile)
- **⏱️ Pomodoro Zamanlayıcı** — 25dk çalış / 5dk mola döngüsü
- **📋 Görev Yönetimi** — Günlük görev ekleme, tamamlama, erteleme
- **🔔 Otomatik Hatırlatmalar** — Sabah planı, ders hatırlatması, öğün bildirimi, gün sonu özeti
- **🤖 AI Sohbet** — Doğal dilde soru sorma, motivasyon, tavsiye alma

## 🚀 Kurulum

### 1. Gereksinimler
- Python 3.10+
- Telegram Bot Token (@BotFather'dan)
- GitHub Personal Access Token (models:read scope)

### 2. Bağımlılıkları Kur
```bash
pip install -r requirements.txt
```

### 3. .env Dosyasını Oluştur
```bash
copy .env.example .env
```

`.env` dosyasını düzenle:
```
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
GITHUB_TOKEN=github_pat_...
TELEGRAM_USER_ID=123456789
```

**Telegram Bot Token:**
1. Telegram'da [@BotFather](https://t.me/BotFather) ile konuş
2. `/newbot` yaz ve adımları takip et
3. Token'ı kopyala

**GitHub Token:**
1. [github.com/settings/tokens](https://github.com/settings/tokens) adresine git
2. "Generate new token (classic)" → `models:read` scope'u seç
3. Token'ı kopyala

**Telegram User ID:**
1. Botu başlat, `/id` komutunu gönder
2. Gösterilen ID'yi `.env` dosyasına yaz

### 4. Botu Başlat
```bash
python main.py
```

## 📱 Komutlar

| Komut | Açıklama |
|-------|----------|
| `/basla` | Karşılama + hedef özeti |
| `/plan` | AI ile bugünün planı |
| `/hafta` | Haftalık özet tablosu |
| `/kilo <değer>` | Kilo kaydet (ör: `/kilo 81.5`) |
| `/calis <ders> <dk>` | Çalışma kaydet (ör: `/calis sat 45`) |
| `/ogun` | AI öğün önerisi |
| `/ozet` | Günlük ilerleme özeti |
| `/sor <soru>` | AI'a soru sor |
| `/pomodoro` | Pomodoro zamanlayıcı |
| `/gorevler` | Görev listesi |
| `/gorev_ekle <metin>` | Yeni görev ekle |
| `/tartil` | Hızlı kilo girişi (butonlarla) |
| `/tavsiye <ders>` | Çalışma tavsiyesi |
| `/id` | Telegram ID'ni öğren |

## 🔔 Otomatik Hatırlatmalar

| Saat | İçerik |
|------|--------|
| 08:00 | ☀️ Sabah planı + motivasyon |
| 10:00 | 📚 Ders çalışma hatırlatması |
| 12:30 | 🍽️ Öğle yemeği + protein |
| 14:00 | 📚 Ders çalışma hatırlatması |
| 19:00 | 🍽️ Akşam yemeği + protein |
| 22:00 | 🌙 Gün sonu özet |

## 🛠️ Teknolojiler

- **Python 3.10+**
- **python-telegram-bot** — Telegram Bot API
- **OpenAI SDK** → GitHub Models (GPT-4o-mini)
- **APScheduler** — Zamanlı görevler
- **SQLite** — Yerel veritabanı

## 📁 Proje Yapısı

```
qiosk2/
├── main.py                    # Ana giriş noktası
├── config.py                  # Yapılandırma ve sabitler
├── requirements.txt           # Python bağımlılıkları
├── .env.example              # Örnek ortam değişkenleri
├── .gitignore
├── README.md
└── bot/
    ├── __init__.py
    ├── database.py            # SQLite veritabanı katmanı
    ├── handlers/
    │   ├── __init__.py
    │   ├── komutlar.py        # Slash komutları
    │   └── butonlar.py        # Inline butonlar ve callback'ler
    └── services/
        ├── __init__.py
        ├── ai_service.py      # GitHub Models AI entegrasyonu
        └── hatirlatici.py     # APScheduler hatırlatmalar
```

## 📝 Lisans

MIT
