"""
AI Servisi — OpenAI SDK yok, doğrudan httpx ile GitHub Models API.
Tamamen açık kaynak bağımlılıklar.
"""

import json
import logging
from datetime import date
from typing import Callable, Optional

import httpx

from config import AI_API_URL, AI_MODEL, GITHUB_TOKEN, HEDEFLER, MAX_AGENT_STEPS, SYSTEM_PROMPT

logger = logging.getLogger(__name__)

# ─── Tool Tanımları ───────────────────────────────────────

TOOLS = [
    # --- Web ---
    {
        "type": "function",
        "function": {
            "name": "web_ara",
            "description": "İnternette arama yap. Otel, restoran, ürün, bilgi, haber — her şeyi ara.",
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
            "description": "Web sayfasının içeriğini oku. Yorumlar, fiyatlar, detaylar çekilir. Arama sonuçlarındaki linkleri incelemek için kullan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Okunacak URL"},
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
    {
        "type": "function",
        "function": {
            "name": "dosya_indir",
            "description": "İnternetten dosya indir (resim, PDF, vs). URL ve kayıt yolunu ver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "İndirilecek dosyanın URL'si"},
                    "kayit_yolu": {"type": "string", "description": "Kayıt edilecek dosya yolu"},
                },
                "required": ["url", "kayit_yolu"],
            },
        },
    },
    # --- Dosya Sistemi ---
    {
        "type": "function",
        "function": {
            "name": "dosya_oku",
            "description": "Bilgisayardaki bir dosyanın içeriğini oku.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yol": {"type": "string", "description": "Dosya yolu"},
                },
                "required": ["yol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_yaz",
            "description": "Bir dosyaya içerik yaz. Not tutmak, rapor kaydetmek için de kullan.",
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
            "description": "Klasör içeriğini listele.",
            "parameters": {
                "type": "object",
                "properties": {
                    "yol": {"type": "string", "description": "Klasör yolu"},
                    "detayli": {"type": "boolean", "description": "Boyut bilgisi göster"},
                },
                "required": ["yol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_ara",
            "description": "Bilgisayarda dosya ara. İsme göre veya içeriğe göre arayabilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "baslangic_yolu": {"type": "string", "description": "Aramaya başlanacak klasör"},
                    "desen": {"type": "string", "description": "Dosya adı deseni (ör: *.pdf, rapor*)"},
                    "icerik_ara": {"type": "string", "description": "Dosya içinde aranacak metin (opsiyonel)"},
                },
                "required": ["baslangic_yolu", "desen"],
            },
        },
    },
    # --- Sistem ---
    {
        "type": "function",
        "function": {
            "name": "komut_calistir",
            "description": "Terminal/shell komutu çalıştır. Her türlü sistem komutu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "komut": {"type": "string", "description": "Çalıştırılacak komut"},
                    "cwd": {"type": "string", "description": "Çalışma dizini (opsiyonel)"},
                },
                "required": ["komut"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "uygulama_ac",
            "description": "URL'yi tarayıcıda aç veya dosya/uygulamayı varsayılan programla aç.",
            "parameters": {
                "type": "object",
                "properties": {
                    "hedef": {"type": "string", "description": "URL, dosya yolu veya uygulama adı"},
                },
                "required": ["hedef"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sistem_bilgisi",
            "description": "CPU, RAM, disk kullanımı ve sistem bilgilerini göster.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "islem_listele",
            "description": "Çalışan işlemleri listele. İsme göre filtreleyebilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filtre": {"type": "string", "description": "İşlem adı filtresi (opsiyonel)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "islem_kapat",
            "description": "Çalışan bir işlemi (programı) kapat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "islem_adi": {"type": "string", "description": "Kapatılacak işlem adı"},
                },
                "required": ["islem_adi"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ekran_goruntusu",
            "description": "Ekran görüntüsü al ve kaydet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kayit_yolu": {"type": "string", "description": "Kayıt yolu (opsiyonel, varsayılan masaüstü)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "panoya_kopyala",
            "description": "Metni panoya (clipboard) kopyala.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metin": {"type": "string", "description": "Kopyalanacak metin"},
                },
                "required": ["metin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "panodan_oku",
            "description": "Panodaki (clipboard) metni oku.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # --- Kişisel Takip ---
    {
        "type": "function",
        "function": {
            "name": "kilo_kaydet",
            "description": "Kullanıcının kilo değerini kaydet.",
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
                    "dakika": {"type": "integer", "description": "Süre (dakika)"},
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
            "description": "Kilo kayıt geçmişini ve trendi göster.",
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
            "description": "Günlük ilerleme özeti (kilo, çalışma, görevler, geri sayım).",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "haftalik_ozet",
            "description": "Haftalık çalışma ve kilo istatistikleri.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "pomodoro_baslat",
            "description": "Pomodoro çalışma zamanlayıcısı başlat.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ders": {"type": "string", "enum": ["sat", "cents"], "description": "Ders"},
                },
                "required": ["ders"],
            },
        },
    },
    # --- Skill Yönetimi & Kendini Geliştirme ---
    {
        "type": "function",
        "function": {
            "name": "skill_olustur",
            "description": "Kendine yeni bir yetenek/skill oluştur. Python fonksiyonu olarak kaydedilir ve hemen kullanılabilir hale gelir. Eksik bir yeteneğin olduğunu fark edersen kendi kendine yeni skill oluşturabilirsin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ad": {"type": "string", "description": "Skill adı (snake_case, ASCII, Türkçe karakter yok)"},
                    "aciklama": {"type": "string", "description": "Skill'in ne yaptığının açıklaması"},
                    "parametreler_json": {"type": "string", "description": "OpenAI function parameters JSON schema string. Örnek: {\"type\":\"object\",\"properties\":{\"x\":{\"type\":\"string\"}},\"required\":[\"x\"]}"},
                    "fonksiyon_kodu": {"type": "string", "description": "calistir(**kwargs) fonksiyonunun gövdesi (def satırı OLMADAN). kwargs.get() ile parametrelere eriş. String döndürmeli."},
                },
                "required": ["ad", "aciklama", "parametreler_json", "fonksiyon_kodu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_listele",
            "description": "Oluşturulmuş tüm özel skill'leri listele.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "skill_sil",
            "description": "Bir özel skill'i sil.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ad": {"type": "string", "description": "Silinecek skill adı"},
                },
                "required": ["ad"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kendi_kodunu_oku",
            "description": "Kendi kaynak kodunu oku. Bot'un kendi dosyalarını incelemek, anlamak ve geliştirmek için kullan. Proje köküne göre relative yol ver.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dosya_yolu": {"type": "string", "description": "Proje köküne göre dosya yolu (ör: bot/services/ai_service.py, config.py, main.py)"},
                },
                "required": ["dosya_yolu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kendi_kodunu_duzenle",
            "description": "Kendi kaynak kodunu düzenle. Metin bul-değiştir yöntemi ile çalışır. Otomatik yedek alınır ve syntax kontrolü yapılır. Önce kendi_kodunu_oku ile dosyayı oku, sonra düzenle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dosya_yolu": {"type": "string", "description": "Proje köküne göre dosya yolu"},
                    "eski_metin": {"type": "string", "description": "Değiştirilecek mevcut metin (dosyadaki ile BİREBİR aynı olmalı)"},
                    "yeni_metin": {"type": "string", "description": "Yerine konacak yeni metin"},
                },
                "required": ["dosya_yolu", "eski_metin", "yeni_metin"],
            },
        },
    },
]


# ─── GitHub Models API — ham httpx ────────────────────────

def _api_cagri(messages: list, tools: list = None) -> dict:
    """GitHub Models API'ye doğrudan HTTP isteği at. OpenAI SDK yok."""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": AI_MODEL,
        "messages": messages,
        "max_tokens": 2000,
        "temperature": 0.7,
    }

    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    with httpx.Client(timeout=60) as client:
        response = client.post(AI_API_URL, headers=headers, json=payload)
        response.raise_for_status()

    return response.json()


def _sistem_promptu() -> str:
    bugun = date.today()
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    cents_str = "tamamlandı ✅" if cents_kalan < 0 else f"{cents_kalan} gün kaldı"
    sat_str = "tamamlandı ✅" if sat_kalan < 0 else f"{sat_kalan} gün kaldı"

    return SYSTEM_PROMPT.format(
        tarih=bugun.strftime("%d %B %Y"),
        cents_kalan=cents_str,
        sat_kalan=sat_str,
    )


# ─── Agent Loop ───────────────────────────────────────────

def agent_loop(
    mesaj: str,
    ek_context: str,
    tool_executor: Callable,
    progress_callback: Optional[Callable] = None,
) -> str:
    """
    Ana ajan döngüsü — tool çağır, sonucu al, tekrar, görev bitene kadar.
    OpenAI SDK yok, ham HTTP.
    """
    messages = [{"role": "system", "content": _sistem_promptu()}]

    if ek_context:
        messages.append({"role": "system", "content": f"Kullanıcının mevcut durumu:\n{ek_context}"})

    messages.append({"role": "user", "content": mesaj})

    # Dinamik skill tool'larını statik TOOLS ile birleştir
    from bot.services.skill_manager import skill_toollarini_getir
    tum_toollar = TOOLS + skill_toollarini_getir()

    for step in range(MAX_AGENT_STEPS):
        try:
            data = _api_cagri(messages, tum_toollar)
        except httpx.HTTPStatusError as e:
            logger.error(f"API HTTP hatası (adım {step}): {e.response.status_code} {e.response.text[:300]}")
            return f"⚠️ AI servisi hata verdi (HTTP {e.response.status_code}). Biraz sonra tekrar dene."
        except Exception as e:
            logger.error(f"API hatası (adım {step}): {e}")
            return f"⚠️ AI ile iletişimde sorun: {str(e)[:150]}"

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls")

        # Tool çağrısı yok → görev bitti, cevabı döndür
        if not tool_calls:
            return message.get("content") or "🤔 Cevap oluşturulamadı."

        # Assistant mesajını history'ye ekle
        messages.append(message)

        # Her tool çağrısını çalıştır
        for tc in tool_calls:
            func_name = tc["function"]["name"]
            try:
                func_args = json.loads(tc["function"]["arguments"])
            except (json.JSONDecodeError, KeyError):
                func_args = {}

            logger.info(f"🔧 Adım {step + 1}: {func_name}({func_args})")

            if progress_callback:
                try:
                    progress_callback(step + 1, func_name, func_args)
                except Exception:
                    pass

            # Tool'u çalıştır
            try:
                result = tool_executor(func_name, func_args)
            except Exception as e:
                result = f"❌ Hata ({func_name}): {str(e)}"
                logger.error(result)

            # Sonucu ekle
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": str(result)[:6000],
            })

    return "⚠️ Görev çok karmaşık, tamamlayamadım. Daha spesifik sorabilir misin?"


def basit_cevap(prompt: str) -> str:
    """Basit AI cevabı — hatırlatmalar için, tool yok."""
    try:
        data = _api_cagri([
            {"role": "system", "content": _sistem_promptu()},
            {"role": "user", "content": prompt},
        ])
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Basit cevap hatası: {e}")
        return f"⚠️ AI yanıt veremedi: {str(e)[:100]}"
