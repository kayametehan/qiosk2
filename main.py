"""
🤖 Kişisel Asistan Telegram Botu
Haftalık planlama, hedef takibi, AI destekli kişisel asistan

Çalıştırmak için:
  1. .env dosyasını oluştur (.env.example'dan kopyala)
  2. pip install -r requirements.txt
  3. python main.py
"""

import logging

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from config import TELEGRAM_BOT_TOKEN
from bot import database as db
from bot.handlers.komutlar import (
    basla,
    calis,
    hafta,
    kilo,
    kullanici_id,
    ogun,
    ozet,
    plan,
    sor,
    tavsiye,
)
from bot.handlers.butonlar import (
    buton_callback,
    gorev_ekle_komut,
    gorevleri_goster,
    hizli_kilo,
    pomodoro_baslat,
)
from bot.services.hatirlatici import hatirlatici_kur

# Logging ayarı
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Botu başlat."""
    # Token kontrolü
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "buraya_telegram_token":
        print("❌ TELEGRAM_BOT_TOKEN ayarlanmamış!")
        print("📋 .env.example dosyasını .env olarak kopyala ve token'ları gir.")
        return

    # Veritabanı tablolarını oluştur
    db.tablolari_olustur()
    logger.info("✅ Veritabanı hazır")

    # Bot uygulamasını oluştur
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # ─── Komut Handler'ları ───────────────────────────
    app.add_handler(CommandHandler("basla", basla))
    app.add_handler(CommandHandler("start", basla))  # Telegram standart
    app.add_handler(CommandHandler("id", kullanici_id))
    app.add_handler(CommandHandler("plan", plan))
    app.add_handler(CommandHandler("hafta", hafta))
    app.add_handler(CommandHandler("kilo", kilo))
    app.add_handler(CommandHandler("calis", calis))
    app.add_handler(CommandHandler("ogun", ogun))
    app.add_handler(CommandHandler("ozet", ozet))
    app.add_handler(CommandHandler("sor", sor))
    app.add_handler(CommandHandler("tavsiye", tavsiye))

    # ─── Buton Handler'ları ───────────────────────────
    app.add_handler(CommandHandler("pomodoro", pomodoro_baslat))
    app.add_handler(CommandHandler("gorevler", gorevleri_goster))
    app.add_handler(CommandHandler("gorev_ekle", gorev_ekle_komut))
    app.add_handler(CommandHandler("tartil", hizli_kilo))

    # ─── Callback Query (inline butonlar) ─────────────
    app.add_handler(CallbackQueryHandler(buton_callback))

    # ─── Hatırlatıcıları kur ──────────────────────────
    scheduler = hatirlatici_kur(app)
    scheduler.start()
    logger.info("✅ Zamanlı hatırlatıcılar aktif")

    # ─── Botu başlat (polling modu - Windows uyumlu) ──
    logger.info("🤖 Bot başlatılıyor...")
    print("""
╔══════════════════════════════════════════════════╗
║  🤖 Kişisel Asistan Bot Aktif!                  ║
║                                                  ║
║  Komutlar:                                       ║
║  /basla    - Karşılama + hedef özeti             ║
║  /plan     - Bugünün AI planı                    ║
║  /hafta    - Haftalık özet                       ║
║  /kilo     - Kilo kaydet                         ║
║  /calis    - Çalışma kaydet                      ║
║  /ogun     - Öğün önerisi                        ║
║  /ozet     - Günlük ilerleme                     ║
║  /sor      - AI'a soru sor                       ║
║  /pomodoro - Zamanlayıcı başlat                  ║
║  /gorevler - Görev listesi                       ║
║  /tartil   - Hızlı kilo girişi                   ║
║  /tavsiye  - Çalışma tavsiyesi                   ║
║                                                  ║
║  Durdurmak için: Ctrl+C                          ║
╚══════════════════════════════════════════════════╝
    """)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
