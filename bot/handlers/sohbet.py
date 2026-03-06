"""
Sohbet Handler — Ana mesaj işleyici.
Onboarding tanışma, konuşma hafızası, sesli mesaj, ekran görüntüsü,
onay mekanizması, Excel, hafıza, 40+ tool executor, async.
"""

import asyncio
import logging
import os
import tempfile
from datetime import date
from functools import partial

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
    hafiza_kaydet,
    hafiza_sil,
    hafizalari_getir,
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
from bot.services.excel_service import excel_duzenle, excel_oku, excel_olustur
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

# Bekleyen ekran görüntüleri (Telegram'a fotoğraf olarak gönderilecek)
_bekleyen_fotograflar = []

# Onay bekleyen işlemler: {user_id: {"func_name": ..., "func_args": ..., "aciklama": ...}}
bekleyen_islemler = {}

# Onay gerektiren tehlikeli tool'lar
ONAY_GEREKEN_TOOLLAR = {"islem_kapat", "kendi_kodunu_duzenle"}
ONAY_KELIMELERI = {"evet", "onay", "onayla", "yap", "tamam", "ok", "olur"}
IPTAL_KELIMELERI = {"hayır", "iptal", "vazgeç", "yok", "yapma"}


def _onay_gerekli_mi(func_name: str, func_args: dict) -> bool:
    """Bu tool çağrısı onay gerektiriyor mu?"""
    if func_name in ONAY_GEREKEN_TOOLLAR:
        return True
    if func_name == "komut_calistir":
        komut = func_args.get("komut", "").lower()
        tehlikeli = ["rm ", "rm -", "rmdir", "del ", "format ", "mkfs",
                     "dd if=", "shutdown", "reboot", "kill ", "killall"]
        return any(d in komut for d in tehlikeli)
    return False


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

def tool_calistir(func_name: str, func_args: dict, user_id: int = 0) -> str:
    """Tool adını ve argümanlarını alıp ilgili fonksiyonu çağırır.
    user_id verilirse tehlikeli işlemlerde onay mekanizması devreye girer.
    """

    # ── Onay mekanizması ──
    if user_id and _onay_gerekli_mi(func_name, func_args):
        aciklama_map = {
            "islem_kapat": f"🔴 '{func_args.get('islem_adi', '?')}' işlemi kapatılacak",
            "kendi_kodunu_duzenle": f"📝 '{func_args.get('dosya_yolu', '?')}' dosyası düzenlenecek",
            "komut_calistir": f"💻 Tehlikeli komut: {func_args.get('komut', '?')[:80]}",
        }
        aciklama = aciklama_map.get(func_name, f"⚠️ {func_name} çağrılacak")
        bekleyen_islemler[user_id] = {
            "func_name": func_name,
            "func_args": func_args,
            "aciklama": aciklama,
        }
        return (
            f"⚠️ ONAY GEREKLİ!\n{aciklama}\n\n"
            f"Bu işlemi yapmamı onaylıyor musun? (evet/hayır)"
        )

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
        sonuc = ekran_goruntusu(func_args.get("kayit_yolu"))
        # Dosya yolunu çıkar ve fotoğraf listesine ekle (Telegram'a gönderilecek)
        if "kaydedildi:" in sonuc:
            yol = sonuc.split("kaydedildi: ", 1)[-1].strip()
            if os.path.exists(yol):
                _bekleyen_fotograflar.append(yol)
        return sonuc
    elif func_name == "panoya_kopyala":
        return panoya_kopyala(func_args["metin"])
    elif func_name == "panodan_oku":
        return panodan_oku()

    # === Excel ===
    elif func_name == "excel_oku":
        return excel_oku(func_args["yol"], func_args.get("sayfa"))
    elif func_name == "excel_olustur":
        return excel_olustur(
            func_args["yol"], func_args["basliklar"],
            func_args.get("veriler"), func_args.get("sayfa_adi", "Sayfa1"),
        )
    elif func_name == "excel_duzenle":
        return excel_duzenle(func_args["yol"], func_args["islemler"])

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

    # === Hafıza ===
    elif func_name == "hafiza_notu_ekle":
        nid = hafiza_kaydet(
            func_args["kategori"], func_args["icerik"],
            func_args.get("onem", 5),
        )
        return f"🧠 Hafızaya kaydedildi (ID: {nid}): [{func_args['kategori']}] {func_args['icerik']}"

    elif func_name == "hafiza_notlari_goster":
        notlar = hafizalari_getir(30)
        if not notlar:
            return "🧠 Uzun süreli hafızada henüz not yok."
        cikti = "🧠 Uzun Süreli Hafıza Notları:\n\n"
        for n in notlar:
            cikti += f"  [{n['id']}] ⭐{n['onem']} [{n['kategori']}] {n['icerik']}\n"
            cikti += f"      📅 {n['tarih']}\n"
        return cikti

    elif func_name == "hafiza_notu_sil":
        ok = hafiza_sil(func_args["hafiza_id"])
        return (
            f"✅ Hafıza notu #{func_args['hafiza_id']} silindi."
            if ok else f"❌ Hafıza notu #{func_args['hafiza_id']} bulunamadı."
        )

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
# ORTAK MESAJ İŞLEME
# ═══════════════════════════════════════════════════════════

async def _mesaji_isle(update: Update, context: ContextTypes.DEFAULT_TYPE,
                       mesaj: str, bekle_msg=None):
    """Metin veya ses mesajını işle — ortak mantık."""
    global _bekleyen_fotograflar

    user_id = update.effective_user.id

    # ── Onay bekleyen işlem var mı? ──
    if user_id in bekleyen_islemler:
        if mesaj.lower().strip() in ONAY_KELIMELERI:
            islem = bekleyen_islemler.pop(user_id)
            try:
                sonuc = tool_calistir(islem["func_name"], islem["func_args"], user_id=0)
            except Exception as e:
                sonuc = f"❌ İşlem hatası: {str(e)}"
            if bekle_msg:
                try:
                    await bekle_msg.delete()
                except Exception:
                    pass
            await update.message.reply_text(f"✅ İşlem yapıldı:\n\n{sonuc}")
            return
        elif mesaj.lower().strip() in IPTAL_KELIMELERI:
            bekleyen_islemler.pop(user_id)
            if bekle_msg:
                try:
                    await bekle_msg.delete()
                except Exception:
                    pass
            await update.message.reply_text("❌ İşlem iptal edildi.")
            return
        else:
            # Farklı mesaj geldi — bekleyen işlemi iptal et, yeni mesajı işle
            bekleyen_islemler.pop(user_id)

    # ── Onboarding kontrolü ──
    if not onboarding_tamamlandi():
        handled = await _onboarding_handler(update, context, mesaj)
        if handled:
            if bekle_msg:
                try:
                    await bekle_msg.delete()
                except Exception:
                    pass
            return

    # ── AI Ajan ──
    if not bekle_msg:
        bekle_msg = await update.message.reply_text("🤔 Düşünüyorum...")

    async def ilerleme_goster(adim: int, tool_adi: str, args: dict):
        try:
            await bekle_msg.edit_text(f"🔧 Adım {adim}: {tool_adi}...")
        except Exception:
            pass

    ctx = _kullanici_contexti()
    _bekleyen_fotograflar.clear()

    # user_id'li executor (onay mekanizması için)
    _tool_executor = partial(tool_calistir, user_id=user_id)

    cevap = await agent_loop(mesaj, ctx, _tool_executor, ilerleme_goster)

    # Pomodoro özel case
    if cevap.startswith("⏱️ POMODORO:"):
        ders = cevap.split(":")[1]
        await bekle_msg.delete()
        asyncio.create_task(_pomodoro_dongusu(update, context, ders))
        return

    # Cevabı gönder (4096 char limit)
    try:
        await bekle_msg.delete()
    except Exception:
        pass

    if len(cevap) <= 4096:
        await update.message.reply_text(cevap)
    else:
        parcalar = [cevap[i : i + 4096] for i in range(0, len(cevap), 4096)]
        for parca in parcalar:
            await update.message.reply_text(parca)

    # Bekleyen ekran görüntülerini fotoğraf olarak gönder
    for foto_yol in _bekleyen_fotograflar:
        try:
            with open(foto_yol, "rb") as f:
                await update.message.reply_photo(photo=f, caption="📸 Ekran görüntüsü")
        except Exception as e:
            logger.error(f"Fotoğraf gönderilemedi: {e}")
    _bekleyen_fotograflar.clear()


# ═══════════════════════════════════════════════════════════
# ANA MESAJ HANDLER
# ═══════════════════════════════════════════════════════════

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Her metin mesajını işle: onboarding → onay kontrolü → AI ajan."""

    if not update.message or not update.message.text:
        return

    # Sadece yetkili kullanıcı
    if TELEGRAM_USER_ID and update.effective_user.id != TELEGRAM_USER_ID:
        await update.message.reply_text("⛔ Yetkin yok.")
        return

    mesaj = update.message.text.strip()
    if not mesaj:
        return

    await _mesaji_isle(update, context, mesaj)


# ═══════════════════════════════════════════════════════════
# SESLİ MESAJ HANDLER
# ═══════════════════════════════════════════════════════════

async def sesli_mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sesli mesajları işle: indir → çevir → metne dönüştür → AI'ya gönder."""

    if not update.message:
        return

    if TELEGRAM_USER_ID and update.effective_user.id != TELEGRAM_USER_ID:
        await update.message.reply_text("⛔ Yetkin yok.")
        return

    bekle = await update.message.reply_text("🎤 Sesli mesaj işleniyor...")

    try:
        voice = update.message.voice or update.message.audio
        if not voice:
            await bekle.edit_text("❌ Sesli mesaj bulunamadı.")
            return

        # Dosyayı indir
        file = await context.bot.get_file(voice.file_id)
        ogg_path = tempfile.mktemp(suffix=".ogg")
        await file.download_to_drive(ogg_path)

        wav_path = ogg_path.replace(".ogg", ".wav")

        # OGG → WAV dönüşümü (pydub + ffmpeg)
        try:
            from pydub import AudioSegment

            audio = AudioSegment.from_ogg(ogg_path)
            audio.export(wav_path, format="wav")
        except ImportError:
            await bekle.edit_text(
                "❌ Sesli mesaj desteği için gerekli paketler eksik.\n"
                "Kur: pip install pydub SpeechRecognition\n"
                "Ve ffmpeg yükle: brew install ffmpeg"
            )
            return
        except Exception as e:
            await bekle.edit_text(
                f"❌ Ses dönüştürme hatası.\n"
                f"ffmpeg kurulu mu? (brew install ffmpeg)\n{str(e)[:100]}"
            )
            return

        # Ses → Metin (Google Speech Recognition — ücretsiz, Türkçe)
        try:
            import speech_recognition as sr

            recognizer = sr.Recognizer()
            with sr.AudioFile(wav_path) as source:
                audio_data = recognizer.record(source)
            metin = recognizer.recognize_google(audio_data, language="tr-TR")
        except ImportError:
            await bekle.edit_text(
                "❌ SpeechRecognition paketi eksik.\nKur: pip install SpeechRecognition"
            )
            return
        except Exception as e:
            err_str = str(e).lower()
            if "could not understand" in err_str or "unknownvalue" in err_str:
                await bekle.edit_text("❌ Ses anlaşılamadı. Lütfen daha net konuşup tekrar dene.")
            else:
                await bekle.edit_text(f"❌ Ses tanıma hatası: {str(e)[:120]}")
            return
        finally:
            # Geçici dosyaları temizle
            for p in [ogg_path, wav_path]:
                try:
                    os.unlink(p)
                except OSError:
                    pass

        await bekle.edit_text(f'🎤 Anlaşılan: "{metin}"\n\n🤔 Düşünüyorum...')

        # AI'ya metin olarak gönder
        await _mesaji_isle(update, context, metin, bekle_msg=bekle)

    except Exception as e:
        logger.error(f"Sesli mesaj hatası: {e}")
        try:
            await bekle.edit_text(f"❌ Sesli mesaj işlenemedi: {str(e)[:100]}")
        except Exception:
            pass
