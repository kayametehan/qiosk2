"""
Sohbet Handler — Ana mesaj işleyici.
Onboarding tanışma, konuşma hafızası, 30+ tool executor, async.
"""

import asyncio
import logging
from datetime import date

from telegram import Update
from telegram.ext import ContextTypes

from bot.database import (
    calisma_kaydet,
    deneme_gecmisi,
    deneme_kaydet,
    genel_istatistik,
    gorev_ekle,
    gorev_ertele,
    gorev_tamamla,
    gunluk_calisma,
    gunluk_kalori,
    gunluk_ogunler,
    gunun_gorevleri,
    haftalik_calisma,
    haftalik_gunluk_detay,
    kilo_gecmisi,
    kilo_kaydet,
    ogun_kaydet,
    onboarding_tamamlandi,
    profil_ayarla,
    profil_tumu,
    sohbet_temizle as _sohbet_temizle,
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
from bot.services.skill_manager import (
    kendi_kodunu_duzenle,
    kendi_kodunu_oku,
    skill_calistir as _skill_calistir,
    skill_listele as _skill_listele,
    skill_olustur as _skill_olustur,
    skill_sil as _skill_sil,
    skill_var_mi,
)
from config import HEDEFLER, POMODORO_CALISMA_DK, POMODORO_MOLA_DK, TELEGRAM_USER_ID

logger = logging.getLogger(__name__)

# Aktif pomodoro'lar
aktif_pomodorolar = {}


# ═══════════════════════════════════════════════════════════
# ONBOARDING — İlk Tanışma
# ═══════════════════════════════════════════════════════════

ONBOARDING_SORULARI = [
    ("isim", "👋 Merhaba! Ben senin kişisel AI asistanınım. Seninle tanışmak istiyorum!\n\n📝 İsmin ne?"),
    ("yas", "Güzel tanıştığıma memnun oldum {isim}! 🎉\n\n🎂 Kaç yaşındasın?"),
    ("meslek", "Harika! 💫\n\n🎓 Ne yapıyorsun? (öğrenci, çalışan, vs.)"),
    ("ilgi_alanlari", "Süper! 🌟\n\n🎮 Hobilerin ve ilgi alanların neler? (virgülle ayır)"),
    ("gunluk_rutin", "Çok iyi! 📋\n\n⏰ Günlük rutinin nasıl? (kaçta kalkıyorsun, ne zaman ders çalışıyorsun, vs.)"),
]

ONBOARDING_BITIS = """🎉 Tanışma tamamlandı, {isim}! Artık seni tanıyorum.

İşte yapabileceklerim:

🌐 **İnternet**
• Web araması, haber takibi
• Sayfa okuma, dosya indirme

📊 **Kişisel Takip**
• ⚖️ Kilo takibi (75 kg hedef)
• 📚 Ders çalışma süresi (SAT & CENT-S)
• 📝 Deneme sınavı skor takibi
• ✅ Görev yönetimi (ekle/tamamla/ertele)
• 🍽️ Öğün & kalori takibi
• 🍅 Pomodoro zamanlayıcı

💻 **Bilgisayar**
• Dosya okuma/yazma/arama
• Terminal komutları
• Uygulama açma
• Ekran görüntüsü, pano
• İşlem yönetimi

🧠 **Kendini Geliştirme**
• Yeni yetenekler oluşturabiliyorum
• Kendi kodumu okuyup düzenleyebiliyorum

💬 **Konuşma Hafızası**
• Önceki konuşmalarımızı hatırlıyorum!

Sadece yaz, ben hallederim! 🚀"""


async def _onboarding_handler(update: Update, context: ContextTypes.DEFAULT_TYPE, mesaj: str) -> bool:
    """Onboarding sürecini yönet. True dönerse mesaj işlendi demektir."""

    # Hangi adımdayız?
    profil = profil_tumu()
    adim = int(profil.get("onboarding_adim", "0"))

    if adim >= len(ONBOARDING_SORULARI):
        return False  # Onboarding bitti, normal akışa devam

    anahtar, _ = ONBOARDING_SORULARI[adim]

    # Cevabı kaydet
    profil_ayarla(anahtar, mesaj)

    # Sonraki adıma geç
    sonraki_adim = adim + 1
    profil_ayarla("onboarding_adim", str(sonraki_adim))

    if sonraki_adim < len(ONBOARDING_SORULARI):
        # Sonraki soruyu sor
        _, sonraki_soru = ONBOARDING_SORULARI[sonraki_adim]
        # Placeholders
        profil_guncel = profil_tumu()
        for k, v in profil_guncel.items():
            sonraki_soru = sonraki_soru.replace(f"{{{k}}}", v)
        await update.message.reply_text(sonraki_soru)
    else:
        # Onboarding bitti!
        profil_ayarla("onboarding_bitti", "evet")
        profil_guncel = profil_tumu()
        bitis = ONBOARDING_BITIS.replace("{isim}", profil_guncel.get("isim", "dostum"))
        await update.message.reply_text(bitis)

    return True


# ═══════════════════════════════════════════════════════════
# CONTEXT OLUŞTURUCU
# ═══════════════════════════════════════════════════════════

def _kullanici_contexti() -> str:
    """Mevcut istatistikleri AI'ya context olarak ver."""
    bugun = date.today()
    parcalar = []

    # Profil bilgileri
    profil = profil_tumu()
    if profil.get("isim"):
        parcalar.append(f"Kullanıcı: {profil['isim']}")
    if profil.get("yas"):
        parcalar.append(f"Yaş: {profil['yas']}")
    if profil.get("meslek"):
        parcalar.append(f"Meslek: {profil['meslek']}")
    if profil.get("ilgi_alanlari"):
        parcalar.append(f"İlgi alanları: {profil['ilgi_alanlari']}")
    if profil.get("gunluk_rutin"):
        parcalar.append(f"Günlük rutin: {profil['gunluk_rutin']}")

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

    # Öğünler + kalori
    ogunler = gunluk_ogunler()
    if ogunler:
        toplam_kal = gunluk_kalori()
        parcalar.append(f"Bugün {len(ogunler)} öğün, ~{toplam_kal} kcal")

    # Geri sayım
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days
    if cents_kalan > 0:
        parcalar.append(f"CENT-S sınavına {cents_kalan} gün")
    if sat_kalan > 0:
        parcalar.append(f"SAT sınavına {sat_kalan} gün")

    return "\n".join(parcalar) if parcalar else ""


# ═══════════════════════════════════════════════════════════
# TOOL EXECUTOR — 30+ tool
# ═══════════════════════════════════════════════════════════

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
        return dosya_ara(func_args["baslangic_yolu"], func_args["desen"], func_args.get("icerik_ara"))

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
        return (f"✅ {result['tarih']}: {result['kilo']} kg kaydedildi"
                + (" (güncellendi)" if result.get("guncellendi") else ""))

    elif func_name == "calisma_kaydet":
        result = calisma_kaydet(func_args["ders"], func_args["dakika"])
        return f"✅ {result['ders']} çalışması kaydedildi: {result['dakika']} dakika"

    elif func_name == "ogun_kaydet":
        result = ogun_kaydet(func_args["ogun_tipi"], func_args["icerik"], func_args.get("kalori", 0))
        toplam = gunluk_kalori()
        return (f"🍽️ Öğün kaydedildi: {result['ogun_tipi']} — {result['icerik']}\n"
                f"   ~{result['kalori']} kcal\n"
                f"📊 Bugünkü toplam: ~{toplam} kcal")

    elif func_name == "gorev_ekle":
        gorev_id = gorev_ekle(func_args["gorev"])
        return f"✅ Görev eklendi (ID: {gorev_id}): {func_args['gorev']}"

    elif func_name == "gorev_tamamla":
        ok = gorev_tamamla(func_args["gorev_id"])
        return f"✅ Görev #{func_args['gorev_id']} tamamlandı!" if ok else f"❌ Görev #{func_args['gorev_id']} bulunamadı."

    elif func_name == "gorev_ertele":
        ok = gorev_ertele(func_args["gorev_id"])
        return f"↩️ Görev #{func_args['gorev_id']} ertelendi." if ok else f"❌ Görev #{func_args['gorev_id']} bulunamadı."

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

    elif func_name == "deneme_kaydet":
        result = deneme_kaydet(
            func_args["sinav_turu"], func_args["puan"],
            func_args.get("bolum"), func_args.get("toplam", 0), func_args.get("notlar"),
        )
        return (f"📝 Deneme kaydedildi!\n"
                f"   {result['sinav_turu'].upper()} — {result['puan']}"
                + (f"/{result['toplam']}" if result['toplam'] else "")
                + (f" ({result['bolum']})" if result['bolum'] else ""))

    elif func_name == "deneme_gecmisi":
        gecmis = deneme_gecmisi(func_args.get("sinav_turu"))
        if not gecmis:
            return "📊 Henüz deneme sınavı kaydı yok."
        cikti = "📊 Deneme Sınavı Geçmişi:\n\n"
        for d in gecmis:
            cikti += f"  {d['tarih']}: {d['sinav_turu'].upper()}"
            if d['bolum']:
                cikti += f" ({d['bolum']})"
            cikti += f" — {d['puan']}"
            if d['toplam']:
                cikti += f"/{d['toplam']}"
            if d['notlar']:
                cikti += f" 📝 {d['notlar']}"
            cikti += "\n"
        return cikti

    elif func_name == "ozet_goster":
        return _gunluk_ozet_olustur()
    elif func_name == "haftalik_ozet":
        return _haftalik_ozet_olustur()

    elif func_name == "pomodoro_baslat":
        return f"⏱️ POMODORO:{func_args['ders']}"

    elif func_name == "sohbet_temizle":
        _sohbet_temizle()
        return "🧹 Konuşma geçmişi temizlendi. Yeni bir sayfa açtık!"

    # === Skill Yönetimi ===
    elif func_name == "skill_olustur":
        return _skill_olustur(func_args["ad"], func_args["aciklama"],
                              func_args["parametreler_json"], func_args["fonksiyon_kodu"])
    elif func_name == "skill_listele":
        return _skill_listele()
    elif func_name == "skill_sil":
        return _skill_sil(func_args["ad"])
    elif func_name == "kendi_kodunu_oku":
        return kendi_kodunu_oku(func_args["dosya_yolu"])
    elif func_name == "kendi_kodunu_duzenle":
        return kendi_kodunu_duzenle(func_args["dosya_yolu"], func_args["eski_metin"], func_args["yeni_metin"])

    else:
        # Dinamik skill kontrolü
        if skill_var_mi(func_name):
            return _skill_calistir(func_name, func_args)
        return f"❌ Bilinmeyen araç: {func_name}"


# ═══════════════════════════════════════════════════════════
# ÖZET OLUŞTURUCULAR
# ═══════════════════════════════════════════════════════════

def _gunluk_ozet_olustur() -> str:
    bugun = date.today()
    cikti = f"📊 Günlük Özet — {bugun.strftime('%d.%m.%Y')}\n\n"

    sk = son_kilo()
    if sk:
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        cikti += f"⚖️ Kilo: {sk['kilo']} kg (hedef {hedef})\n"

    gc = gunluk_calisma()
    if gc:
        cikti += "\n📚 Bugünkü çalışma:\n"
        for ders, dk in gc.items():
            saat, kalan = dk // 60, dk % 60
            cikti += f"  • {ders.upper()}: {saat}s {kalan}dk\n" if saat else f"  • {ders.upper()}: {kalan}dk\n"
        cikti += f"  Toplam: {sum(gc.values())} dakika\n"
    else:
        cikti += "\n📚 Bugün henüz çalışma yok\n"

    gorevler = gunun_gorevleri()
    if gorevler:
        tamam = sum(1 for g in gorevler if g["durum"] == "tamamlandi")
        cikti += f"\n✅ Görevler: {tamam}/{len(gorevler)} tamamlandı\n"

    # Kalori
    toplam_kal = gunluk_kalori()
    if toplam_kal:
        cikti += f"\n🍽️ Kalori: ~{toplam_kal} kcal\n"

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
            saat, kalan = dk // 60, dk % 60
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
            cikti += f"  {tarih}: {sum(d['toplam'] for d in dersler)} dk\n"

    kg = kilo_gecmisi(7)
    if kg:
        cikti += "\n⚖️ Kilo trendi:\n"
        for k in reversed(kg):
            cikti += f"  {k['tarih']}: {k['kilo']} kg\n"

    stats = genel_istatistik()
    cikti += f"\n📈 Genel: {stats['tamamlanan_gorev']}/{stats['toplam_gorev']} görev tamamlandı\n"

    return cikti


# ═══════════════════════════════════════════════════════════
# POMODORO
# ═══════════════════════════════════════════════════════════

async def _pomodoro_dongusu(update: Update, context: ContextTypes.DEFAULT_TYPE, ders: str):
    """Pomodoro zamanlayıcısı — 25dk çalışma + 5dk mola."""
    user_id = update.effective_user.id

    if user_id in aktif_pomodorolar:
        await update.message.reply_text("⏱️ Zaten aktif bir pomodoro var!")
        return

    aktif_pomodorolar[user_id] = True

    await update.message.reply_text(
        f"🍅 Pomodoro başladı!\n📚 Ders: {ders.upper()}\n⏱️ {POMODORO_CALISMA_DK} dakika çalışma..."
    )

    await asyncio.sleep(POMODORO_CALISMA_DK * 60)

    if user_id not in aktif_pomodorolar:
        return

    calisma_kaydet(ders, POMODORO_CALISMA_DK)

    await update.message.reply_text(
        f"✅ {POMODORO_CALISMA_DK} dakika tamamlandı!\n📚 {ders.upper()} kaydedildi.\n☕ {POMODORO_MOLA_DK} dakika mola!"
    )

    await asyncio.sleep(POMODORO_MOLA_DK * 60)

    if user_id in aktif_pomodorolar:
        del aktif_pomodorolar[user_id]
        await update.message.reply_text("🍅 Mola bitti! Hazırsan yeni pomodoro başlat.")


# ═══════════════════════════════════════════════════════════
# ANA MESAJ HANDLER
# ═══════════════════════════════════════════════════════════

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Her mesajı işle: onboarding → AI ajan."""

    if not update.message or not update.message.text:
        return

    # Sadece yetkili kullanıcı
    if TELEGRAM_USER_ID and update.effective_user.id != TELEGRAM_USER_ID:
        await update.message.reply_text("⛔ Yetkin yok.")
        return

    mesaj = update.message.text.strip()
    if not mesaj:
        return

    # ── Onboarding kontrolü ──
    if not onboarding_tamamlandi():
        handled = await _onboarding_handler(update, context, mesaj)
        if handled:
            return

    # ── AI Ajan ──
    bekle = await update.message.reply_text("🤔 Düşünüyorum...")

    # Async progress callback
    async def ilerleme_goster(adim: int, tool_adi: str, args: dict):
        try:
            await bekle.edit_text(f"🔧 Adım {adim}: {tool_adi}...")
        except Exception:
            pass

    ctx = _kullanici_contexti()

    cevap = await agent_loop(mesaj, ctx, tool_calistir, ilerleme_goster)

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
