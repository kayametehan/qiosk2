"""
Hatırlatıcı Servisi — Günlük otomatik hatırlatmalar.
APScheduler ile belirlenen saatlerde motivasyon ve durum mesajları.
"""

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bot.database import gunluk_calisma, gunun_gorevleri, son_kilo
from bot.services.ai_service import basit_cevap
from config import HATIRLATMALAR, HEDEFLER, TELEGRAM_USER_ID

logger = logging.getLogger(__name__)


def _ozet_context() -> str:
    """AI'ya verilecek günlük özet."""
    bugun = date.today()
    parcalar = [f"Tarih: {bugun.strftime('%d %B %Y')}"]

    sk = son_kilo()
    if sk:
        parcalar.append(f"Son kilo: {sk['kilo']} kg")

    gc = gunluk_calisma()
    if gc:
        parcalar.append("Bugünkü çalışma: " + ", ".join(f"{k}: {v}dk" for k, v in gc.items()))
    else:
        parcalar.append("Bugün henüz çalışma yok")

    gorevler = gunun_gorevleri()
    bekleyen = [g for g in gorevler if g["durum"] == "bekliyor"]
    if bekleyen:
        parcalar.append(f"Bekleyen görevler: {len(bekleyen)}")

    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days
    parcalar.append(f"CENT-S: {cents_kalan} gün, SAT: {sat_kalan} gün kaldı")

    return "\n".join(parcalar)


async def _sabah_plani(bot):
    """Sabah motivasyon + günlük plan önerisi."""
    context = _ozet_context()
    prompt = (
        f"Sabah hatırlatması yap. Günaydın de, bugünkü durumu özetle, "
        f"kısa bir plan öner. Motive edici ol.\n\nDurum:\n{context}"
    )
    mesaj = await basit_cevap(prompt)
    try:
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=mesaj)
    except Exception as e:
        logger.error(f"Sabah mesajı gönderilemedi: {e}")


async def _ders_hatirlatma(bot, seans: int):
    """Ders çalışma hatırlatması."""
    context = _ozet_context()
    prompt = (
        f"Ders çalışma hatırlatması yap (seans {seans}). "
        f"Bugünkü çalışma durumuna göre motive et, pomodoro öner.\n\nDurum:\n{context}"
    )
    mesaj = await basit_cevap(prompt)
    try:
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=mesaj)
    except Exception as e:
        logger.error(f"Ders hatırlatma gönderilemedi: {e}")


async def _ogun_hatirlatma(bot, ogun: str):
    """Öğün hatırlatması — sağlıklı beslenme önerisi."""
    prompt = (
        f"{ogun} vakti! Sağlıklı bir {ogun.lower()} önerisi yap. "
        f"Kullanıcı 75 kg hedefli, yumurta yemez, karamelli protein tozu var. "
        f"Kısa ve pratik öner."
    )
    mesaj = await basit_cevap(prompt)
    try:
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=mesaj)
    except Exception as e:
        logger.error(f"Öğün hatırlatma gönderilemedi: {e}")


async def _gun_sonu_ozet(bot):
    """Gün sonu performans özeti."""
    context = _ozet_context()
    prompt = (
        f"Gün sonu özeti yap. Bugün ne yapıldı, ne eksik kaldı, yarın için öneriler. "
        f"Kısa ve yapıcı ol.\n\nDurum:\n{context}"
    )
    mesaj = await basit_cevap(prompt)
    try:
        await bot.send_message(chat_id=TELEGRAM_USER_ID, text=mesaj)
    except Exception as e:
        logger.error(f"Gün sonu özeti gönderilemedi: {e}")


def hatirlaticilari_kur(scheduler: AsyncIOScheduler, bot):
    """Tüm zamanlanmış hatırlatıcıları kur."""

    h = HATIRLATMALAR

    # Sabah planı
    saat, dk = h["sabah_plani"]
    scheduler.add_job(
        _sabah_plani, CronTrigger(hour=saat, minute=dk),
        args=[bot], id="sabah_plani", replace_existing=True,
    )

    # Ders hatırlatma 1
    saat, dk = h["ders_hatirlatma_1"]
    scheduler.add_job(
        _ders_hatirlatma, CronTrigger(hour=saat, minute=dk),
        args=[bot, 1], id="ders_hatirlatma_1", replace_existing=True,
    )

    # Ders hatırlatma 2
    saat, dk = h["ders_hatirlatma_2"]
    scheduler.add_job(
        _ders_hatirlatma, CronTrigger(hour=saat, minute=dk),
        args=[bot, 2], id="ders_hatirlatma_2", replace_existing=True,
    )

    # Öğle öğünü
    saat, dk = h["ogun_ogle"]
    scheduler.add_job(
        _ogun_hatirlatma, CronTrigger(hour=saat, minute=dk),
        args=[bot, "Öğle"], id="ogun_ogle", replace_existing=True,
    )

    # Akşam öğünü
    saat, dk = h["ogun_aksam"]
    scheduler.add_job(
        _ogun_hatirlatma, CronTrigger(hour=saat, minute=dk),
        args=[bot, "Akşam"], id="ogun_aksam", replace_existing=True,
    )

    # Gün sonu özet
    saat, dk = h["gun_sonu_ozet"]
    scheduler.add_job(
        _gun_sonu_ozet, CronTrigger(hour=saat, minute=dk),
        args=[bot], id="gun_sonu_ozet", replace_existing=True,
    )

    logger.info("⏰ Tüm hatırlatıcılar kuruldu.")
