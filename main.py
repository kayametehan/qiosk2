"""
Qiosk2 — Kişisel AI Asistan Telegram Botu
Ana giriş noktası. Sadece /start ve /id komutu var, geri kalan her şey doğal sohbet.
"""

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bot.database import tablolari_olustur, onboarding_tamamlandi, profil_ayarla
from bot.handlers.sohbet import mesaj_handler, ONBOARDING_SORULARI
from bot.services.hatirlatici import hatirlaticilari_kur
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID

# ─── Logging ───────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ─── Komutlar ──────────────────────────────────────────────

async def start(update, context):
    """Bot başlangıç mesajı — onboarding başlat veya hoşgeldin de."""
    if not onboarding_tamamlandi():
        # Onboarding'i sıfırla ve ilk soruyu sor
        profil_ayarla("onboarding_adim", "0")
        _, ilk_soru = ONBOARDING_SORULARI[0]
        await update.message.reply_text(ilk_soru)
    else:
        await update.message.reply_text(
            "👋 Tekrar merhaba! Nasıl yardımcı olabilirim?\n\n"
            "Sadece yaz, ben hallederim! 🚀"
        )


async def id_goster(update, context):
    """Kullanıcı ID'sini göster."""
    await update.message.reply_text(f"🆔 Senin Telegram ID'n: {update.effective_user.id}")


# ─── Uygulama ─────────────────────────────────────────────

def main():
    """Bot'u başlat."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN ayarlanmamış! .env dosyasını kontrol et.")
        return

    # Veritabanı tablolarını oluştur
    tablolari_olustur()
    logger.info("✅ Veritabanı hazır.")

    # Bot uygulamasını oluştur
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # Komutlar (sadece 2 tane)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", id_goster))

    # Diğer tüm mesajlar → AI ajan
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))

    # Hatırlatıcılar
    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")
    hatirlaticilari_kur(scheduler, app.bot)
    scheduler.start()
    logger.info("⏰ Zamanlayıcı başlatıldı.")

    # Bot çalıştır
    logger.info("🤖 Bot başlatılıyor...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
