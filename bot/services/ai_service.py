"""
AI Servisi — Async httpx ile GitHub Models API.
Konuşma hafızası, dinamik skill'ler, 30+ tool.
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
            "description": "Web sayfasının içeriğini oku. Yorumlar, fiyatlar, detaylar çekilir.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Okunacak URL"}},
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
                "properties": {"sorgu": {"type": "string", "description": "Haber arama sorgusu"}},
                "required": ["sorgu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_indir",
            "description": "İnternetten dosya indir (resim, PDF, vs).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "İndirilecek dosyanın URL'si"},
                    "kayit_yolu": {"type": "string", "description": "Kayıt yolu (opsiyonel)"},
                },
                "required": ["url"],
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
                "properties": {"yol": {"type": "string", "description": "Dosya yolu"}},
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
            "description": "Bilgisayarda dosya ara. İsme veya içeriğe göre.",
            "parameters": {
                "type": "object",
                "properties": {
                    "baslangic_yolu": {"type": "string", "description": "Aramaya başlanacak klasör"},
                    "desen": {"type": "string", "description": "Dosya adı deseni (ör: *.pdf, rapor*)"},
                    "icerik_ara": {"type": "string", "description": "İçerik araması (opsiyonel)"},
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
            "description": "Terminal/shell komutu çalıştır.",
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
            "description": "URL'yi tarayıcıda aç veya dosya/uygulamayı aç.",
            "parameters": {
                "type": "object",
                "properties": {"hedef": {"type": "string", "description": "URL, dosya veya uygulama"}},
                "required": ["hedef"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sistem_bilgisi",
            "description": "CPU, RAM, disk ve sistem bilgilerini göster.",
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
                "properties": {"filtre": {"type": "string", "description": "İşlem adı filtresi"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "islem_kapat",
            "description": "Çalışan bir işlemi kapat.",
            "parameters": {
                "type": "object",
                "properties": {"islem_adi": {"type": "string", "description": "İşlem adı"}},
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
                "properties": {"kayit_yolu": {"type": "string", "description": "Kayıt yolu (opsiyonel)"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "panoya_kopyala",
            "description": "Metni panoya kopyala.",
            "parameters": {
                "type": "object",
                "properties": {"metin": {"type": "string", "description": "Kopyalanacak metin"}},
                "required": ["metin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "panodan_oku",
            "description": "Panodaki metni oku.",
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
                "properties": {"kilo": {"type": "number", "description": "Kilo (kg)"}},
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
                    "ders": {"type": "string", "enum": ["sat", "cents"], "description": "Ders"},
                    "dakika": {"type": "integer", "description": "Süre (dakika)"},
                },
                "required": ["ders", "dakika"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ogun_kaydet",
            "description": "Yemek/öğün kaydı ekle. Kullanıcı ne yediğini söylediğinde kullan. Kaloriyi sen tahmin et.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ogun_tipi": {"type": "string", "enum": ["kahvalti", "ogle", "aksam", "ara_ogun"],
                                  "description": "Öğün tipi"},
                    "icerik": {"type": "string", "description": "Ne yenildiği"},
                    "kalori": {"type": "integer", "description": "Tahmini kalori (kcal)"},
                },
                "required": ["ogun_tipi", "icerik", "kalori"],
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
                "properties": {"gorev": {"type": "string", "description": "Görev açıklaması"}},
                "required": ["gorev"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gorev_tamamla",
            "description": "Görevi tamamlandı olarak işaretle.",
            "parameters": {
                "type": "object",
                "properties": {"gorev_id": {"type": "integer", "description": "Görev ID'si"}},
                "required": ["gorev_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gorev_ertele",
            "description": "Görevi ertele.",
            "parameters": {
                "type": "object",
                "properties": {"gorev_id": {"type": "integer", "description": "Görev ID'si"}},
                "required": ["gorev_id"],
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
                "properties": {"gun": {"type": "integer", "description": "Kaç gün (varsayılan 7)"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deneme_kaydet",
            "description": "Deneme sınavı sonucunu kaydet (SAT, CENT-S). Bölüm ve puan bilgisiyle.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sinav_turu": {"type": "string", "enum": ["sat", "cents"], "description": "Sınav türü"},
                    "puan": {"type": "integer", "description": "Alınan puan"},
                    "bolum": {"type": "string", "description": "Bölüm (math, reading, writing vb.)"},
                    "toplam": {"type": "integer", "description": "Toplam puan (ör: 800)"},
                    "notlar": {"type": "string", "description": "Ek notlar"},
                },
                "required": ["sinav_turu", "puan"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deneme_gecmisi",
            "description": "Deneme sınavı sonuç geçmişini göster. Trend analizi için.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sinav_turu": {"type": "string", "enum": ["sat", "cents"],
                                   "description": "Sınav türü (opsiyonel, hepsini görmek için boş bırak)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ozet_goster",
            "description": "Günlük ilerleme özeti (kilo, çalışma, görevler, kalori, geri sayım).",
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
                "properties": {"ders": {"type": "string", "enum": ["sat", "cents"], "description": "Ders"}},
                "required": ["ders"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "sohbet_temizle",
            "description": "Konuşma geçmişini sıfırla. Hafızayı temizle.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    # --- Skill Yönetimi & Kendini Geliştirme ---
    {
        "type": "function",
        "function": {
            "name": "skill_olustur",
            "description": "Kendine yeni bir yetenek oluştur. Python fonksiyonu olarak kaydedilir ve anında kullanılabilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "ad": {"type": "string", "description": "Skill adı (snake_case, ASCII)"},
                    "aciklama": {"type": "string", "description": "Açıklama"},
                    "parametreler_json": {"type": "string", "description": "OpenAI function parameters JSON schema string"},
                    "fonksiyon_kodu": {"type": "string", "description": "calistir(**kwargs) gövdesi (def satırı OLMADAN). kwargs.get() ile parametrelere eriş."},
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
                "properties": {"ad": {"type": "string", "description": "Silinecek skill adı"}},
                "required": ["ad"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kendi_kodunu_oku",
            "description": "Kendi kaynak kodunu oku. Proje köküne göre relative yol ver.",
            "parameters": {
                "type": "object",
                "properties": {"dosya_yolu": {"type": "string", "description": "Dosya yolu (ör: bot/services/ai_service.py)"}},
                "required": ["dosya_yolu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "kendi_kodunu_duzenle",
            "description": "Kendi kaynak kodunu düzenle (bul-değiştir). Yedek alınır, syntax kontrol edilir.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dosya_yolu": {"type": "string", "description": "Dosya yolu"},
                    "eski_metin": {"type": "string", "description": "Değiştirilecek metin (BİREBİR eşleşmeli)"},
                    "yeni_metin": {"type": "string", "description": "Yerine konacak metin"},
                },
                "required": ["dosya_yolu", "eski_metin", "yeni_metin"],
            },
        },
    },
]


# ─── GitHub Models API — async httpx ─────────────────────

async def _api_cagri(messages: list, tools: list = None) -> dict:
    """GitHub Models API'ye async HTTP isteği at."""
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

    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(AI_API_URL, headers=headers, json=payload)
        response.raise_for_status()
    return response.json()


def _sistem_promptu() -> str:
    from bot.database import profil_tumu

    bugun = date.today()
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    cents_str = "tamamlandı ✅" if cents_kalan < 0 else f"{cents_kalan} gün kaldı"
    sat_str = "tamamlandı ✅" if sat_kalan < 0 else f"{sat_kalan} gün kaldı"

    # Profil bilgisi
    profil = profil_tumu()
    profil_satirlari = []
    etiketler = {"isim": "İsim", "yas": "Yaş", "meslek": "Meslek",
                 "ilgi_alanlari": "İlgi Alanları", "gunluk_rutin": "Günlük Rutin"}
    for key, label in etiketler.items():
        if key in profil:
            profil_satirlari.append(f"- {label}: {profil[key]}")
    profil_bilgisi = "\n".join(profil_satirlari) if profil_satirlari else "Henüz tanışma yapılmadı"

    return SYSTEM_PROMPT.format(
        tarih=bugun.strftime("%d %B %Y"),
        cents_kalan=cents_str,
        sat_kalan=sat_str,
        profil_bilgisi=profil_bilgisi,
    )


# ─── Agent Loop (async + konuşma hafızası) ────────────────

async def agent_loop(
    mesaj: str,
    ek_context: str,
    tool_executor: Callable,
    progress_callback: Optional[Callable] = None,
) -> str:
    """
    Ana ajan döngüsü — async, konuşma hafızalı.
    """
    from bot.database import sohbet_gecmisi_getir, sohbet_kaydet
    from bot.services.skill_manager import skill_toollarini_getir

    messages = [{"role": "system", "content": _sistem_promptu()}]

    if ek_context:
        messages.append({"role": "system", "content": f"Kullanıcının mevcut durumu:\n{ek_context}"})

    # Konuşma hafızasını yükle (son 30 mesaj)
    gecmis = sohbet_gecmisi_getir(30)
    if gecmis:
        messages.extend(gecmis)

    messages.append({"role": "user", "content": mesaj})

    # Kullanıcı mesajını kaydet
    sohbet_kaydet("user", mesaj)

    # Dinamik skill tool'larını birleştir
    tum_toollar = TOOLS + skill_toollarini_getir()

    for step in range(MAX_AGENT_STEPS):
        try:
            data = await _api_cagri(messages, tum_toollar)
        except httpx.HTTPStatusError as e:
            logger.error(f"API HTTP hatası (adım {step}): {e.response.status_code} {e.response.text[:300]}")
            return f"⚠️ AI servisi hata verdi (HTTP {e.response.status_code}). Biraz sonra tekrar dene."
        except Exception as e:
            logger.error(f"API hatası (adım {step}): {e}")
            return f"⚠️ AI ile iletişimde sorun: {str(e)[:150]}"

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        tool_calls = message.get("tool_calls")

        # Tool çağrısı yok → görev bitti
        if not tool_calls:
            cevap = message.get("content") or "🤔 Cevap oluşturulamadı."
            # AI cevabını hafızaya kaydet
            sohbet_kaydet("assistant", cevap)
            return cevap

        # Assistant mesajını history'ye ekle
        messages.append(message)

        # Tool calls'u hafızaya kaydet
        tc_json = json.dumps([{
            "id": tc["id"], "type": "function",
            "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}
        } for tc in tool_calls])
        sohbet_kaydet("assistant", message.get("content"), tool_calls_json=tc_json)

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
                    await progress_callback(step + 1, func_name, func_args)
                except Exception:
                    pass

            # Tool'u çalıştır
            try:
                result = tool_executor(func_name, func_args)
            except Exception as e:
                result = f"❌ Hata ({func_name}): {str(e)}"
                logger.error(result)

            result_str = str(result)[:6000]

            # Tool sonucunu hafızaya kaydet
            sohbet_kaydet("tool", result_str, tool_call_id=tc["id"])

            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": result_str,
            })

    return "⚠️ Görev çok karmaşık, tamamlayamadım. Daha spesifik sorabilir misin?"


async def basit_cevap(prompt: str) -> str:
    """Basit AI cevabı — hatırlatmalar için, tool yok."""
    try:
        data = await _api_cagri([
            {"role": "system", "content": _sistem_promptu()},
            {"role": "user", "content": prompt},
        ])
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"Basit cevap hatası: {e}")
        return f"⚠️ AI yanıt veremedi: {str(e)[:100]}"
