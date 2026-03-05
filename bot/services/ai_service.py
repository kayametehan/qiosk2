"""
AI Servisi - GitHub Models (GPT-4o-mini) entegrasyonu
"""

from datetime import date
from openai import OpenAI

from config import AI_BASE_URL, AI_MODEL, GITHUB_TOKEN, HEDEFLER, SYSTEM_PROMPT


def _client() -> OpenAI:
    """OpenAI client oluştur (GitHub Models endpoint)."""
    return OpenAI(
        base_url=AI_BASE_URL,
        api_key=GITHUB_TOKEN,
    )


def _sistem_promptu() -> str:
    """Güncel bilgilerle system prompt oluştur."""
    bugun = date.today()

    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    # Sınav geçtiyse bilgiyi güncelle
    if cents_kalan < 0:
        cents_str = "CENT-S sınavı tamamlandı ✅"
    else:
        cents_str = f"{cents_kalan} gün"

    if sat_kalan < 0:
        sat_str = "SAT sınavı tamamlandı ✅"
    else:
        sat_str = f"{sat_kalan} gün"

    return SYSTEM_PROMPT.format(
        tarih=bugun.strftime("%d %B %Y"),
        cents_kalan=cents_str,
        sat_kalan=sat_str,
    )


def ai_soru_sor(soru: str, ek_bilgi: str = "") -> str:
    """AI'a genel soru sor."""
    try:
        client = _client()
        messages = [
            {"role": "system", "content": _sistem_promptu()},
        ]

        if ek_bilgi:
            messages.append({"role": "system", "content": f"Ek bilgi:\n{ek_bilgi}"})

        messages.append({"role": "user", "content": soru})

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"⚠️ AI servisi şu an yanıt veremiyor: {str(e)}"


def gunluk_plan_olustur(kilo_bilgi: str = "", calisma_bilgi: str = "") -> str:
    """AI ile günlük plan oluştur."""
    bugun = date.today()
    gun_adi = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"][bugun.weekday()]

    prompt = f"""Bugün {gun_adi}, {bugun.strftime('%d %B %Y')}.

{kilo_bilgi}
{calisma_bilgi}

Benim için bugünün detaylı planını oluştur. Şunları içersin:

1. ⏰ Saatlik program (08:00-23:00 arası)
2. 📚 Ders çalışma blokları (hangi ders, kaç dakika, hangi konular)
3. 🍽️ Öğün planı (yumurtasız, protein tozlu tariflerle)
4. 🏋️ Egzersiz önerisi
5. 💪 Günün motivasyon sözü

Sınav yakınlığına göre ders dağılımını ayarla."""

    return ai_soru_sor(prompt)


def ogun_onerisi() -> str:
    """AI ile öğün önerisi al."""
    prompt = """Bana bugün için 3 öğünlük (kahvaltı, öğle, akşam) bir diyet menüsü öner.

Kurallar:
- ❌ Yumurta YOK
- ✅ Karamelli protein tozu kullanabilirsin
- 🎯 Yüksek protein, düşük kalori
- Her öğünün yaklaşık kalorisini belirt
- Kolay hazırlanan tarifler olsun
- Ara öğün olarak protein shake tarifi ver"""

    return ai_soru_sor(prompt)


def motivasyon_mesaji() -> str:
    """AI ile motivasyon mesajı oluştur."""
    bugun = date.today()
    cents_kalan = (HEDEFLER["cents"]["sinav_tarihi"] - bugun).days
    sat_kalan = (HEDEFLER["sat"]["sinav_tarihi"] - bugun).days

    prompt = f"""Kısa ve etkili bir sabah motivasyon mesajı yaz.

CENT-S sınavına {cents_kalan} gün, SAT sınavına {sat_kalan} gün kaldı.
Kilo hedefim 75 kg.

Mesaj enerjik, samimi ve Türkçe olsun. 3-4 cümleyi geçmesin. Emoji kullan."""

    return ai_soru_sor(prompt)


def calisma_tavsiyesi(ders: str, kalan_gun: int) -> str:
    """Belirli bir ders için çalışma tavsiyesi al."""
    prompt = f"""{ders.upper()} sınavına {kalan_gun} gün kaldı.

Bu sürede en verimli nasıl çalışabilirim?
- Hangi konulara öncelik vermeliyim?
- Günde kaç saat çalışmalıyım?
- Pratik mi yapmalıyım yoksa konu mu çalışmalıyım?

Kısa ve net bir plan ver."""

    return ai_soru_sor(prompt)


def gun_sonu_degerlendirme(calisma_ozet: str, kilo_bilgi: str, gorev_bilgi: str) -> str:
    """Gün sonu değerlendirmesi yap."""
    prompt = f"""Bugün şunları yaptım:

📚 Çalışma: {calisma_ozet}
⚖️ Kilo: {kilo_bilgi}
✅ Görevler: {gorev_bilgi}

Kısa bir gün sonu değerlendirmesi yap:
- Neleri iyi yaptım?
- Yarın neye dikkat etmeliyim?
- 1 motivasyon cümlesi ekle"""

    return ai_soru_sor(prompt)
