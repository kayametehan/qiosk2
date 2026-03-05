"""
Hatırlatıcı Servisi - Zamanlı bildirimler
"""

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from config import HATIRLATMALAR, HEDEFLER, TELEGRAM_USER_ID
from bot import database as db
from bot.services.ai_service import basit_ai_cevap

logger = logging.getLogger(__name__)


async def _gonder(app: Application, mesaj: str):
    """Kullanıcıya mesaj gönder."""
    if TELEGRAM_USER_ID == 0:
        return
    try:
        await app.bot.send_message(chat_id=TELEGRAM_USER_ID, text=mesaj, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Hatırlatma gönderilemedi: {e}")


async def sabah_plani(app: Application):
    """08:00 — Sabah motivasyon + plan."""
    bugun = date.today()
    son_kilo = db.son_kilo()
    kilo_str = f"Son kilo: {son_kilo['kilo']} kg" if son_kilo else ""

    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    prompt = f"""Günaydın mesajı + bugünün kısa planını yap.
{kilo_str}
CENT-S'e {cents_kalan} gün, SAT'a {sat_kalan} gün kaldı.
Bugün hangi derse öncelik vermeli, kaç saat çalışmalı, öğün önerileri ver.
Kısa ve motive edici tut."""

    cevap = basit_ai_cevap(prompt)
    await _gonder(app, f"☀️ {cevap}")


async def ders_hatirlatma(app: Application):
    """10:00, 14:00 — Ders hatırlatması."""
    bugun = date.today()
    gunluk = db.gunluk_calisma()
    toplam = sum(gunluk.values()) if gunluk else 0

    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    if cents_kalan < 0 and sat_kalan < 0:
        return  # Sınavlar bitti

    mesaj = "📚 *Ders Zamanı!*\n\n"

    if cents_kalan > 0:
        mesaj += f"⚡ CENT-S'e *{cents_kalan} gün* — "
    if sat_kalan > 0:
        mesaj += f"📖 SAT'a *{sat_kalan} gün*\n"

    if toplam > 0:
        mesaj += f"\n📊 Bugün {toplam}dk çalıştın. "
        mesaj += "Devam et! 💪" if toplam >= 60 else "Biraz daha!"
    else:
        mesaj += "\n⏰ Bugün henüz başlamadın, haydi!"

    await _gonder(app, mesaj)


async def ogun_hatirlatma(app: Application, ogun: str = "öğle"):
    """12:30, 19:00 — Öğün hatırlatması."""
    mesaj = (
        f"🍽️ *{ogun.title()} Zamanı!*\n\n"
        f"💡 Protein ağırlıklı beslen\n"
        f"🥤 Protein shake'ini unutma\n"
        f"💧 Su iç!\n\n"
        f"_Ne yesem diye sor, öneri yapayım_ 😊"
    )
    await _gonder(app, mesaj)


async def gun_sonu(app: Application):
    """22:00 — Gün sonu değerlendirmesi."""
    gunluk = db.gunluk_calisma()
    son_kilo = db.son_kilo()

    calisma_str = ", ".join(f"{d.upper()}: {dk}dk" for d, dk in gunluk.items()) if gunluk else "Çalışma yok"
    kilo_str = f"{son_kilo['kilo']} kg" if son_kilo else "Kayıt yok"

    prompt = f"""Gün sonu kısa değerlendirme yap:
Çalışma: {calisma_str}
Kilo: {kilo_str}
Neleri iyi yaptım, yarın ne yapmalıyım? 2-3 cümle yeter."""

    cevap = basit_ai_cevap(prompt)
    mesaj = f"🌙 *Gün Sonu*\n\n{cevap}"

    # Kilo girişi kontrolü
    bugun = date.today().isoformat()
    gecmis = db.kilo_gecmisi(1)
    if not gecmis or gecmis[0]["tarih"] != bugun:
        mesaj += "\n\n⚖️ _Bugün kilo girmedin! Kaç kilosun yaz_"

    await _gonder(app, mesaj)


def hatirlatici_kur(app: Application) -> AsyncIOScheduler:
    """Tüm hatırlatıcıları kur."""
    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

    s, d = HATIRLATMALAR["sabah_plani"]
    scheduler.add_job(sabah_plani, "cron", hour=s, minute=d, args=[app], id="sabah")

    for key in ["ders_hatirlatma_1", "ders_hatirlatma_2"]:
        s, d = HATIRLATMALAR[key]
        scheduler.add_job(ders_hatirlatma, "cron", hour=s, minute=d, args=[app], id=key)

    s, d = HATIRLATMALAR["ogun_ogle"]
    scheduler.add_job(ogun_hatirlatma, "cron", hour=s, minute=d, args=[app, "öğle"], id="ogle")

    s, d = HATIRLATMALAR["ogun_aksam"]
    scheduler.add_job(ogun_hatirlatma, "cron", hour=s, minute=d, args=[app, "akşam"], id="aksam")

    s, d = HATIRLATMALAR["gun_sonu_ozet"]
    scheduler.add_job(gun_sonu, "cron", hour=s, minute=d, args=[app], id="gece")

    logger.info("✅ Hatırlatıcılar kuruldu")
    return scheduler
