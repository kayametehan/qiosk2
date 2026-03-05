"""
Sohbet Handler - Ana mesaj işleyici
Her mesaj buraya gelir, AI agent loop ile çözülür.
"""

import asyncio
import logging
from datetime import date
from functools import partial

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import HEDEFLER, POMODORO_CALISMA_DK, POMODORO_MOLA_DK
from bot import database as db
from bot.services import ai_service, web_service, system_service

logger = logging.getLogger(__name__)

# Aktif pomodoro oturumları {user_id: asyncio.Task}
aktif_pomodorolar: dict = {}


# ─── Tool Executor — AI'ın çağırdığı tool'ları çalıştırır ─

def tool_calistir(tool_adi: str, tool_args: dict) -> str:
    """AI'ın istediği tool'u çalıştır ve sonucu döndür."""

    # --- Web Tools ---
    if tool_adi == "web_ara":
        return web_service.web_ara(
            tool_args["sorgu"],
            tool_args.get("max_sonuc", 8),
        )

    elif tool_adi == "sayfa_oku":
        return web_service.sayfa_oku(tool_args["url"])

    elif tool_adi == "haber_ara":
        return web_service.haber_ara(tool_args["sorgu"])

    # --- Dosya/Sistem Tools ---
    elif tool_adi == "dosya_oku":
        return system_service.dosya_oku(tool_args["yol"])

    elif tool_adi == "dosya_yaz":
        return system_service.dosya_yaz(tool_args["yol"], tool_args["icerik"])

    elif tool_adi == "dosya_listele":
        return system_service.dosya_listele(
            tool_args.get("yol", "."),
            tool_args.get("detayli", False),
        )

    elif tool_adi == "komut_calistir":
        return system_service.komut_calistir(
            tool_args["komut"],
            tool_args.get("cwd"),
        )

    elif tool_adi == "uygulama_ac":
        return system_service.uygulama_ac(tool_args["hedef"])

    elif tool_adi == "sistem_bilgisi":
        return system_service.sistem_bilgisi()

    # --- Kişisel Takip Tools ---
    elif tool_adi == "kilo_kaydet":
        kilo = tool_args["kilo"]
        sonuc = db.kilo_kaydet(kilo)
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        fark = kilo - hedef
        return (
            f"Kilo kaydedildi: {kilo} kg (Tarih: {sonuc['tarih']})\n"
            f"Hedef: {hedef} kg | Fark: {fark:+.1f} kg\n"
            f"{'Güncelleme' if sonuc['guncellendi'] else 'Yeni kayıt'}"
        )

    elif tool_adi == "calisma_kaydet":
        ders = tool_args["ders"]
        dakika = tool_args["dakika"]
        sonuc = db.calisma_kaydet(ders, dakika)
        gunluk = db.gunluk_calisma()
        toplam = sum(gunluk.values())
        return (
            f"Çalışma kaydedildi: {ders.upper()} — {dakika} dakika\n"
            f"Bugünkü toplam: {toplam} dakika\n"
            f"Detay: {', '.join(f'{d.upper()}: {dk}dk' for d, dk in gunluk.items())}"
        )

    elif tool_adi == "gorev_ekle":
        gorev_metni = tool_args["gorev"]
        gorev_id = db.gorev_ekle(gorev_metni)
        return f"Görev eklendi (ID: {gorev_id}): {gorev_metni}"

    elif tool_adi == "gorevleri_listele":
        gorevler = db.gunun_gorevleri()
        if not gorevler:
            return "Bugün görev yok."
        satirlar = []
        for g in gorevler:
            durum = {"tamamlandi": "✅", "ertelendi": "⏭️", "bekliyor": "⏳"}.get(g["durum"], "⏳")
            satirlar.append(f"{durum} [{g['id']}] {g['gorev']}")
        return "Bugünkü görevler:\n" + "\n".join(satirlar)

    elif tool_adi == "kilo_gecmisi":
        gun = tool_args.get("gun", 7)
        gecmis = db.kilo_gecmisi(gun)
        if not gecmis:
            return "Kilo kaydı yok."
        satirlar = [f"{k['tarih']}: {k['kilo']} kg" for k in reversed(gecmis)]
        if len(gecmis) >= 2:
            degisim = gecmis[0]["kilo"] - gecmis[-1]["kilo"]
            satirlar.append(f"Değişim: {degisim:+.1f} kg")
        return "Kilo geçmişi:\n" + "\n".join(satirlar)

    elif tool_adi == "ozet_goster":
        return _ozet_olustur()

    elif tool_adi == "haftalik_ozet":
        return _haftalik_ozet_olustur()

    elif tool_adi == "pomodoro_baslat":
        # Pomodoro özel — sadece bilgi döndür, asıl başlatma sohbet handler'da
        return f"POMODORO_TRIGGER:{tool_args['ders']}"

    else:
        return f"Bilinmeyen tool: {tool_adi}"


def _ozet_olustur() -> str:
    """Günlük özet verisi oluştur."""
    bugun = date.today()
    gunluk = db.gunluk_calisma()
    son_kilo = db.son_kilo()
    gorevler = db.gunun_gorevleri()
    istatistik = db.genel_istatistik()

    satirlar = [f"Tarih: {bugun.isoformat()}"]

    # Çalışma
    if gunluk:
        satirlar.append("Bugünkü çalışma: " + ", ".join(f"{d.upper()}: {dk}dk" for d, dk in gunluk.items()))
        satirlar.append(f"Toplam: {sum(gunluk.values())} dakika")
    else:
        satirlar.append("Bugün çalışma yok")

    # Kilo
    if son_kilo:
        fark = son_kilo["kilo"] - HEDEFLER["kilo"]["hedef_kg"]
        satirlar.append(f"Son kilo: {son_kilo['kilo']} kg (Hedef: 75 kg, Fark: {fark:+.1f} kg)")
    else:
        satirlar.append("Kilo kaydı yok")

    # Sınavlar
    for sinav in ["cents", "sat"]:
        kalan = (HEDEFLER[sinav]["sinav_tarihi"] - bugun).days
        if kalan >= 0:
            satirlar.append(f"{HEDEFLER[sinav]['aciklama']}: {kalan} gün kaldı")
        else:
            satirlar.append(f"{HEDEFLER[sinav]['aciklama']}: Tamamlandı")

    # Görevler
    if gorevler:
        tamamlanan = sum(1 for g in gorevler if g["durum"] == "tamamlandi")
        satirlar.append(f"Görevler: {tamamlanan}/{len(gorevler)} tamamlandı")

    satirlar.append(f"Bu hafta toplam çalışma: {istatistik['hafta_calisma_dk']} dakika")

    return "\n".join(satirlar)


def _haftalik_ozet_olustur() -> str:
    """Haftalık özet verisi oluştur."""
    haftalik = db.haftalik_calisma()
    detay = db.haftalik_gunluk_detay()
    kilo_gecmisi = db.kilo_gecmisi(7)
    istatistik = db.genel_istatistik()

    satirlar = ["Haftalık Özet:"]

    if haftalik:
        for ders, dk in haftalik.items():
            satirlar.append(f"  {ders.upper()}: {dk // 60}s {dk % 60}dk")
        toplam = sum(haftalik.values())
        satirlar.append(f"  Toplam: {toplam // 60} saat {toplam % 60} dakika")

    if detay:
        satirlar.append("\nGün gün:")
        gunler = {}
        for d in detay:
            gunler.setdefault(d["tarih"], []).append(f"{d['ders'].upper()}: {d['toplam']}dk")
        for tarih, dersler in gunler.items():
            satirlar.append(f"  {tarih}: {', '.join(dersler)}")

    if kilo_gecmisi:
        satirlar.append("\nKilo trendi:")
        for k in reversed(kilo_gecmisi):
            satirlar.append(f"  {k['tarih']}: {k['kilo']} kg")

    satirlar.append(f"\nToplam görev: {istatistik['tamamlanan_gorev']}/{istatistik['toplam_gorev']}")

    return "\n".join(satirlar)


# ─── Ana Mesaj Handler ────────────────────────────────────

async def mesaj_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Her gelen mesajı işle — AI agent loop ile."""
    mesaj = update.message.text
    user_id = update.effective_user.id

    if not mesaj:
        return

    # "Düşünüyor" göstergesi
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    # Mevcut durum bilgisini topla (AI'a context olarak verilecek)
    ek_context = _kullanici_context_olustur()

    # İlerleme mesajları göndermek için callback
    progress_messages = []

    def progress_fn(step, tool_name, tool_args):
        tool_aciklama = {
            "web_ara": "🔍 İnternette arıyorum...",
            "sayfa_oku": "📄 Sayfayı okuyorum...",
            "haber_ara": "📰 Haberlere bakıyorum...",
            "dosya_oku": "📂 Dosyayı okuyorum...",
            "dosya_yaz": "📝 Dosyaya yazıyorum...",
            "dosya_listele": "📁 Klasörü listeliyorum...",
            "komut_calistir": "💻 Komut çalıştırıyorum...",
            "uygulama_ac": "🚀 Açıyorum...",
            "sistem_bilgisi": "💻 Sistem bilgisi alıyorum...",
            "kilo_kaydet": "⚖️ Kilo kaydediyorum...",
            "calisma_kaydet": "📚 Çalışma kaydediyorum...",
            "gorev_ekle": "📋 Görev ekliyorum...",
            "gorevleri_listele": "📋 Görevlere bakıyorum...",
            "kilo_gecmisi": "📊 Kilo geçmişine bakıyorum...",
            "ozet_goster": "📈 Özet hazırlıyorum...",
            "haftalik_ozet": "📊 Haftalık özet hazırlıyorum...",
            "pomodoro_baslat": "⏱️ Pomodoro hazırlıyorum...",
        }
        progress_messages.append(tool_aciklama.get(tool_name, f"🔧 {tool_name}..."))

    # Agent loop'u ayrı thread'de çalıştır (blocking olduğu için)
    loop = asyncio.get_event_loop()

    # İlerleme mesajı gönderme task'ı
    async def send_progress():
        """Her 3 saniyede bir ilerleme mesajı gönder."""
        sent = set()
        while True:
            await asyncio.sleep(2)
            for msg in progress_messages:
                if msg not in sent:
                    sent.add(msg)
                    try:
                        await context.bot.send_chat_action(
                            chat_id=update.effective_chat.id, action="typing"
                        )
                    except Exception:
                        pass

    progress_task = asyncio.create_task(send_progress())

    try:
        cevap = await loop.run_in_executor(
            None,
            lambda: ai_service.agent_loop(mesaj, ek_context, tool_calistir, progress_fn),
        )
    except Exception as e:
        logger.error(f"Agent loop hatası: {e}")
        cevap = f"😅 Bir sorun oluştu, tekrar dener misin?\n({str(e)[:100]})"
    finally:
        progress_task.cancel()

    # Pomodoro özel tetikleme kontrolü
    if "POMODORO_TRIGGER:" in (cevap or ""):
        # AI pomodoro başlatmak istedi, inline butonlarla sor
        ders = cevap.split("POMODORO_TRIGGER:")[1].split("\n")[0].strip() if "POMODORO_TRIGGER:" in cevap else "sat"
        await _pomodoro_buton_gonder(update, context, ders)
        return

    # Cevabı gönder (uzunsa parçala)
    if cevap:
        await _uzun_mesaj_gonder(update, cevap)


async def _uzun_mesaj_gonder(update: Update, metin: str):
    """4096 karakterden uzun mesajları parçalayarak gönder."""
    MAX = 4000  # Telegram limiti 4096, biraz pay bırak

    if len(metin) <= MAX:
        try:
            await update.message.reply_text(metin, parse_mode="Markdown")
        except Exception:
            # Markdown parse hatası olursa düz gönder
            await update.message.reply_text(metin)
        return

    # Parçala
    parcalar = []
    while metin:
        if len(metin) <= MAX:
            parcalar.append(metin)
            break

        # En yakın satır sonundan kes
        kesim = metin.rfind("\n", 0, MAX)
        if kesim == -1:
            kesim = MAX

        parcalar.append(metin[:kesim])
        metin = metin[kesim:].lstrip("\n")

    for parca in parcalar:
        try:
            await update.message.reply_text(parca, parse_mode="Markdown")
        except Exception:
            await update.message.reply_text(parca)


# ─── /start komutu ───────────────────────────────────────

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """İlk karşılama mesajı."""
    bugun = date.today()
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days
    son_kilo = db.son_kilo()
    kilo_str = f"{son_kilo['kilo']} kg" if son_kilo else "?"

    mesaj = f"""🤖 *Selam! Ben senin kişisel asistanınım!*

Benimle normal konuşabilirsin, ne istediğini anlarım.

📋 *Hedeflerini biliyorum:*
⚖️ Kilo: {kilo_str} → 75 kg
📚 CENT-S: {'✅ Bitti' if cents_kalan < 0 else f'{cents_kalan} gün kaldı'}
📚 SAT: {'✅ Bitti' if sat_kalan < 0 else f'{sat_kalan} gün kaldı'}

💬 *Benimle şöyle konuşabilirsin:*
• "81.5 kiloyum" → kaydederim
• "1 saat SAT çalıştım" → kaydederim
• "bugün ne yapayım" → plan yaparım
• "ne yesem" → diyet önerisi veririm
• "nasıl gidiyorum" → özet çıkarırım
• "İstanbul'da güzel otel bul" → araştırırım
• "masaüstündeki dosyaları göster" → gösteririm
• "hava durumuna bak" → bakarım

🧠 *Hiçbir komut ezberleme — sadece yaz!*"""

    await update.message.reply_text(mesaj, parse_mode="Markdown")


# ─── /id komutu ──────────────────────────────────────────

async def id_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kullanıcı ID'sini göster."""
    await update.message.reply_text(
        f"🆔 Telegram ID'n: `{update.effective_user.id}`\n"
        f"Bunu `.env` dosyasındaki `TELEGRAM_USER_ID`'ye yaz.",
        parse_mode="Markdown",
    )


# ─── Pomodoro Sistemi ────────────────────────────────────

async def _pomodoro_buton_gonder(update: Update, context: ContextTypes.DEFAULT_TYPE, ders: str):
    """Pomodoro başlatma butonları gönder."""
    keyboard = [
        [
            InlineKeyboardButton(f"▶️ {ders.upper()} Pomodoro Başlat", callback_data=f"pomo_start_{ders}"),
            InlineKeyboardButton("❌ Vazgeç", callback_data="pomo_iptal"),
        ],
    ]
    await update.message.reply_text(
        f"⏱️ *{ders.upper()} Pomodoro*\n{POMODORO_CALISMA_DK}dk çalış → {POMODORO_MOLA_DK}dk mola\n\nBaşlayalım mı?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline buton callback'leri."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data.startswith("pomo_start_"):
        ders = data.replace("pomo_start_", "")

        if user_id in aktif_pomodorolar:
            await query.edit_message_text("⚠️ Zaten aktif bir pomodoro var!")
            return

        await query.edit_message_text(
            f"🔴 *{ders.upper()} Pomodoro Başladı!*\n\n"
            f"⏱️ {POMODORO_CALISMA_DK} dakika — Konsantre ol! 💪\n"
            f"_Bitince haber vereceğim..._",
            parse_mode="Markdown",
        )

        task = asyncio.create_task(_pomodoro_timer(context, user_id, ders, update.effective_chat.id))
        aktif_pomodorolar[user_id] = task

    elif data == "pomo_iptal":
        task = aktif_pomodorolar.pop(user_id, None)
        if task:
            task.cancel()
        await query.edit_message_text("❌ Pomodoro iptal edildi.")

    elif data.startswith("pomo_tekrar_"):
        ders = data.replace("pomo_tekrar_", "")
        await query.edit_message_text(
            f"🔴 *{ders.upper()} Pomodoro Tekrar Başladı!*\n⏱️ {POMODORO_CALISMA_DK} dakika 💪",
            parse_mode="Markdown",
        )
        task = asyncio.create_task(_pomodoro_timer(context, user_id, ders, update.effective_chat.id))
        aktif_pomodorolar[user_id] = task

    elif data.startswith("gorev_tamam_"):
        gorev_id = int(data.replace("gorev_tamam_", ""))
        db.gorev_tamamla(gorev_id)
        await query.edit_message_text("✅ Görev tamamlandı!")

    elif data.startswith("gorev_ertele_"):
        gorev_id = int(data.replace("gorev_ertele_", ""))
        db.gorev_ertele(gorev_id)
        await query.edit_message_text("⏭️ Görev ertelendi.")


async def _pomodoro_timer(context, user_id: int, ders: str, chat_id: int):
    """Pomodoro zamanlayıcı."""
    try:
        await asyncio.sleep(POMODORO_CALISMA_DK * 60)
        db.calisma_kaydet(ders, POMODORO_CALISMA_DK)

        keyboard = [
            [
                InlineKeyboardButton("🔄 Tekrar", callback_data=f"pomo_tekrar_{ders}"),
                InlineKeyboardButton("✅ Bitir", callback_data="pomo_iptal"),
            ],
        ]

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ *{POMODORO_CALISMA_DK}dk {ders.upper()} tamamlandı!*\n\n"
                 f"☕ {POMODORO_MOLA_DK}dk mola zamanı!\n"
                 f"📊 Otomatik kaydedildi.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
    except asyncio.CancelledError:
        pass
    finally:
        aktif_pomodorolar.pop(user_id, None)


# ─── Yardımcılar ─────────────────────────────────────────

def _kullanici_context_olustur() -> str:
    """Kullanıcının mevcut durumunu AI'a context olarak hazırla."""
    bugun = date.today()
    satirlar = []

    # Kilo
    son_kilo = db.son_kilo()
    if son_kilo:
        satirlar.append(f"Son kilo: {son_kilo['kilo']} kg ({son_kilo['tarih']})")

    # Bugünkü çalışma
    gunluk = db.gunluk_calisma()
    if gunluk:
        satirlar.append("Bugünkü çalışma: " + ", ".join(f"{d.upper()}: {dk}dk" for d, dk in gunluk.items()))

    # Sınavlar
    for sinav in ["cents", "sat"]:
        kalan = (HEDEFLER[sinav]["sinav_tarihi"] - bugun).days
        if kalan >= 0:
            satirlar.append(f"{HEDEFLER[sinav]['aciklama']}: {kalan} gün kaldı")

    # Görevler
    gorevler = db.gunun_gorevleri()
    if gorevler:
        bekleyen = [g for g in gorevler if g["durum"] == "bekliyor"]
        if bekleyen:
            satirlar.append(f"Bekleyen görevler: {', '.join(g['gorev'] for g in bekleyen)}")

    return "\n".join(satirlar) if satirlar else "Henüz kayıt yok."
