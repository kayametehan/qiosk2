"""
🤖 Kişisel Asistan Telegram Botu — Tam Yerel AI Ajan
Komut yok, sadece doğal konuşma. Bot her şeyi anlar ve yapar.
"""

import logging

from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import TELEGRAM_BOT_TOKEN
from bot import database as db
from bot.handlers.sohbet import (
    callback_handler,
    id_handler,
    mesaj_handler,
    start_handler,
)
from bot.services.hatirlatici import hatirlatici_kur

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "buraya_telegram_token":
        print("❌ TELEGRAM_BOT_TOKEN ayarlanmamış!")
        print("📋 .env.example → .env kopyala, token'ları gir.")
        return

    # Veritabanı
    db.tablolari_olustur()
    logger.info("✅ Veritabanı hazır")

    # Bot
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Sadece /start ve /id komutları — geri kalan her şey sohbetle
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("id", id_handler))

    # Inline buton callback'leri (pomodoro, görev)
    app.add_handler(CallbackQueryHandler(callback_handler))

    # 🧠 Ana handler — HER mesaj buraya gelir, AI karar verir
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))

    # Hatırlatıcılar
    scheduler = hatirlatici_kur(app)
    scheduler.start()

    print("""
╔══════════════════════════════════════════════════════════╗
║  🤖 Kişisel Asistan Bot — AI Ajan Modu                  ║
║                                                          ║
║  Komut yok, sadece doğal konuş:                          ║
║                                                          ║
║  "82 kiloyum"           → kaydeder                       ║
║  "1 saat SAT çalıştım"  → kaydeder                      ║
║  "bugün ne yapayım"     → AI plan yapar                  ║
║  "ne yesem"             → diyet önerisi                  ║
║  "nasıl gidiyorum"      → özet çıkarır                   ║
║  "İstanbul otel bul"    → internette araştırır           ║
║  "desktop'taki dosyalar" → bilgisayarı kontrol eder      ║
║                                                          ║
║  Ctrl+C ile durdur                                       ║
╚══════════════════════════════════════════════════════════╝
    """)

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
