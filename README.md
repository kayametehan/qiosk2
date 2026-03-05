# 🤖 Kişisel Asistan Telegram Botu — AI Ajan

Komut yok, sadece doğal konuş. Bot her şeyi anlar ve yapar.
İnternette arar, dosyalarını yönetir, bilgisayarını kontrol eder.

## 🧠 Nasıl Çalışır?

Normal mesaj atarsın, AI anlayıp gerekli aksiyonları **kendisi** alır:

| Sen yazarsın | Bot yapar |
|---|---|
| "82 kiloyum" | ⚖️ Kilo kaydeder, hedefe kalan farkı söyler |
| "1 saat SAT çalıştım" | 📚 Çalışmayı kaydeder, istatistik gösterir |
| "bugün ne yapayım" | 📅 AI ile günlük plan oluşturur |
| "ne yesem" | 🍽️ Yumurtasız, proteinli öğün önerir |
| "nasıl gidiyorum" | 📈 Kilo, çalışma, sınav özeti çıkarır |
| "İstanbul'da güzel otel bul" | 🔍 İnternette arar, sayfaları okur, karşılaştırır |
| "masaüstündeki dosyaları göster" | 📁 Bilgisayardaki dosyaları listeler |
| "hava durumuna bak" | 🌤️ İnternetten hava durumu çeker |
| "spotify aç" | 🚀 Uygulamayı açar |

## 🔧 Yetenekleri

- **🔍 Web Arama** — DuckDuckGo ile her şeyi arar
- **📄 Sayfa Okuma** — Web sayfalarını okur (fiyatlar, yorumlar, bilgi)
- **📁 Dosya Yönetimi** — Dosya okur, yazar, klasör listeler
- **💻 Terminal** — Sistem komutları çalıştırır
- **🚀 Uygulama** — URL/uygulama açar
- **⚖️ Kilo Takibi** — Kayıt, trend, hedef analizi
- **📚 Çalışma Takibi** — SAT & CENT-S seans kaydı
- **📋 Görev Yönetimi** — Yapılacaklar listesi
- **⏱️ Pomodoro** — 25dk/5dk zamanlayıcı
- **🔔 Hatırlatmalar** — Sabah plan, ders, öğün, gün sonu
- **🤖 Çok Adımlı Ajan** — Karmaşık görevleri adım adım çözer

## 🚀 Kurulum

### 1. Bağımlılıkları Kur
```bash
pip install -r requirements.txt
```

### 2. .env Dosyasını Ayarla
```bash
copy .env.example .env
```

Düzenle:
```
TELEGRAM_BOT_TOKEN=...    # @BotFather'dan al
GITHUB_TOKEN=...          # github.com/settings/tokens → models:read
TELEGRAM_USER_ID=...      # Botu başlat, /id yaz, öğren
```

### 3. Çalıştır
```bash
python main.py
```
Windows'ta: `start_bot.bat` çift tıkla

## 📁 Yapı

```
qiosk2/
├── main.py                     # Giriş noktası
├── config.py                   # Ayarlar ve hedefler
├── requirements.txt
├── start_bot.bat               # Windows başlatıcı
└── bot/
    ├── database.py             # SQLite veritabanı
    ├── handlers/
    │   └── sohbet.py           # Ana mesaj işleyici + agent tool executor
    └── services/
        ├── ai_service.py       # AI agent loop + function calling
        ├── web_service.py      # Web arama + sayfa okuma
        ├── system_service.py   # Dosya + sistem işlemleri
        └── hatirlatici.py      # Zamanlı bildirimler
```
