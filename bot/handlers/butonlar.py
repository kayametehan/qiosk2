"""
Inline Butonlar ve Callback Handlers
Pomodoro zamanlayıcı, görev yönetimi, hızlı kilo girişi
"""

import asyncio
import logging
from datetime import date

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from config import HEDEFLER, POMODORO_CALISMA_DK, POMODORO_MOLA_DK
from bot import database as db

logger = logging.getLogger(__name__)

# Aktif pomodoro oturumları {user_id: task}
aktif_pomodorolar: dict = {}


# ─── /pomodoro komutu ────────────────────────────────────

async def pomodoro_baslat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pomodoro zamanlayıcı başlat - ders seçimi."""
    keyboard = [
        [
            InlineKeyboardButton("📚 SAT", callback_data="pomo_sat"),
            InlineKeyboardButton("📚 CENT-S", callback_data="pomo_cents"),
        ],
        [
            InlineKeyboardButton("❌ İptal", callback_data="pomo_iptal"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"⏱️ *Pomodoro Zamanlayıcı*\n\n"
        f"📖 {POMODORO_CALISMA_DK} dk çalış → {POMODORO_MOLA_DK} dk mola\n\n"
        f"Hangi ders için başlatmak istiyorsun?",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )


async def _pomodoro_timer(update_or_query, context, ders: str, user_id: int):
    """Pomodoro zamanlayıcı arka plan görevi."""
    try:
        # Çalışma başlıyor
        if hasattr(update_or_query, "edit_message_text"):
            await update_or_query.edit_message_text(
                f"🔴 *{ders.upper()} — Pomodoro Başladı!*\n\n"
                f"⏱️ {POMODORO_CALISMA_DK} dakika çalışma zamanı!\n"
                f"Konsantre ol, yapabilirsin! 💪\n\n"
                f"_Bittiğinde sana haber vereceğim..._",
                parse_mode="Markdown",
            )
        
        # Çalışma süresi bekle
        await asyncio.sleep(POMODORO_CALISMA_DK * 60)

        # Çalışmayı kaydet
        db.calisma_kaydet(ders, POMODORO_CALISMA_DK)

        # Mola bildirimi
        keyboard = [
            [
                InlineKeyboardButton("🔄 Tekrar Başlat", callback_data=f"pomo_{ders}"),
                InlineKeyboardButton("✅ Bitir", callback_data="pomo_bitti"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await context.bot.send_message(
            chat_id=user_id,
            text=f"✅ *{POMODORO_CALISMA_DK} dk {ders.upper()} tamamlandı!*\n\n"
                 f"☕ *{POMODORO_MOLA_DK} dakika mola zamanı!*\n"
                 f"Kalk, su iç, gözlerini dinlendir 👀\n\n"
                 f"📊 Bu seans otomatik kaydedildi.",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

    except asyncio.CancelledError:
        logger.info(f"Pomodoro iptal edildi: {user_id}")
    finally:
        aktif_pomodorolar.pop(user_id, None)


# ─── Görev listesi butonları ─────────────────────────────

async def gorevleri_goster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bugünkü görevleri butonlarla göster. /gorevler komutu."""
    gorevler = db.gunun_gorevleri()

    if not gorevler:
        keyboard = [
            [InlineKeyboardButton("➕ Görev Ekle", callback_data="gorev_ekle_sor")],
        ]
        await update.message.reply_text(
            "📋 *Bugünkü Görevler*\n\nHenüz görev eklenmemiş!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
        return

    mesaj = "📋 *Bugünkü Görevler:*\n\n"
    keyboard = []

    for g in gorevler:
        durum_emoji = {"tamamlandi": "✅", "ertelendi": "⏭️", "bekliyor": "⏳"}
        emoji = durum_emoji.get(g["durum"], "⏳")
        mesaj += f"{emoji} {g['gorev']}\n"

        if g["durum"] == "bekliyor":
            keyboard.append([
                InlineKeyboardButton(f"✅ {g['gorev'][:20]}", callback_data=f"gorev_tamam_{g['id']}"),
                InlineKeyboardButton(f"⏭️ Ertele", callback_data=f"gorev_ertele_{g['id']}"),
            ])

    keyboard.append([InlineKeyboardButton("➕ Görev Ekle", callback_data="gorev_ekle_sor")])

    await update.message.reply_text(
        mesaj,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── Hızlı kilo girişi butonları ─────────────────────────

async def hizli_kilo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hızlı kilo girişi butonları göster. /tartil komutu."""
    son = db.son_kilo()
    base = son["kilo"] if son else 80.0

    # Base değer etrafında butonlar oluştur
    values = [base - 0.5, base - 0.3, base, base + 0.3, base + 0.5]

    keyboard = [
        [InlineKeyboardButton(f"{v:.1f} kg", callback_data=f"kilo_{v:.1f}") for v in values[:3]],
        [InlineKeyboardButton(f"{v:.1f} kg", callback_data=f"kilo_{v:.1f}") for v in values[3:]],
    ]

    mesaj = "⚖️ *Hızlı Kilo Girişi*\n\n"
    if son:
        mesaj += f"Son kayıt: *{son['kilo']} kg* ({son['tarih']})\n"
    mesaj += "Bugünkü kilonu seç veya /kilo <değer> ile gir:"

    await update.message.reply_text(
        mesaj,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


# ─── Callback Query Handler ─────────────────────────────

async def buton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tüm inline buton callback'lerini işle."""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ── Pomodoro ──
    if data.startswith("pomo_"):
        ders = data.replace("pomo_", "")

        if ders == "iptal":
            # Aktif pomodoro varsa iptal et
            task = aktif_pomodorolar.pop(user_id, None)
            if task:
                task.cancel()
            await query.edit_message_text("❌ Pomodoro iptal edildi.")
            return

        if ders == "bitti":
            await query.edit_message_text("✅ Pomodoro oturumu tamamlandı! Aferin! 🎉")
            return

        # Zaten aktif pomodoro var mı?
        if user_id in aktif_pomodorolar:
            await query.answer("⚠️ Zaten aktif bir pomodoro var!", show_alert=True)
            return

        # Yeni pomodoro başlat
        task = asyncio.create_task(_pomodoro_timer(query, context, ders, user_id))
        aktif_pomodorolar[user_id] = task

    # ── Görev tamamla ──
    elif data.startswith("gorev_tamam_"):
        gorev_id = int(data.replace("gorev_tamam_", ""))
        basarili = db.gorev_tamamla(gorev_id)
        if basarili:
            await query.edit_message_text("✅ Görev tamamlandı! Harika! 💪")
        else:
            await query.edit_message_text("❌ Görev bulunamadı.")

    # ── Görev ertele ──
    elif data.startswith("gorev_ertele_"):
        gorev_id = int(data.replace("gorev_ertele_", ""))
        basarili = db.gorev_ertele(gorev_id)
        if basarili:
            await query.edit_message_text("⏭️ Görev ertelendi.")
        else:
            await query.edit_message_text("❌ Görev bulunamadı.")

    # ── Görev ekle (soru sor) ──
    elif data == "gorev_ekle_sor":
        await query.edit_message_text(
            "📝 Yeni görev eklemek için şunu yaz:\n\n"
            "`/gorev_ekle <görev açıklaması>`\n\n"
            "Örnek: /gorev_ekle SAT matematik pratik",
            parse_mode="Markdown",
        )

    # ── Hızlı kilo girişi ──
    elif data.startswith("kilo_"):
        kilo_val = float(data.replace("kilo_", ""))
        sonuc = db.kilo_kaydet(kilo_val)
        hedef = HEDEFLER["kilo"]["hedef_kg"]
        fark = kilo_val - hedef

        if fark > 0:
            durum = f"Hedefe *{fark:.1f} kg* kaldı 📉"
        elif fark == 0:
            durum = "🎉 HEDEFE ULAŞTIN!"
        else:
            durum = f"Hedefin *{abs(fark):.1f} kg* altındasın 🎯"

        await query.edit_message_text(
            f"⚖️ *{kilo_val} kg kaydedildi!*\n\n{durum}",
            parse_mode="Markdown",
        )


# ─── /gorev_ekle komutu ─────────────────────────────────

async def gorev_ekle_komut(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yeni görev ekle."""
    if not context.args:
        await update.message.reply_text(
            "📝 Kullanım: /gorev\\_ekle <görev açıklaması>\n"
            "Örnek: /gorev\\_ekle SAT matematik pratik",
            parse_mode="Markdown",
        )
        return

    gorev_metni = " ".join(context.args)
    gorev_id = db.gorev_ekle(gorev_metni)

    await update.message.reply_text(
        f"✅ Görev eklendi!\n\n"
        f"📋 *{gorev_metni}*\n"
        f"🔢 ID: {gorev_id}\n\n"
        f"Görevlerini görmek için: /gorevler",
        parse_mode="Markdown",
    )
