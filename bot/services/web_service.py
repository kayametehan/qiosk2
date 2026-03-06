"""
Web Servisi — DuckDuckGo arama, sayfa okuma, haber arama, dosya indirme.
Tüm bağımlılıklar açık kaynak: duckduckgo-search, beautifulsoup4, httpx.
Rate limit koruması ile retry mekanizması.
"""

import logging
import time
from pathlib import Path
from datetime import datetime

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}

# Rate limit koruması
_son_arama_zamani = 0.0
_MIN_ARAMA_ARASI = 2.0  # saniye


def _rate_limit_bekle():
    """Rate limit koruması — aramalar arası minimum süre."""
    global _son_arama_zamani
    simdi = time.time()
    gecen = simdi - _son_arama_zamani
    if gecen < _MIN_ARAMA_ARASI:
        time.sleep(_MIN_ARAMA_ARASI - gecen)
    _son_arama_zamani = time.time()


# ─── Web Arama ────────────────────────────────────────────

def web_ara(sorgu: str, max_sonuc: int = 8) -> str:
    """DuckDuckGo ile web araması yap. Rate limit koruması ve retry mekanizması."""
    son_hata = None

    for deneme in range(3):
        try:
            _rate_limit_bekle()

            with DDGS() as ddgs:
                sonuclar = list(ddgs.text(sorgu, region="tr-tr", max_results=max_sonuc))

            if not sonuclar:
                return f"🔍 '{sorgu}' için sonuç bulunamadı."

            cikti = f"🔍 '{sorgu}' arama sonuçları:\n\n"
            for i, s in enumerate(sonuclar, 1):
                cikti += f"{i}. **{s.get('title', 'Başlıksız')}**\n"
                cikti += f"   {s.get('href', '')}\n"
                body = s.get("body", "")
                if body:
                    cikti += f"   {body[:200]}\n"
                cikti += "\n"

            return cikti

        except Exception as e:
            son_hata = e
            hata_str = str(e).lower()
            if "ratelimit" in hata_str or "202" in hata_str:
                bekleme = (deneme + 1) * 3  # 3s, 6s, 9s
                logger.warning(f"Rate limit, {bekleme}s bekleniyor... (deneme {deneme + 1}/3)")
                time.sleep(bekleme)
                continue
            else:
                logger.error(f"Web arama hatası: {e}")
                return f"❌ Arama hatası: {str(e)}"

    logger.error(f"Web arama başarısız (3 deneme): {son_hata}")
    return f"❌ Arama başarısız (rate limit). Biraz sonra tekrar dene."


def haber_ara(sorgu: str, max_sonuc: int = 6) -> str:
    """DuckDuckGo ile haber araması yap. Retry mekanizmalı."""
    son_hata = None

    for deneme in range(3):
        try:
            _rate_limit_bekle()

            with DDGS() as ddgs:
                sonuclar = list(ddgs.news(sorgu, region="tr-tr", max_results=max_sonuc))

            if not sonuclar:
                return f"📰 '{sorgu}' ile ilgili haber bulunamadı."

            cikti = f"📰 '{sorgu}' haberleri:\n\n"
            for i, s in enumerate(sonuclar, 1):
                cikti += f"{i}. **{s.get('title', 'Başlıksız')}**\n"
                cikti += f"   📅 {s.get('date', 'Tarih yok')}\n"
                cikti += f"   🔗 {s.get('url', '')}\n"
                body = s.get("body", "")
                if body:
                    cikti += f"   {body[:180]}\n"
                cikti += "\n"

            return cikti

        except Exception as e:
            son_hata = e
            if "ratelimit" in str(e).lower() or "202" in str(e):
                bekleme = (deneme + 1) * 3
                logger.warning(f"Haber rate limit, {bekleme}s bekleniyor...")
                time.sleep(bekleme)
                continue
            else:
                logger.error(f"Haber arama hatası: {e}")
                return f"❌ Haber arama hatası: {str(e)}"

    return f"❌ Haber araması başarısız (rate limit). Biraz sonra tekrar dene."


# ─── Sayfa Oku ────────────────────────────────────────────

def sayfa_oku(url: str) -> str:
    """Web sayfasını oku ve ana içeriği çıkar."""
    try:
        with httpx.Client(
            headers=HEADERS, timeout=20, follow_redirects=True, verify=False
        ) as client:
            response = client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Gereksiz etiketleri sil
        for tag in soup(["script", "style", "nav", "footer", "header",
                         "aside", "iframe", "noscript", "form", "button"]):
            tag.decompose()

        # Başlık
        baslik = ""
        title_tag = soup.find("title")
        if title_tag:
            baslik = title_tag.get_text(strip=True)

        # Meta açıklama
        aciklama = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta:
            aciklama = meta.get("content", "")

        # Ana içerik — article > main > body
        icerik_element = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_="content")
            or soup.find("div", id="content")
            or soup.body
        )

        if icerik_element:
            metin = icerik_element.get_text(separator="\n", strip=True)
        else:
            metin = soup.get_text(separator="\n", strip=True)

        # Boş satırları temizle
        satirlar = [s.strip() for s in metin.split("\n") if s.strip()]
        metin = "\n".join(satirlar)

        # Kısalt
        if len(metin) > 8000:
            metin = metin[:8000] + "\n\n[... kesildi ...]"

        cikti = f"🌐 {url}\n"
        if baslik:
            cikti += f"📌 {baslik}\n"
        if aciklama:
            cikti += f"📝 {aciklama}\n"
        cikti += f"\n{metin}"

        return cikti
    except httpx.HTTPStatusError as e:
        return f"❌ HTTP hatası ({e.response.status_code}): {url}"
    except Exception as e:
        logger.error(f"Sayfa okuma hatası: {e}")
        return f"❌ Sayfa okunamadı: {str(e)}"


# ─── Dosya İndir ──────────────────────────────────────────

def dosya_indir(url: str, kayit_yolu: str = None) -> str:
    """URL'den dosya indir."""
    try:
        if not kayit_yolu:
            # URL'den dosya adını çıkar
            from urllib.parse import urlparse, unquote
            parsed = urlparse(url)
            dosya_adi = unquote(parsed.path.split("/")[-1]) or "indirilen_dosya"
            indirilenler = Path.home() / "Downloads"
            indirilenler.mkdir(parents=True, exist_ok=True)
            kayit_yolu = str(indirilenler / dosya_adi)

        kayit = Path(kayit_yolu)
        kayit.parent.mkdir(parents=True, exist_ok=True)

        with httpx.Client(
            headers=HEADERS, timeout=120, follow_redirects=True, verify=False
        ) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                toplam = int(response.headers.get("content-length", 0))

                with open(kayit, "wb") as f:
                    indirilen = 0
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        indirilen += len(chunk)

        boyut = kayit.stat().st_size
        if boyut < 1024:
            b = f"{boyut} B"
        elif boyut < 1048576:
            b = f"{boyut/1024:.1f} KB"
        else:
            b = f"{boyut/1048576:.1f} MB"

        return f"✅ İndirildi: {kayit} ({b})"
    except httpx.HTTPStatusError as e:
        return f"❌ İndirme HTTP hatası ({e.response.status_code}): {url}"
    except Exception as e:
        logger.error(f"Dosya indirme hatası: {e}")
        return f"❌ İndirme hatası: {str(e)}"
