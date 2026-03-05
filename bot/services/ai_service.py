"""
AI Servis - Agent Loop ile Çok Adımlı Görev Çözücü
Kullanıcı bir şey istediğinde AI kendi başına tool'ları zincirleyerek çözer.
"""

import json
import logging
from datetime import date
from typing import Callable, Optional

from openai import OpenAI

from config import AI_BASE_URL, AI_MODEL, GITHUB_TOKEN, HEDEFLER, MAX_AGENT_STEPS, SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ─── Tool Tanımları (AI bunlardan seçer) ──────────────────

TOOLS = [
    # --- Web ---
    {
        "type": "function",
        "function": {
            "name": "web_ara",
            "description": "İnternette arama yap. Otel, restoran, ürün, bilgi, haber — her şeyi arayabilir. Türkçe veya İngilizce arama yapabilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sorgu": {"type": "string", "description": "Aranacak metin"},
                    "max_sonuc": {"type": "integer", "description": "Kaç sonuç (varsayılan 8)"},
                },
                "required": ["sorgu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sayfa_oku",
            "description": "Bir web sayfasının içeriğini oku. URL ver, sayfadaki metni, yorumları, fiyatları çeker. Arama sonuçlarındaki linkleri detaylı incelemek için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Okunacak sayfanın URL'si"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "haber_ara",
            "description": "Güncel haberlerde arama yap.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sorgu": {"type": "string", "description": "Haber arama sorgusu"},
                },
                "required": ["sorgu"],
            },
        },
    },
    # --- Dosya Sistemi ---
    {
        "type": "function",
        "function": {
            "name": "dosya_oku",
            "description": "Bilgisayardaki bir dosyanın içeriğini oku. Tam yol ver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yol": {"type": "string", "description": "Dosya yolu (ör: C:/Users/kullanici/belge.txt veya ~/Desktop/notlar.md)"},
                },
                "required": ["yol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_yaz",
            "description": "Bir dosyaya içerik yaz. Dosya yoksa oluşturur, varsa üzerine yazar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yol": {"type": "string", "description": "Dosya yolu"},
                    "icerik": {"type": "string", "description": "Yazılacak içerik"},
                },
                "required": ["yol", "icerik"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_listele",
            "description": "Bir klasörün içeriğini listele. Dosya ve alt klasörleri gösterir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yol": {"type": "string", "description": "Klasör yolu (varsayılan: mevcut dizin)"},
                    "detayli": {"type": "boolean", "description": "Dosya boyutlarını da göster"},
                },
                "required": ["yol"],
            },
        },
    },
    # --- Sistem ---
    {
        "type": "function",
        "function": {
            "name": "komut_calistir",
            "description": "Terminal/komut satırında bir komut çalıştır. Herhangi bir shell komutu çalıştırabilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "komut": {"type": "string", "description": "Çalıştırılacak komut"},
                    "cwd": {"type": "string", "description": "Çalışma dizini (isteğe bağlı)"},
                },
                "required": ["komut"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "uygulama_ac",
            "description": "Bir URL'yi tarayıcıda aç veya bir dosya/uygulamayı varsayılan programla aç.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hedef": {"type": "string", "description": "Açılacak URL, dosya yolu veya uygulama"},
                },
                "required": ["hedef"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sistem_bilgisi",
            "description": "Bilgisayarın CPU, RAM, disk kullanımını göster.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # --- Kişisel Takip ---
    {
        "type": "function",
        "function": {
            "name": "kilo_kaydet",
            "description": "Kullanıcının kilo değerini veritabanına kaydet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kilo": {"type": "number", "description": "Kilo (kg)"},
                },
                "required": ["kilo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calisma_kaydet",
            "description": "Ders çalışma süresini kaydet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ders": {"type": "string", "enum": ["sat", "cents"], "description": "Ders adı"},
                    "dakika": {"type": "integer", "description": "Çalışma süresi (dakika)"},
                },
                "required": ["ders", "dakika"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gorev_ekle",
            "description": "Yapılacaklar listesine görev ekle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gorev": {"type": "string", "description": "Görev açıklaması"},
                },
                "required": ["gorev"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gorevleri_listele",
            "description": "Bugünkü görevleri göster.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kilo_gecmisi",
            "description": "Kilo kayıt geçmişini ve trendini göster.",
            "parameters": {
                "type": "object",
                "properties": {
                    "gun": {"type": "integer", "description": "Kaç günlük (varsayılan 7)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ozet_goster",
            "description": "Günlük ilerleme özetini göster (kilo, çalışma, görevler, sınav geri sayımı).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "haftalik_ozet",
            "description": "Haftalık istatistikleri ve çalışma detaylarını göster.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pomodoro_baslat",
            "description": "Pomodoro çalışma zamanlayıcısı başlat (25dk çalış / 5dk mola).",
            "parameters": {
                "type": "object",
                "properties": {
                    "ders": {"type": "string", "enum": ["sat", "cents"], "description": "Hangi ders"},
                },
                "required": ["ders"],
            },
        },
    },
]


def _client() -> OpenAI:
    return OpenAI(base_url=AI_BASE_URL, api_key=GITHUB_TOKEN)


def _sistem_promptu() -> str:
    bugun = date.today()
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    cents_str = "CENT-S tamamlandı ✅" if cents_kalan < 0 else f"{cents_kalan} gün kaldı"
    sat_str = "SAT tamamlandı ✅" if sat_kalan < 0 else f"{sat_kalan} gün kaldı"

    return SYSTEM_PROMPT.format(
        tarih=bugun.strftime("%d %B %Y"),
        cents_kalan=cents_str,
        sat_kalan=sat_str,
    )


def agent_loop(
    mesaj: str,
    ek_context: str,
    tool_executor: Callable,
    progress_callback: Optional[Callable] = None,
) -> str:
    """
    Ana ajan döngüsü. AI tool çağırır → çalıştırılır → sonuç geri verilir → tekrar.
    Görev bitene kadar devam eder (max MAX_AGENT_STEPS adım).

    Args:
        mesaj: Kullanıcının mesajı
        ek_context: Mevcut durum bilgisi (kilo, çalışma vs.)
        tool_executor: Tool'ları çalıştıran fonksiyon (name, args) -> result
        progress_callback: Her adımda çağrılan bildirim fonksiyonu (opsiyonel)

    Returns:
        AI'ın son cevabı (kullanıcıya gösterilecek metin)
    """
    client = _client()

    messages = [
        {"role": "system", "content": _sistem_promptu()},
    ]

    if ek_context:
        messages.append({
            "role": "system",
            "content": f"Kullanıcının mevcut durumu:\n{ek_context}",
        })

    messages.append({"role": "user", "content": mesaj})

    for step in range(MAX_AGENT_STEPS):
        try:
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=messages,
                tools=TOOLS,
                tool_choice="auto",
                max_tokens=2000,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"AI çağrı hatası (adım {step}): {e}")
            return f"⚠️ AI ile iletişimde sorun oluştu: {str(e)[:150]}"

        choice = response.choices[0]

        # Tool çağrısı yok → görev tamamlandı, cevabı döndür
        if not choice.message.tool_calls:
            return choice.message.content or "🤔 Cevap oluşturulamadı."

        # Tool çağrıları var → hepsini çalıştır
        messages.append(choice.message)  # assistant mesajını ekle

        for tool_call in choice.message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            logger.info(f"🔧 Adım {step + 1}: {func_name}({func_args})")

            # İlerleme bildirimi
            if progress_callback:
                try:
                    progress_callback(step + 1, func_name, func_args)
                except Exception:
                    pass

            # Tool'u çalıştır
            try:
                result = tool_executor(func_name, func_args)
            except Exception as e:
                result = f"❌ Tool hatası ({func_name}): {str(e)}"
                logger.error(result)

            # Sonucu mesajlara ekle
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result)[:6000],  # Token limiti için kırp
            })

    # Max adıma ulaşıldı
    return "⚠️ Görev çok karmaşık, tüm adımları tamamlayamadım. Daha spesifik sorabilir misin?"


def basit_ai_cevap(prompt: str) -> str:
    """Basit AI cevabı — tool çağrısı olmadan, hatırlatmalar için."""
    try:
        client = _client()
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": _sistem_promptu()},
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Basit AI hatası: {e}")
        return f"⚠️ AI yanıt veremedi: {str(e)[:100]}"
