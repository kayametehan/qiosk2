"""
Qiosk2 — Kişisel AI Asistan Telegram Botu
Tek komutla kurulum + çalıştırma: python main.py
Bağımlılık kurulumu → .env yapılandırma → bot başlatma hepsi otomatik.
"""

import os
import sys
import subprocess
from pathlib import Path

PROJE_KOKU = Path(__file__).parent
ENV_PATH = PROJE_KOKU / ".env"
REQ_PATH = PROJE_KOKU / "requirements.txt"


# ═══════════════════════════════════════════════════════════
# ADIM 1: BAĞIMLILIK KURULUMU
# ═══════════════════════════════════════════════════════════

def _paket_kontrol():
    """Kritik paketler kurulu mu kontrol et, değilse hepsini kur."""
    try:
        import telegram        # noqa: F401
        import httpx           # noqa: F401
        import apscheduler     # noqa: F401
        import dotenv          # noqa: F401
        import duckduckgo_search  # noqa: F401
        import openpyxl        # noqa: F401
        return True
    except ImportError:
        return False


def _bagimliliklari_kur():
    """requirements.txt'den tüm bağımlılıkları kur."""
    print("\n📦 Bağımlılıklar kuruluyor... (ilk çalıştırma)")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", str(REQ_PATH)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        print("✅ Tüm paketler kuruldu.\n")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Paket kurulumu başarısız!\n   {e}")
        print(f"   Elle dene: pip install -r {REQ_PATH}")
        return False


def _ffmpeg_kontrol():
    """ffmpeg kurulu mu kontrol et (sesli mesajlar için)."""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️  ffmpeg kurulu değil — sesli mesajlar çalışmayacak.")
        if sys.platform == "darwin":
            print("   Kur: brew install ffmpeg")
        elif sys.platform == "win32":
            print("   İndir: https://ffmpeg.org/download.html")
        else:
            print("   Kur: sudo apt install ffmpeg")
        print()
        return False


# ═══════════════════════════════════════════════════════════
# ADIM 2: .ENV YAPILANDIRMA
# ═══════════════════════════════════════════════════════════

def _env_yapılandir():
    """İnteraktif .env yapılandırması — token'ları sor, dosyayı oluştur."""
    print("=" * 55)
    print("  🤖 Qiosk2 — İlk Kurulum")
    print("=" * 55)

    mevcut = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                mevcut[k.strip()] = v.strip()

    print("\n📋 Bot için 3 bilgi lazım:\n")

    # ─── 1. Telegram Bot Token ────────────────────────
    print("1️⃣  TELEGRAM BOT TOKEN")
    print("   @BotFather'a git → /newbot → token'ı kopyala")
    print("   https://t.me/BotFather")
    eski = mevcut.get("TELEGRAM_BOT_TOKEN", "")
    if eski:
        print(f"   Mevcut: {eski[:8]}...{eski[-4:]}")
    token = input("   Token: ").strip() or eski
    if not token:
        print("❌ Token boş olamaz!")
        sys.exit(1)

    print()

    # ─── 2. GitHub Token ──────────────────────────────
    print("2️⃣  GITHUB TOKEN (AI modeli için — ücretsiz)")
    print("   https://github.com/settings/tokens → Generate new token")
    print("   'Models' iznini seç")
    eski = mevcut.get("GITHUB_TOKEN", "")
    if eski:
        print(f"   Mevcut: {eski[:8]}...{eski[-4:]}")
    gh_token = input("   Token: ").strip() or eski
    if not gh_token:
        print("❌ GitHub Token boş olamaz!")
        sys.exit(1)

    print()

    # ─── 3. Telegram User ID ─────────────────────────
    print("3️⃣  TELEGRAM USER ID (güvenlik — sadece sen kullanabilirsin)")
    print("   Bilmiyorsan 0 yaz → botu başlat → /id komutu ile öğren")
    eski = mevcut.get("TELEGRAM_USER_ID", "0")
    uid = input(f"   User ID [{eski}]: ").strip() or eski

    # ─── Kaydet ───────────────────────────────────────
    ENV_PATH.write_text(
        f"# Qiosk2 Yapılandırma (python main.py ile oluşturuldu)\n"
        f"TELEGRAM_BOT_TOKEN={token}\n"
        f"GITHUB_TOKEN={gh_token}\n"
        f"TELEGRAM_USER_ID={uid}\n",
        encoding="utf-8",
    )

    print("\n" + "=" * 55)
    print("  ✅ Ayarlar kaydedildi!")
    print("=" * 55)

    if uid == "0":
        print("\n⚠️  User ID ayarlanmadı — botu başlat, /id yaz, sonra .env'yi güncelle.")

    print()


# ═══════════════════════════════════════════════════════════
# ADIM 3: BOTU BAŞLAT
# ═══════════════════════════════════════════════════════════

def _botu_baslat():
    """Tüm kontroller geçtikten sonra botu başlat."""
    import logging
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    from bot.database import tablolari_olustur, onboarding_tamamlandi, profil_ayarla
    from bot.handlers.sohbet import mesaj_handler, sesli_mesaj_handler, ONBOARDING_SORULARI
    from bot.services.hatirlatici import hatirlaticilari_kur
    from config import TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID

    logging.basicConfig(
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN boş! .env dosyasını kontrol et.")
        return

    # ── Komutlar ──

    async def start(update, context):
        if not onboarding_tamamlandi():
            profil_ayarla("onboarding_adim", "0")
            _, ilk_soru = ONBOARDING_SORULARI[0]
            await update.message.reply_text(ilk_soru)
        else:
            await update.message.reply_text(
                "👋 Tekrar merhaba! Nasıl yardımcı olabilirim?\n\n"
                "Sadece yaz, ben hallederim! 🚀"
            )

    async def id_goster(update, context):
        await update.message.reply_text(f"🆔 Senin Telegram ID'n: {update.effective_user.id}")

    # ── Başlat ──

    tablolari_olustur()
    logger.info("✅ Veritabanı hazır.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", id_goster))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, sesli_mesaj_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mesaj_handler))

    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")
    hatirlaticilari_kur(scheduler, app.bot)
    scheduler.start()
    logger.info("⏰ Zamanlayıcı başlatıldı.")

    logger.info("🤖 Bot başlatılıyor...")
    app.run_polling(drop_pending_updates=True)


# ═══════════════════════════════════════════════════════════
# ANA GİRİŞ — python main.py
# ═══════════════════════════════════════════════════════════

def main():
    """Tek komutla kurulum + başlatma."""
    print("\n🤖 Qiosk2 — Kişisel AI Asistan\n")

    # 1) Paketler kurulu mu?
    if not _paket_kontrol():
        if not _bagimliliklari_kur():
            return
        # Paketler yeni kuruldu, modül cache'i eski — Python'u yeniden başlat
        print("🔄 Yeniden başlatılıyor...\n")
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # 2) .env var mı?
    if not ENV_PATH.exists():
        _env_yapılandir()
    else:
        # .env var ama token boş olabilir
        from config import TELEGRAM_BOT_TOKEN, GITHUB_TOKEN
        if not TELEGRAM_BOT_TOKEN or not GITHUB_TOKEN:
            print("⚠️  .env dosyasında eksik token var, yeniden yapılandırılıyor...\n")
            _env_yapılandir()

    # 3) ffmpeg kontrolü (bilgi amaçlı)
    _ffmpeg_kontrol()

    # 4) Botu başlat
    _botu_baslat()


if __name__ == "__main__":
    main()
