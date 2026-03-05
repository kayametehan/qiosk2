"""
Hatırlatıcı Servisi - APScheduler ile zamanlı bildirimler
"""

import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram.ext import Application

from config import HATIRLATMALAR, HEDEFLER, TELEGRAM_USER_ID
from bot import database as db
from bot.services.ai_service import (
    gun_sonu_degerlendirme,
    gunluk_plan_olustur,
    motivasyon_mesaji,
)

logger = logging.getLogger(__name__)


async def _mesaj_gonder(app: Application, mesaj: str):
    """Kullanıcıya mesaj gönder."""
    if TELEGRAM_USER_ID == 0:
        logger.warning("TELEGRAM_USER_ID ayarlanmamış! Hatırlatma gönderilemedi.")
        return
    try:
        await app.bot.send_message(
            chat_id=TELEGRAM_USER_ID,
            text=mesaj,
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Mesaj gönderilemedi: {e}")


# ─── Sabah Planı (08:00) ─────────────────────────────────

async def sabah_plani(app: Application):
    """Sabah motivasyon + günlük plan gönder."""
    bugun = date.today()

    # Motivasyon mesajı
    motiv = motivasyon_mesaji()
    await _mesaj_gonder(app, f"☀️ *Günaydın!*\n\n{motiv}")

    # Kilo bilgisi
    son_kilo = db.son_kilo()
    kilo_str = f"Son kilo: {son_kilo['kilo']} kg" if son_kilo else "Kilo kaydı yok"

    # Plan oluştur
    plan = gunluk_plan_olustur(kilo_str, "Yeni güne başlıyoruz!")
    await _mesaj_gonder(app, f"📅 *Bugünün Planı*\n\n{plan}")


# ─── Ders Hatırlatması (10:00, 14:00) ────────────────────

async def ders_hatirlatma(app: Application):
    """Ders çalışma hatırlatması."""
    bugun = date.today()

    # Günlük çalışma durumu
    gunluk = db.gunluk_calisma()
    toplam = sum(gunluk.values()) if gunluk else 0

    # Hangi sınav daha yakın?
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    mesaj = "📚 *Ders Çalışma Zamanı!*\n\n"

    if cents_kalan > 0 and sat_kalan > 0:
        if cents_kalan <= sat_kalan:
            mesaj += f"⚡ CENT-S sınavına *{cents_kalan} gün* kaldı — Öncelik bu!\n"
            mesaj += f"📖 SAT sınavına *{sat_kalan} gün* kaldı\n"
        else:
            mesaj += f"⚡ SAT sınavına *{sat_kalan} gün* kaldı — Öncelik bu!\n"
            mesaj += f"📖 CENT-S sınavına *{cents_kalan} gün* kaldı\n"
    elif cents_kalan > 0:
        mesaj += f"📖 CENT-S sınavına *{cents_kalan} gün* kaldı\n"
    elif sat_kalan > 0:
        mesaj += f"📖 SAT sınavına *{sat_kalan} gün* kaldı\n"
    else:
        mesaj = "🎉 Tüm sınavlar tamamlandı! Artık kilo hedefine odaklan 💪"
        await _mesaj_gonder(app, mesaj)
        return

    if toplam > 0:
        mesaj += f"\n📊 Bugün şu ana kadar *{toplam} dakika* çalıştın."
        if toplam < 120:
            mesaj += "\n⚠️ Hedefe ulaşmak için biraz daha çalışmalısın!"
        else:
            mesaj += "\n✅ Güzel gidiyorsun, devam et!"
    else:
        mesaj += "\n⏰ Bugün henüz çalışmaya başlamadın! Haydi başla!"

    mesaj += "\n\n`/calis sat 30` veya `/calis cents 30` ile kaydet"

    await _mesaj_gonder(app, mesaj)


# ─── Öğün Hatırlatması (12:30, 19:00) ────────────────────

async def ogun_hatirlatma(app: Application, ogun_tipi: str = "öğle"):
    """Öğün ve protein hatırlatması."""
    mesaj = f"🍽️ *{ogun_tipi.title()} Yemeği Zamanı!*\n\n"
    mesaj += "💡 Unutma:\n"
    mesaj += "  • Yüksek proteinli beslen 🥩\n"
    mesaj += "  • Protein shake içmeyi unutma 🥤\n"
    mesaj += "  • Bol su iç 💧\n"
    mesaj += "\n🤖 Menü önerisi için: /ogun"

    await _mesaj_gonder(app, mesaj)


# ─── Gün Sonu Özet (22:00) ───────────────────────────────

async def gun_sonu_ozeti(app: Application):
    """Gün sonu özet ve değerlendirme."""
    # Bugünkü verileri topla
    gunluk = db.gunluk_calisma()
    son_kilo = db.son_kilo()
    gorevler = db.gunun_gorevleri()

    # Çalışma özeti
    if gunluk:
        calisma_str = ", ".join(f"{d.upper()}: {dk}dk" for d, dk in gunluk.items())
        toplam = sum(gunluk.values())
        calisma_str += f" (Toplam: {toplam}dk)"
    else:
        calisma_str = "Bugün çalışma kaydı yok 😴"

    # Kilo bilgisi
    if son_kilo:
        kilo_str = f"{son_kilo['kilo']} kg (Hedef: {HEDEFLER['kilo']['hedef_kg']} kg)"
    else:
        kilo_str = "Kilo kaydı yok"

    # Görev bilgisi
    if gorevler:
        tamamlanan = sum(1 for g in gorevler if g["durum"] == "tamamlandi")
        gorev_str = f"{tamamlanan}/{len(gorevler)} görev tamamlandı"
    else:
        gorev_str = "Görev eklenmemiş"

    # AI değerlendirmesi
    degerlendirme = gun_sonu_degerlendirme(calisma_str, kilo_str, gorev_str)

    mesaj = f"🌙 *Gün Sonu Özeti*\n\n{degerlendirme}"

    # Kilo girişi kontrolü
    bugun = date.today().isoformat()
    kilo_kayitlari = db.kilo_gecmisi(1)
    if not kilo_kayitlari or kilo_kayitlari[0]["tarih"] != bugun:
        mesaj += "\n\n⚖️ *Bugün kilo girmedin!* /kilo ile kaydet"

    await _mesaj_gonder(app, mesaj)


# ─── Scheduler Kurulumu ──────────────────────────────────

def hatirlatici_kur(app: Application) -> AsyncIOScheduler:
    """Tüm hatırlatıcıları kur ve scheduler'ı döndür."""
    scheduler = AsyncIOScheduler(timezone="Europe/Istanbul")

    # Sabah planı
    saat, dakika = HATIRLATMALAR["sabah_plani"]
    scheduler.add_job(
        sabah_plani,
        "cron",
        hour=saat,
        minute=dakika,
        args=[app],
        id="sabah_plani",
    )

    # Ders hatırlatmaları
    for key in ["ders_hatirlatma_1", "ders_hatirlatma_2"]:
        saat, dakika = HATIRLATMALAR[key]
        scheduler.add_job(
            ders_hatirlatma,
            "cron",
            hour=saat,
            minute=dakika,
            args=[app],
            id=key,
        )

    # Öğle yemeği
    saat, dakika = HATIRLATMALAR["ogun_ogle"]
    scheduler.add_job(
        ogun_hatirlatma,
        "cron",
        hour=saat,
        minute=dakika,
        args=[app, "öğle"],
        id="ogun_ogle",
    )

    # Akşam yemeği
    saat, dakika = HATIRLATMALAR["ogun_aksam"]
    scheduler.add_job(
        ogun_hatirlatma,
        "cron",
        hour=saat,
        minute=dakika,
        args=[app, "akşam"],
        id="ogun_aksam",
    )

    # Gün sonu özet
    saat, dakika = HATIRLATMALAR["gun_sonu_ozet"]
    scheduler.add_job(
        gun_sonu_ozeti,
        "cron",
        hour=saat,
        minute=dakika,
        args=[app],
        id="gun_sonu_ozet",
    )

    logger.info("✅ Hatırlatıcılar kuruldu!")
    return scheduler
