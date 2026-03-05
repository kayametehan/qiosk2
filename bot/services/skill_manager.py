"""
Skill Manager — Dinamik skill oluşturma, yönetme ve çalıştırma.
Bot kendi kendine yeni yetenekler oluşturabilir ve kendi kodunu geliştirebilir.
"""

import importlib.util
import json
import logging
import os
import shutil
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Proje kök dizini
PROJE_KOKU = Path(__file__).parent.parent.parent.resolve()
SKILLS_DIZINI = PROJE_KOKU / "bot" / "skills"
YEDEK_DIZINI = PROJE_KOKU / ".yedekler"

# Yüklü skill'ler
_yuklu_skilller: dict = {}


# ─── Skill Yükleme ───────────────────────────────────────

def _skilleri_yukle() -> dict:
    """bot/skills/ dizinindeki tüm skill'leri yükle / yeniden yükle."""
    global _yuklu_skilller
    _yuklu_skilller.clear()

    SKILLS_DIZINI.mkdir(parents=True, exist_ok=True)

    for dosya in SKILLS_DIZINI.glob("*.py"):
        if dosya.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(dosya.stem, dosya)
            modul = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(modul)

            if hasattr(modul, "SKILL_META") and hasattr(modul, "calistir"):
                _yuklu_skilller[dosya.stem] = {
                    "meta": modul.SKILL_META,
                    "calistir": modul.calistir,
                    "dosya": str(dosya),
                }
                logger.info(f"✅ Skill yüklendi: {dosya.stem}")
            else:
                logger.warning(f"⚠️ {dosya.name} — SKILL_META veya calistir() eksik, atlanıyor.")
        except Exception as e:
            logger.error(f"❌ Skill yükleme hatası ({dosya.name}): {e}")

    return _yuklu_skilller


# İlk yükleme
_skilleri_yukle()


# ─── Skill CRUD ───────────────────────────────────────────

def skill_olustur(ad: str, aciklama: str, parametreler_json: str, fonksiyon_kodu: str) -> str:
    """
    Yeni bir skill oluştur ve kaydet.

    Args:
        ad: Skill adı (snake_case, ASCII)
        aciklama: Ne yaptığını açıklayan metin
        parametreler_json: OpenAI tool parameters schema (JSON string)
        fonksiyon_kodu: calistir(**kwargs) fonksiyonunun gövdesi
    """
    try:
        # İsim doğrulama
        if not ad.isidentifier():
            return f"❌ Geçersiz skill adı: '{ad}' — Python tanımlayıcı kurallarına uymalı (harf/alt çizgi ile başlamalı, boşluk yok)."

        korunan = {
            "web_ara", "sayfa_oku", "haber_ara", "dosya_indir", "dosya_oku",
            "dosya_yaz", "dosya_listele", "dosya_ara", "komut_calistir",
            "uygulama_ac", "sistem_bilgisi", "islem_listele", "islem_kapat",
            "ekran_goruntusu", "panoya_kopyala", "panodan_oku", "kilo_kaydet",
            "calisma_kaydet", "gorev_ekle", "gorevleri_listele", "kilo_gecmisi",
            "ozet_goster", "haftalik_ozet", "pomodoro_baslat", "skill_olustur",
            "skill_listele", "skill_sil", "kendi_kodunu_oku", "kendi_kodunu_duzenle",
        }
        if ad in korunan:
            return f"❌ '{ad}' korunan bir tool adı. Farklı bir isim kullan."

        # Parametreleri parse et
        try:
            parametreler = json.loads(parametreler_json)
        except json.JSONDecodeError as e:
            return f"❌ parametreler_json geçersiz JSON: {e}"

        # Fonksiyon kodunu hazırla — girinti düzelt
        kod_satirlari = fonksiyon_kodu.split("\n")
        girintili_kod = "\n".join(f"    {s}" for s in kod_satirlari)

        # Dosya içeriği oluştur
        icerik = textwrap.dedent(f'''\
"""
Skill: {ad}
Açıklama: {aciklama}
Oluşturulma: {datetime.now().strftime("%Y-%m-%d %H:%M")}
"""

SKILL_META = {{
    "ad": "{ad}",
    "aciklama": """{aciklama}""",
    "parametreler": {json.dumps(parametreler, ensure_ascii=False, indent=8)},
}}


def calistir(**kwargs):
{girintili_kod}
''')

        # Syntax kontrolü
        try:
            compile(icerik, f"{ad}.py", "exec")
        except SyntaxError as e:
            return (
                f"❌ Syntax hatası — skill kaydedilmedi:\n"
                f"  Satır {e.lineno}: {e.msg}\n"
                f"  {e.text.strip() if e.text else ''}\n\n"
                f"Fonksiyon kodunu düzeltip tekrar dene."
            )

        # Dosyayı kaydet
        SKILLS_DIZINI.mkdir(parents=True, exist_ok=True)
        dosya_yolu = SKILLS_DIZINI / f"{ad}.py"
        dosya_yolu.write_text(icerik, encoding="utf-8")

        # Yeniden yükle
        _skilleri_yukle()

        if ad in _yuklu_skilller:
            return (
                f"✅ Skill oluşturuldu ve yüklendi: **{ad}**\n"
                f"📝 {aciklama}\n"
                f"📁 {dosya_yolu}\n\n"
                f"Artık bu skill'i doğal dilde kullanabilirsin!"
            )
        else:
            return (
                f"⚠️ Skill dosyası oluşturuldu ama yüklenemedi.\n"
                f"📁 {dosya_yolu}\n"
                f"Dosyayı kontrol edip düzeltmeyi dene."
            )

    except Exception as e:
        return f"❌ Skill oluşturma hatası: {str(e)}"


def skill_listele() -> str:
    """Mevcut tüm özel skill'leri listele."""
    _skilleri_yukle()  # Güncel listeyi al

    if not _yuklu_skilller:
        return "📭 Henüz özel skill oluşturulmamış.\n\nYeni skill oluşturmak için bana açıkla, ben hallederim!"

    cikti = f"🧩 Özel Skill'ler ({len(_yuklu_skilller)} adet):\n\n"
    for ad, skill in _yuklu_skilller.items():
        meta = skill["meta"]
        cikti += f"  🔧 **{ad}**\n"
        cikti += f"     {meta.get('aciklama', 'Açıklama yok')}\n"

        # Parametreleri göster
        params = meta.get("parametreler", {}).get("properties", {})
        if params:
            param_list = ", ".join(params.keys())
            cikti += f"     Parametreler: {param_list}\n"

        cikti += "\n"

    return cikti


def skill_sil(ad: str) -> str:
    """Bir özel skill'i sil."""
    try:
        dosya = SKILLS_DIZINI / f"{ad}.py"
        if not dosya.exists():
            return f"❌ '{ad}' adında bir skill bulunamadı."

        # Yedek al
        YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        yedek = YEDEK_DIZINI / f"{ad}_{ts}.py.bak"
        shutil.copy2(dosya, yedek)

        dosya.unlink()
        _skilleri_yukle()

        return f"✅ Skill silindi: {ad}\n📦 Yedek: {yedek}"
    except Exception as e:
        return f"❌ Skill silme hatası: {str(e)}"


def skill_kodunu_oku(ad: str) -> str:
    """Bir skill'in kaynak kodunu oku."""
    dosya = SKILLS_DIZINI / f"{ad}.py"
    if not dosya.exists():
        return f"❌ '{ad}' adında bir skill bulunamadı."

    try:
        icerik = dosya.read_text(encoding="utf-8")
        return f"📄 Skill: {ad}\n\n```python\n{icerik}\n```"
    except Exception as e:
        return f"❌ Okuma hatası: {str(e)}"


# ─── Skill Çalıştırma ────────────────────────────────────

def skill_var_mi(ad: str) -> bool:
    """Skill mevcut mu kontrol et."""
    if ad not in _yuklu_skilller:
        _skilleri_yukle()
    return ad in _yuklu_skilller


def skill_calistir(ad: str, args: dict) -> str:
    """Bir skill'i çalıştır."""
    if not skill_var_mi(ad):
        return f"❌ '{ad}' skill'i bulunamadı."

    try:
        fonk = _yuklu_skilller[ad]["calistir"]
        sonuc = fonk(**args)
        return str(sonuc) if sonuc is not None else "✅ Tamamlandı (çıktı yok)."
    except Exception as e:
        return f"❌ Skill çalıştırma hatası ({ad}): {str(e)}"


# ─── Dinamik Tool Tanımları ───────────────────────────────

def skill_toollarini_getir() -> list:
    """Tüm özel skill'ler için AI tool tanımları üret."""
    _skilleri_yukle()
    tools = []

    for ad, skill in _yuklu_skilller.items():
        meta = skill["meta"]
        tool_def = {
            "type": "function",
            "function": {
                "name": ad,
                "description": meta.get("aciklama", f"Özel skill: {ad}"),
                "parameters": meta.get("parametreler", {"type": "object", "properties": {}}),
            },
        }
        tools.append(tool_def)

    return tools


# ─── Kendi Kodunu Okuma / Düzenleme ──────────────────────

def kendi_kodunu_oku(dosya_yolu: str) -> str:
    """
    Bot'un kendi kaynak kodunu oku.
    dosya_yolu proje köküne göre relative olmalı (ör: bot/services/ai_service.py)
    """
    try:
        tam_yol = PROJE_KOKU / dosya_yolu
        if not tam_yol.exists():
            return f"❌ Dosya bulunamadı: {dosya_yolu}"
        if not tam_yol.is_file():
            return f"❌ Bu bir dosya değil: {dosya_yolu}"

        # Güvenlik: proje dışına çıkmasın
        try:
            tam_yol.resolve().relative_to(PROJE_KOKU)
        except ValueError:
            return f"❌ Proje dışı dosyalara erişilemez: {dosya_yolu}"

        icerik = tam_yol.read_text(encoding="utf-8")

        if len(icerik) > 15000:
            icerik = icerik[:15000] + f"\n\n[... kesildi, toplam {len(icerik)} karakter ...]"

        return f"📄 {dosya_yolu}\n\n{icerik}"
    except Exception as e:
        return f"❌ Okuma hatası: {str(e)}"


def kendi_kodunu_duzenle(dosya_yolu: str, eski_metin: str, yeni_metin: str) -> str:
    """
    Bot'un kendi kaynak kodunu düzenle — metin bul/değiştir.
    Otomatik yedek alır ve syntax doğrulaması yapar.
    """
    try:
        tam_yol = PROJE_KOKU / dosya_yolu

        # Güvenlik kontrolleri
        if not tam_yol.exists():
            return f"❌ Dosya bulunamadı: {dosya_yolu}"

        try:
            tam_yol.resolve().relative_to(PROJE_KOKU)
        except ValueError:
            return f"❌ Proje dışı dosyalar düzenlenemez."

        # Kritik dosya koruması — silmeyi veya tamamen boşaltmayı engelle
        if not yeni_metin.strip() and len(eski_metin) > 500:
            return "⚠️ Bu kadar büyük bir bölümü silmek riskli. Daha küçük değişiklikler yap."

        # Dosyayı oku
        icerik = tam_yol.read_text(encoding="utf-8")

        # Eski metin var mı kontrol et
        if eski_metin not in icerik:
            # Benzer metin bul — hata mesajında yardımcı ol
            return (
                f"❌ Aranan metin dosyada bulunamadı: {dosya_yolu}\n\n"
                f"Aranan (ilk 200 karakter):\n{eski_metin[:200]}\n\n"
                f"İpucu: kendi_kodunu_oku ile dosyayı önce oku, sonra tam metni kopyala."
            )

        # Birden fazla eşleşme kontrolü
        eslesme_sayisi = icerik.count(eski_metin)
        if eslesme_sayisi > 1:
            return (
                f"⚠️ '{eski_metin[:80]}...' metni {eslesme_sayisi} kez bulundu.\n"
                f"Tek bir yeri hedeflemek için daha uzun/spesifik metin kullan."
            )

        # Yedek al
        YEDEK_DIZINI.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dosya_adi = tam_yol.name.replace(".", "_")
        yedek = YEDEK_DIZINI / f"{dosya_adi}_{ts}.bak"
        shutil.copy2(tam_yol, yedek)

        # Değişikliği uygula
        yeni_icerik = icerik.replace(eski_metin, yeni_metin, 1)

        # Python dosyası ise syntax kontrolü
        if tam_yol.suffix == ".py":
            try:
                compile(yeni_icerik, str(tam_yol), "exec")
            except SyntaxError as e:
                return (
                    f"❌ Syntax hatası — değişiklik uygulanmadı!\n"
                    f"  Satır {e.lineno}: {e.msg}\n"
                    f"  {e.text.strip() if e.text else ''}\n\n"
                    f"Yedek: {yedek}\n"
                    f"Kodu düzeltip tekrar dene."
                )

        # Kaydet
        tam_yol.write_text(yeni_icerik, encoding="utf-8")

        degisen_satirlar = abs(yeni_metin.count("\n") - eski_metin.count("\n"))

        return (
            f"✅ Kod düzenlendi: {dosya_yolu}\n"
            f"📦 Yedek: {yedek}\n"
            f"📝 {len(eski_metin)} → {len(yeni_metin)} karakter\n"
            f"⚠️ Değişiklikler bir sonraki yeniden başlatmada aktif olacak."
        )

    except Exception as e:
        return f"❌ Düzenleme hatası: {str(e)}"


def proje_yapisini_goster() -> str:
    """Proje dosya yapısını göster — bot'un kendi yapısını anlaması için."""
    cikti = f"📁 Proje Yapısı — {PROJE_KOKU}\n\n"

    for root, dirs, files in os.walk(PROJE_KOKU):
        # Gereksiz klasörleri atla
        dirs[:] = [d for d in dirs if d not in (
            ".git", "__pycache__", ".yedekler", "venv", ".venv", "node_modules"
        )]

        seviye = Path(root).relative_to(PROJE_KOKU)
        girinti = "  " * len(seviye.parts)

        if str(seviye) != ".":
            cikti += f"{girinti}📂 {seviye.name}/\n"

        for f in sorted(files):
            if f.startswith(".") and f not in (".env.example", ".gitignore"):
                continue
            cikti += f"{girinti}  📄 {f}\n"

    return cikti
