"""
Türkçe Bot Komutları - Tüm slash komutlar
"""

from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from config import HEDEFLER
from bot import database as db
from bot.services.ai_service import (
    ai_soru_sor,
    calisma_tavsiyesi,
    gunluk_plan_olustur,
    ogun_onerisi,
)


# ─── /basla ──────────────────────────────────────────────

async def basla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Karşılama mesajı ve hedef özeti."""
    bugun = date.today()
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days
    son_kilo = db.son_kilo()

    kilo_str = f"{son_kilo['kilo']} kg" if son_kilo else "henüz kayıt yok"

    mesaj = f"""🤖 *Merhaba! Ben senin kişisel asistanınım!*

📋 *Hedeflerini biliyorum:*

⚖️ *Kilo:* {kilo_str} → Hedef: {HEDEFLER['kilo']['hedef_kg']} kg
📚 *CENT-S:* {HEDEFLER['cents']['aciklama']} — {'✅ Tamamlandı!' if cents_kalan < 0 else f'*{cents_kalan} gün kaldı!*'}
📚 *SAT:* {HEDEFLER['sat']['aciklama']} — {'✅ Tamamlandı!' if sat_kalan < 0 else f'*{sat_kalan} gün kaldı!*'}

🔧 *Kullanabileceğin komutlar:*

📅 /plan — Bugünün AI planı
📊 /hafta — Haftalık özet tablosu
⚖️ /kilo `<değer>` — Kilo kaydet (ör: /kilo 81.5)
📚 /calis `<ders> <dk>` — Çalışma kaydet (ör: /calis sat 45)
🍽️ /ogun — AI öğün önerisi
📈 /ozet — Günlük ilerleme özeti
🤖 /sor `<soru>` — AI'a soru sor
⏱️ /pomodoro — Pomodoro zamanlayıcı başlat
🆔 /id — Telegram ID'ni öğren

💪 *Haydi başlayalım!*"""

    await update.message.reply_text(mesaj, parse_mode="Markdown")


# ─── /id ─────────────────────────────────────────────────

async def kullanici_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcının Telegram ID'sini göster."""
    user_id = update.effective_user.id
    await update.message.reply_text(
        f"🆔 Senin Telegram ID'n: `{user_id}`\n\nBu değeri `.env` dosyasındaki `TELEGRAM_USER_ID` alanına yaz.",
        parse_mode="Markdown",
    )


# ─── /plan ───────────────────────────────────────────────

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI ile bugünün planını oluştur."""
    await update.message.reply_text("🔄 Plan hazırlanıyor, bir saniye...")

    # Mevcut bilgileri topla
    son_kilo = db.son_kilo()
    kilo_str = f"Son kilo: {son_kilo['kilo']} kg (Hedef: 75 kg)" if son_kilo else "Kilo kaydı yok"

    gunluk = db.gunluk_calisma()
    if gunluk:
        calisma_str = "Bugünkü çalışma: " + ", ".join(
            f"{ders.upper()}: {dk} dk" for ders, dk in gunluk.items()
        )
    else:
        calisma_str = "Bugün henüz çalışma kaydı yok"

    plan_mesaj = gunluk_plan_olustur(kilo_str, calisma_str)
    await update.message.reply_text(f"📅 *Bugünün Planı*\n\n{plan_mesaj}", parse_mode="Markdown")


# ─── /hafta ──────────────────────────────────────────────

async def hafta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Haftalık özet tablosu."""
    haftalik = db.haftalik_calisma()
    detay = db.haftalik_gunluk_detay()
    kilo_gecmisi = db.kilo_gecmisi(7)
    istatistik = db.genel_istatistik()

    mesaj = "📊 *Haftalık Özet*\n\n"

    # Çalışma özeti
    mesaj += "📚 *Çalışma Süreleri:*\n"
    if haftalik:
        toplam = 0
        for ders, dk in haftalik.items():
            saat = dk // 60
            kalan_dk = dk % 60
            mesaj += f"  • {ders.upper()}: {saat}s {kalan_dk}dk\n"
            toplam += dk
        saat_t = toplam // 60
        dk_t = toplam % 60
        mesaj += f"  📌 *Toplam: {saat_t} saat {dk_t} dakika*\n"
    else:
        mesaj += "  Henüz kayıt yok\n"

    # Günlük detay
    if detay:
        mesaj += "\n📅 *Gün Gün:*\n"
        gunler = {}
        for d in detay:
            if d["tarih"] not in gunler:
                gunler[d["tarih"]] = []
            gunler[d["tarih"]].append(f"{d['ders'].upper()}: {d['toplam']}dk")

        for tarih, dersler in gunler.items():
            gun_tarihi = tarih[5:]  # MM-DD
            mesaj += f"  {gun_tarihi}: {', '.join(dersler)}\n"

    # Kilo trendi
    mesaj += "\n⚖️ *Kilo Trendi:*\n"
    if kilo_gecmisi:
        for k in reversed(kilo_gecmisi):
            mesaj += f"  {k['tarih'][5:]}: {k['kilo']} kg\n"

        if len(kilo_gecmisi) >= 2:
            fark = kilo_gecmisi[0]["kilo"] - kilo_gecmisi[-1]["kilo"]
            emoji = "📉" if fark < 0 else "📈" if fark > 0 else "➡️"
            mesaj += f"  {emoji} Değişim: {fark:+.1f} kg\n"
    else:
        mesaj += "  Henüz kayıt yok\n"

    # Görev istatistiği
    mesaj += f"\n✅ *Görevler:* {istatistik['tamamlanan_gorev']}/{istatistik['toplam_gorev']} tamamlandı\n"

    await update.message.reply_text(mesaj, parse_mode="Markdown")


# ─── /kilo ───────────────────────────────────────────────

async def kilo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kilo kaydı ekle."""
    if not context.args:
        await update.message.reply_text(
            "⚖️ Kullanım: /kilo <değer>\nÖrnek: /kilo 81.5"
        )
        return

    try:
        kilo_degeri = float(context.args[0].replace(",", "."))
    except ValueError:
        await update.message.reply_text("❌ Geçersiz değer! Örnek: /kilo 81.5")
        return

    if kilo_degeri < 40 or kilo_degeri > 200:
        await update.message.reply_text("❌ Kilo 40-200 kg arasında olmalı!")
        return

    sonuc = db.kilo_kaydet(kilo_degeri)
    hedef = HEDEFLER["kilo"]["hedef_kg"]
    fark = kilo_degeri - hedef

    if fark > 0:
        emoji = "📉"
        durum = f"Hedefe *{fark:.1f} kg* kaldı!"
    elif fark == 0:
        emoji = "🎉"
        durum = "HEDEFE ULAŞTIN! TEBRİKLER!"
    else:
        emoji = "🎯"
        durum = f"Hedefin *{abs(fark):.1f} kg* altındasın!"

    guncelleme = " (güncellendi)" if sonuc["guncellendi"] else ""

    mesaj = f"""⚖️ *Kilo Kaydedildi{guncelleme}!*

📅 Tarih: {sonuc['tarih']}
🔢 Kilo: *{kilo_degeri} kg*
🎯 Hedef: {hedef} kg
{emoji} {durum}"""

    # Kilo trendi
    gecmis = db.kilo_gecmisi(3)
    if len(gecmis) >= 2:
        onceki = gecmis[1]["kilo"]
        degisim = kilo_degeri - onceki
        if degisim < 0:
            mesaj += f"\n\n✅ Son kayda göre *{abs(degisim):.1f} kg* verdin! 💪"
        elif degisim > 0:
            mesaj += f"\n\n⚠️ Son kayda göre *{degisim:.1f} kg* aldın. Bugün dikkat!"
        else:
            mesaj += "\n\n➡️ Son kaydınla aynı. Devam et!"

    await update.message.reply_text(mesaj, parse_mode="Markdown")


# ─── /calis ──────────────────────────────────────────────

async def calis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Çalışma seansı kaydet."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "📚 Kullanım: /calis <ders> <dakika>\n"
            "Örnekler:\n"
            "  /calis sat 45\n"
            "  /calis cents 60"
        )
        return

    ders = context.args[0].lower()
    if ders not in ["sat", "cents"]:
        await update.message.reply_text(
            "❌ Ders adı `sat` veya `cents` olmalı!\n"
            "Örnek: /calis sat 45",
            parse_mode="Markdown",
        )
        return

    try:
        dakika = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Dakika sayı olmalı! Örnek: /calis sat 45")
        return

    if dakika <= 0 or dakika > 600:
        await update.message.reply_text("❌ Dakika 1-600 arasında olmalı!")
        return

    sonuc = db.calisma_kaydet(ders, dakika)

    # Bugünkü toplam
    gunluk = db.gunluk_calisma()
    toplam = sum(gunluk.values())

    # Sınava kalan gün
    bugun = date.today()
    hedef = HEDEFLER.get(ders, {})
    sinav_tarihi = hedef.get("sinav_tarihi")
    kalan = (sinav_tarihi - bugun).days if sinav_tarihi else None

    mesaj = f"""📚 *Çalışma Kaydedildi!*

📖 Ders: *{ders.upper()}*
⏱️ Süre: *{dakika} dakika*
📅 Tarih: {sonuc['tarih']}"""

    if kalan is not None and kalan >= 0:
        mesaj += f"\n⏳ Sınava kalan: *{kalan} gün*"

    mesaj += f"\n\n📊 *Bugünkü Toplam:*"
    for d, dk in gunluk.items():
        mesaj += f"\n  • {d.upper()}: {dk} dk"
    mesaj += f"\n  📌 Toplam: *{toplam} dakika*"

    # Motivasyon
    if dakika >= 60:
        mesaj += "\n\n🔥 Harika bir seans! Böyle devam!"
    elif dakika >= 30:
        mesaj += "\n\n💪 Güzel tempo, devam et!"
    else:
        mesaj += "\n\n✨ Her dakika önemli, aferin!"

    await update.message.reply_text(mesaj, parse_mode="Markdown")


# ─── /ogun ───────────────────────────────────────────────

async def ogun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI ile öğün önerisi al."""
    await update.message.reply_text("🍽️ Öğün planı hazırlanıyor...")

    oneri = ogun_onerisi()
    await update.message.reply_text(f"🍽️ *Bugünün Öğün Planı*\n\n{oneri}", parse_mode="Markdown")


# ─── /ozet ───────────────────────────────────────────────

async def ozet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Günlük ilerleme özeti."""
    bugun = date.today()
    gunluk = db.gunluk_calisma()
    son_kilo_kayit = db.son_kilo()
    gorevler = db.gunun_gorevleri()
    istatistik = db.genel_istatistik()

    mesaj = f"📈 *Günlük Özet — {bugun.strftime('%d.%m.%Y')}*\n\n"

    # Çalışma
    mesaj += "📚 *Bugünkü Çalışma:*\n"
    if gunluk:
        for ders, dk in gunluk.items():
            saat = dk // 60
            kalan_dk = dk % 60
            mesaj += f"  • {ders.upper()}: {saat}s {kalan_dk}dk\n"
    else:
        mesaj += "  Henüz çalışma yok 😴\n"

    # Kilo
    mesaj += "\n⚖️ *Kilo Durumu:*\n"
    if son_kilo_kayit:
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        fark = son_kilo_kayit["kilo"] - hedef
        mesaj += f"  Son: {son_kilo_kayit['kilo']} kg (Hedef: {hedef} kg)\n"
        if fark > 0:
            mesaj += f"  📉 Hedefe {fark:.1f} kg kaldı\n"
    else:
        mesaj += "  Kayıt yok — /kilo ile kaydet!\n"

    # Sınav geri sayımı
    mesaj += "\n⏳ *Sınav Geri Sayımı:*\n"
    for sinav in ["cents", "sat"]:
        hedef_bilgi = HEDEFLER[sinav]
        kalan = (hedef_bilgi["sinav_tarihi"] - bugun).days
        if kalan >= 0:
            mesaj += f"  📚 {hedef_bilgi['aciklama']}: *{kalan} gün*\n"
        else:
            mesaj += f"  ✅ {hedef_bilgi['aciklama']}: Tamamlandı!\n"

    # Görevler
    mesaj += "\n✅ *Görevler:*\n"
    if gorevler:
        for g in gorevler:
            durum_emoji = {"tamamlandi": "✅", "ertelendi": "⏭️", "bekliyor": "⏳"}
            mesaj += f"  {durum_emoji.get(g['durum'], '⏳')} {g['gorev']}\n"
    else:
        mesaj += "  Bugün görev eklenmemiş\n"

    # Haftalık istatistik
    saat = istatistik["hafta_calisma_dk"] // 60
    dk = istatistik["hafta_calisma_dk"] % 60
    mesaj += f"\n📊 *Bu Hafta Toplam:* {saat}s {dk}dk çalışma"

    await update.message.reply_text(mesaj, parse_mode="Markdown")


# ─── /sor ────────────────────────────────────────────────

async def sor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """AI'a serbest soru sor."""
    if not context.args:
        await update.message.reply_text(
            "🤖 Kullanım: /sor <sorun>\n"
            "Örnek: /sor bugün ne çalışmalıyım?"
        )
        return

    soru = " ".join(context.args)
    await update.message.reply_text("🤔 Düşünüyorum...")

    # Ek bilgi olarak mevcut durumu ekle
    gunluk = db.gunluk_calisma()
    son_kilo_kayit = db.son_kilo()

    ek = ""
    if gunluk:
        ek += "Bugünkü çalışma: " + ", ".join(f"{d}: {dk}dk" for d, dk in gunluk.items()) + "\n"
    if son_kilo_kayit:
        ek += f"Son kilo: {son_kilo_kayit['kilo']} kg\n"

    cevap = ai_soru_sor(soru, ek)
    await update.message.reply_text(f"🤖 {cevap}", parse_mode="Markdown")


# ─── /tavsiye ────────────────────────────────────────────

async def tavsiye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Belirli bir ders için çalışma tavsiyesi al."""
    if not context.args:
        await update.message.reply_text(
            "📖 Kullanım: /tavsiye <ders>\nÖrnek: /tavsiye sat"
        )
        return

    ders = context.args[0].lower()
    if ders not in ["sat", "cents"]:
        await update.message.reply_text("❌ Ders `sat` veya `cents` olmalı!", parse_mode="Markdown")
        return

    await update.message.reply_text(f"📖 {ders.upper()} için tavsiye hazırlanıyor...")

    bugun = date.today()
    sinav_tarihi = HEDEFLER[ders]["sinav_tarihi"]
    kalan = (sinav_tarihi - bugun).days

    if kalan < 0:
        await update.message.reply_text(f"✅ {ders.upper()} sınavı zaten geçti!")
        return

    cevap = calisma_tavsiyesi(ders, kalan)
    await update.message.reply_text(f"📖 *{ders.upper()} Çalışma Tavsiyesi*\n\n{cevap}", parse_mode="Markdown")
