# 🤖 Qiosk2 — Kişisel AI Asistan Telegram Botu

Tamamen Türkçe, sohbet odaklı kişisel asistan. OpenAI SDK yok — tüm bağımlılıklar açık kaynak.

## ✨ Özellikler

### 🧠 AI Ajan (Çoklu Adım)
- Doğal Türkçe sohbet ile her şeyi yapabilir
- Karmaşık görevleri otomatik planlar ve adım adım çözer
- Örnek: "Antalya'da otel ara" → arar → sayfaları okur → karşılaştırır → en iyileri sunar

### 🌐 Web Yetenekleri
- DuckDuckGo ile web araması
- Haber araması
- Web sayfalarını okuma (yorumlar, fiyatlar, detaylar)
- Dosya indirme

### 💻 Sistem Erişimi
- Dosya okuma / yazma / arama
- Klasör listeleme
- Terminal komutları çalıştırma
- Uygulama & URL açma
- İşlem listesi & kapatma
- Sistem bilgisi (CPU, RAM, Disk)
- Ekran görüntüsü alma
- Pano (clipboard) okuma/yazma

### 📊 Kişisel Takip
- ⚖️ Kilo takibi (75 kg hedef)
- 📚 Ders çalışma süresi (SAT & CENT-S)
- ✅ Görev yönetimi
- 🍽️ Öğün takibi
- 🍅 Pomodoro zamanlayıcı

### ⏰ Otomatik Hatırlatmalar
- Sabah planı (08:00)
- Ders hatırlatmaları (10:00, 14:00)
- Öğün hatırlatmaları (12:30, 19:00)
- Gün sonu özet (22:00)

## 🛠️ Kurulum

### 1. Gereksinimler
- Python 3.10+
- Telegram Bot Token (@BotFather'dan al)
- GitHub Personal Access Token (models:read scope)

### 2. Kur

```bash
git clone https://github.com/kayametehan/qiosk2.git
cd qiosk2
pip install -r requirements.txt
```

### 3. Ayarla

```bash
copy .env.example .env
```

`.env` dosyasını düzenle:
```
TELEGRAM_BOT_TOKEN=bot_tokenin
GITHUB_TOKEN=github_pat_tokenin
TELEGRAM_USER_ID=senin_telegram_idn
```

Telegram ID'ni öğrenmek için botu başlat ve `/id` yaz.

### 4. Çalıştır

**Windows:**
```
start_bot.bat
```

**Manuel:**
```bash
python main.py
```

## 📁 Proje Yapısı

```
qiosk2/
├── main.py                      # Ana giriş
├── config.py                    # Ayarlar & system prompt
├── requirements.txt             # Bağımlılıklar (hepsi açık kaynak)
├── start_bot.bat                # Windows başlatıcı
├── .env.example                 # Ortam değişkenleri şablonu
└── bot/
    ├── database.py              # SQLite veri katmanı
    ├── handlers/
    │   └── sohbet.py            # Mesaj handler & tool executor
    └── services/
        ├── ai_service.py        # GitHub Models API (raw httpx)
        ├── web_service.py       # Web arama, sayfa okuma, indirme
        ├── system_service.py    # Dosya, sistem, işlem yönetimi
        └── hatirlatici.py       # Zamanlanmış hatırlatmalar
```

## 🔧 Teknik Detaylar

- **AI**: GitHub Models API (`openai/gpt-4o-mini`) — doğrudan httpx ile, OpenAI SDK yok
- **Telegram**: python-telegram-bot 21.3 (polling mode)
- **Veritabanı**: SQLite (yerel, sunucu gerektirmez)
- **Zamanlama**: APScheduler (AsyncIOScheduler)
- **Web**: DuckDuckGo Search + BeautifulSoup4
- **Sistem**: psutil + Pillow + pyperclip

## 📝 Lisans

Kişisel kullanım.
