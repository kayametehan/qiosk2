"""
Web Servisi - İnternet araması ve sayfa okuma
DuckDuckGo ile arama, httpx + BeautifulSoup ile sayfa içeriği çekme.
"""

import logging
import re

import httpx
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)

# httpx client ayarları
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
}


def web_ara(sorgu: str, max_sonuc: int = 8) -> str:
    """DuckDuckGo ile web araması yap."""
    try:
        with DDGS() as ddgs:
            sonuclar = list(ddgs.text(sorgu, region="tr-tr", max_results=max_sonuc))

        if not sonuclar:
            return "Arama sonucu bulunamadı."

        cikti = f"🔍 '{sorgu}' için {len(sonuclar)} sonuç:\n\n"
        for i, s in enumerate(sonuclar, 1):
            cikti += f"{i}. **{s.get('title', 'Başlıksız')}**\n"
            cikti += f"   🔗 {s.get('href', '')}\n"
            cikti += f"   {s.get('body', '')[:200]}\n\n"

        return cikti

    except Exception as e:
        logger.error(f"Web arama hatası: {e}")
        return f"Arama sırasında hata oluştu: {str(e)}"


def sayfa_oku(url: str, max_karakter: int = 8000) -> str:
    """Bir web sayfasının ana içeriğini oku ve temiz metin olarak döndür."""
    try:
        with httpx.Client(headers=_HEADERS, follow_redirects=True, timeout=15) as client:
            response = client.get(url)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        # Gereksiz elementleri kaldır
        for tag in soup(["script", "style", "nav", "footer", "header", "aside",
                         "iframe", "noscript", "svg", "form"]):
            tag.decompose()

        # Meta bilgilerini al
        title = soup.title.string.strip() if soup.title and soup.title.string else "Başlık yok"
        meta_desc = ""
        meta_tag = soup.find("meta", attrs={"name": "description"})
        if meta_tag:
            meta_desc = meta_tag.get("content", "")

        # Ana içeriği bul — article > main > body sıralamasıyla
        content_elem = (
            soup.find("article")
            or soup.find("main")
            or soup.find("div", class_=re.compile(r"content|article|post|entry", re.I))
            or soup.body
        )

        if not content_elem:
            return f"Sayfa içeriği çıkarılamadı: {url}"

        # Metin çıkar
        text = content_elem.get_text(separator="\n", strip=True)

        # Fazla boşlukları temizle
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r" {2,}", " ", text)

        # Uzunluk sınırı
        if len(text) > max_karakter:
            text = text[:max_karakter] + "\n\n[... içerik kesildi ...]"

        cikti = f"📄 **{title}**\n🔗 {url}\n"
        if meta_desc:
            cikti += f"📝 {meta_desc}\n"
        cikti += f"\n{text}"

        return cikti

    except httpx.HTTPStatusError as e:
        return f"Sayfa açılamadı (HTTP {e.response.status_code}): {url}"
    except httpx.ConnectError:
        return f"Bağlantı kurulamadı: {url}"
    except Exception as e:
        logger.error(f"Sayfa okuma hatası: {e}")
        return f"Sayfa okunurken hata: {str(e)[:200]}"


def haber_ara(sorgu: str, max_sonuc: int = 5) -> str:
    """DuckDuckGo ile haber araması yap."""
    try:
        with DDGS() as ddgs:
            sonuclar = list(ddgs.news(sorgu, region="tr-tr", max_results=max_sonuc))

        if not sonuclar:
            return "Haber bulunamadı."

        cikti = f"📰 '{sorgu}' haberleri:\n\n"
        for i, s in enumerate(sonuclar, 1):
            cikti += f"{i}. **{s.get('title', '')}**\n"
            cikti += f"   📅 {s.get('date', '')}\n"
            cikti += f"   🔗 {s.get('url', '')}\n"
            cikti += f"   {s.get('body', '')[:150]}\n\n"

        return cikti

    except Exception as e:
        logger.error(f"Haber arama hatası: {e}")
        return f"Haber aranırken hata: {str(e)}"
