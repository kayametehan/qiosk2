"""
Sohbet Handler — Ana mesaj işleyici.
Doğal dildeki mesajları AI ajana yönlendirir, tool çağrılarını yürütür.
"""

import asyncio
import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    calisma_kaydet,
    genel_istatistik,
    gorev_ekle,
    gunluk_calisma,
    gunluk_ogunler,
    gunun_gorevleri,
    haftalik_calisma,
    haftalik_gunluk_detay,
    kilo_gecmisi,
    kilo_kaydet,
    son_kilo,
)
from bot.services.ai_service import agent_loop
from bot.services.system_service import (
    dosya_ara,
    dosya_listele,
    dosya_oku,
    dosya_yaz,
    ekran_goruntusu,
    islem_kapat,
    islem_listele,
    komut_calistir,
    panoya_kopyala,
    panodan_oku,
    sistem_bilgisi,
    uygulama_ac,
)
from bot.services.web_service import dosya_indir, haber_ara, sayfa_oku, web_ara
from config import HEDEFLER, POMODORO_CALISMA_DK, POMODORO_MOLA_DK, TELEGRAM_USER_ID

logger = logging.getLogger(__name__)

# Aktif pomodoro'lar
aktif_pomodorolar = {}


# ─── Context oluştur (özet bilgi) ─────────────────────────

def _kullanici_contexti() -> str:
    """Mevcut istatistikleri AI'ya context olarak ver."""
    bugun = date.today()
    parcalar = []

    # Kilo
    sk = son_kilo()
    if sk:
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        fark = sk["kilo"] - hedef
        parcalar.append(f"Son kilo: {sk['kilo']} kg (hedef {hedef}, {'+' if fark > 0 else ''}{fark:.1f} kg)")

    # Bugünkü çalışma
    gc = gunluk_calisma()
    if gc:
        satir = ", ".join(f"{k}: {v} dk" for k, v in gc.items())
        parcalar.append(f"Bugünkü çalışma: {satir}")

    # Görevler
    gorevler = gunun_gorevleri()
    if gorevler:
        bekleyen = [g for g in gorevler if g["durum"] == "bekliyor"]
        tamamlanan = [g for g in gorevler if g["durum"] == "tamamlandi"]
        parcalar.append(f"Görevler: {len(tamamlanan)} tamamlandı, {len(bekleyen)} bekliyor")

    # Öğünler
    ogunler = gunluk_ogunler()
    if ogunler:
        parcalar.append(f"Bugün {len(ogunler)} öğün kaydı var")

    # Geri sayım
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days
    if cents_kalan > 0:
        parcalar.append(f"CENT-S sınavına {cents_kalan} gün")
    if sat_kalan > 0:
        parcalar.append(f"SAT sınavına {sat_kalan} gün")

    return "\n".join(parcalar) if parcalar else ""


# ─── Tool Executor ─────────────────────────────────────────

def tool_calistir(func_name: str, func_args: dict) -> str:
    """Tool adını ve argümanlarını alıp ilgili fonksiyonu çağırır."""

    # === Web ===
    if func_name == "web_ara":
        return web_ara(func_args["sorgu"], func_args.get("max_sonuc", 8))

    elif func_name == "sayfa_oku":
        return sayfa_oku(func_args["url"])

    elif func_name == "haber_ara":
        return haber_ara(func_args["sorgu"])

    elif func_name == "dosya_indir":
        return dosya_indir(func_args["url"], func_args.get("kayit_yolu"))

    # === Dosya Sistemi ===
    elif func_name == "dosya_oku":
        return dosya_oku(func_args["yol"])

    elif func_name == "dosya_yaz":
        return dosya_yaz(func_args["yol"], func_args["icerik"])

    elif func_name == "dosya_listele":
        return dosya_listele(func_args.get("yol", "."), func_args.get("detayli", False))

    elif func_name == "dosya_ara":
        return dosya_ara(
            func_args["baslangic_yolu"],
            func_args["desen"],
            func_args.get("icerik_ara"),
        )

    # === Sistem ===
    elif func_name == "komut_calistir":
        return komut_calistir(func_args["komut"], func_args.get("cwd"))

    elif func_name == "uygulama_ac":
        return uygulama_ac(func_args["hedef"])

    elif func_name == "sistem_bilgisi":
        return sistem_bilgisi()

    elif func_name == "islem_listele":
        return islem_listele(func_args.get("filtre"))

    elif func_name == "islem_kapat":
        return islem_kapat(func_args["islem_adi"])

    elif func_name == "ekran_goruntusu":
        return ekran_goruntusu(func_args.get("kayit_yolu"))

    elif func_name == "panoya_kopyala":
        return panoya_kopyala(func_args["metin"])

    elif func_name == "panodan_oku":
        return panodan_oku()

    # === Kişisel Takip ===
    elif func_name == "kilo_kaydet":
        result = kilo_kaydet(func_args["kilo"])
        return (
            f"✅ {result['tarih']}: {result['kilo']} kg kaydedildi"
            + (" (güncellendi)" if result.get("guncellendi") else "")
        )

    elif func_name == "calisma_kaydet":
        result = calisma_kaydet(func_args["ders"], func_args["dakika"])
        return f"✅ {result['ders']} çalışması kaydedildi: {result['dakika']} dakika"

    elif func_name == "gorev_ekle":
        gorev_id = gorev_ekle(func_args["gorev"])
        return f"✅ Görev eklendi (ID: {gorev_id}): {func_args['gorev']}"

    elif func_name == "gorevleri_listele":
        gorevler = gunun_gorevleri()
        if not gorevler:
            return "📋 Bugün için görev yok."
        cikti = "📋 Bugünkü görevler:\n\n"
        for g in gorevler:
            durum = "✅" if g["durum"] == "tamamlandi" else "⏳" if g["durum"] == "bekliyor" else "↩️"
            cikti += f"  {durum} [{g['id']}] {g['gorev']}\n"
        return cikti

    elif func_name == "kilo_gecmisi":
        gecmis = kilo_gecmisi(func_args.get("gun", 7))
        if not gecmis:
            return "📊 Henüz kilo kaydı yok."
        cikti = "📊 Kilo geçmişi:\n\n"
        for k in gecmis:
            cikti += f"  {k['tarih']}: {k['kilo']} kg\n"
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        son = gecmis[0]["kilo"]
        fark = son - hedef
        cikti += f"\n🎯 Hedef: {hedef} kg | Fark: {'+' if fark > 0 else ''}{fark:.1f} kg"
        return cikti

    elif func_name == "ozet_goster":
        return _gunluk_ozet_olustur()

    elif func_name == "haftalik_ozet":
        return _haftalik_ozet_olustur()

    elif func_name == "pomodoro_baslat":
        return f"⏱️ POMODORO:{func_args['ders']}"  # Sohbet handler'da yakalanacak

    else:
        return f"❌ Bilinmeyen araç: {func_name}"


# ─── Özet Oluşturucular ────────────────────────────────────

def _gunluk_ozet_olustur() -> str:
    bugun = date.today()
    cikti = f"📊 Günlük Özet — {bugun.strftime('%d.%m.%Y')}\n\n"

    # Kilo
    sk = son_kilo()
    if sk:
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        cikti += f"⚖️ Kilo: {sk['kilo']} kg (hedef {hedef})\n"

    # Çalışma
    gc = gunluk_calisma()
    if gc:
        cikti += "\n📚 Bugünkü çalışma:\n"
        for ders, dk in gc.items():
            saat = dk // 60
            kalan = dk % 60
            cikti += f"  • {ders.upper()}: {saat}s {kalan}dk\n" if saat else f"  • {ders.upper()}: {kalan}dk\n"
        toplam = sum(gc.values())
        cikti += f"  Toplam: {toplam} dakika\n"
    else:
        cikti += "\n📚 Bugün henüz çalışma yok\n"

    # Görevler
    gorevler = gunun_gorevleri()
    if gorevler:
        tamam = sum(1 for g in gorevler if g["durum"] == "tamamlandi")
        cikti += f"\n✅ Görevler: {tamam}/{len(gorevler)} tamamlandı\n"

    # Geri sayım
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days
    cikti += f"\n⏳ CENT-S: {cents_kalan} gün | SAT: {sat_kalan} gün\n"

    return cikti


def _haftalik_ozet_olustur() -> str:
    cikti = "📊 Haftalık Özet\n\n"

    hc = haftalik_calisma()
    if hc:
        cikti += "📚 Son 7 gün çalışma:\n"
        for ders, dk in hc.items():
            saat = dk // 60
            kalan = dk % 60
            cikti += f"  • {ders.upper()}: {saat}s {kalan}dk\n"
        toplam = sum(hc.values())
        cikti += f"  Toplam: {toplam // 60}s {toplam % 60}dk\n"

    detay = haftalik_gunluk_detay()
    if detay:
        cikti += "\n📅 Gün gün:\n"
        gun_gruplari = {}
        for d in detay:
            gun_gruplari.setdefault(d["tarih"], []).append(d)
        for tarih, dersler in gun_gruplari.items():
            toplam = sum(d["toplam"] for d in dersler)
            cikti += f"  {tarih}: {toplam} dk\n"

    kg = kilo_gecmisi(7)
    if kg:
        cikti += "\n⚖️ Kilo trendi:\n"
        for k in reversed(kg):
            cikti += f"  {k['tarih']}: {k['kilo']} kg\n"

    stats = genel_istatistik()
    cikti += f"\n📈 Genel: {stats['tamamlanan_gorev']}/{stats['toplam_gorev']} görev tamamlandı\n"

    return cikti


# ─── Pomodoro ──────────────────────────────────────────────

async def _pomodoro_dongusu(update: Update, context: ContextTypes.DEFAULT_TYPE, ders: str):
    """Pomodoro zamanlayıcısı — 25dk çalışma + 5dk mola."""
    user_id = update.effective_user.id

    if user_id in aktif_pomodorolar:
        await update.message.reply_text("⏱️ Zaten aktif bir pomodoro var!")
        return

    aktif_pomodorolar[user_id] = True

    await update.message.reply_text(
        f"🍅 Pomodoro başladı!\n"
        f"📚 Ders: {ders.upper()}\n"
        f"⏱️ {POMODORO_CALISMA_DK} dakika çalışma..."
    )

    await asyncio.sleep(POMODORO_CALISMA_DK * 60)

    if user_id not in aktif_pomodorolar:
        return

    # Çalışmayı kaydet
    calisma_kaydet(ders, POMODORO_CALISMA_DK)

    await update.message.reply_text(
        f"✅ {POMODORO_CALISMA_DK} dakika tamamlandı!\n"
        f"📚 {ders.upper()} çalışması kaydedildi.\n"
        f"☕ {POMODORO_MOLA_DK} dakika mola!"
    )

    await asyncio.sleep(POMODORO_MOLA_DK * 60)

    if user_id in aktif_pomodorolar:
        del aktif_pomodorolar[user_id]
        await update.message.reply_text("🍅 Mola bitti! Hazırsan yeni pomodoro başlat.")


# ─── Ana Mesaj Handler ─────────────────────────────────────

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Her mesajı AI ajana ilet. Bot zeka ile ne yapacağına karar verir."""

    if not update.message or not update.message.text:
        return

    # Sadece yetkili kullanıcı
    if TELEGRAM_USER_ID and update.effective_user.id != TELEGRAM_USER_ID:
        await update.message.reply_text("⛔ Yetkin yok.")
        return

    mesaj = update.message.text.strip()
    if not mesaj:
        return

    # Bekleniyor…
    bekle = await update.message.reply_text("🤔 Düşünüyorum...")

    # Durum güncelleyici
    adim_sayaci = [0]

    def ilerleme_goster(adim: int, tool_adi: str, args: dict):
        adim_sayaci[0] = adim
        try:
            asyncio.get_event_loop().create_task(
                bekle.edit_text(f"🔧 Adım {adim}: {tool_adi}...")
            )
        except Exception:
            pass

    # Agent loop'u çalıştır (blocking → thread'de)
    ctx = _kullanici_contexti()

    loop = asyncio.get_event_loop()
    cevap = await loop.run_in_executor(
        None,
        lambda: agent_loop(mesaj, ctx, tool_calistir, ilerleme_goster),
    )

    # Pomodoro özel case
    if cevap.startswith("⏱️ POMODORO:"):
        ders = cevap.split(":")[1]
        await bekle.delete()
        asyncio.create_task(_pomodoro_dongusu(update, context, ders))
        return

    # Cevabı gönder (4096 char limit)
    await bekle.delete()

    if len(cevap) <= 4096:
        await update.message.reply_text(cevap)
    else:
        parcalar = [cevap[i : i + 4096] for i in range(0, len(cevap), 4096)]
        for parca in parcalar:
            await update.message.reply_text(parca)
