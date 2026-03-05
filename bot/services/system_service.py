"""
Sistem Servisi - Dosya işlemleri, terminal komutları, uygulama açma
Bilgisayara tam yerel erişim sağlar.
"""

import logging
import os
import platform
import subprocess
import webbrowser
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


def dosya_oku(yol: str) -> str:
    """Bir dosyanın içeriğini oku."""
    try:
        path = Path(yol).expanduser().resolve()

        if not path.exists():
            return f"❌ Dosya bulunamadı: {path}"
        if not path.is_file():
            return f"❌ Bu bir dosya değil: {path}"
        if path.stat().st_size > 1_000_000:  # 1MB limit
            return f"⚠️ Dosya çok büyük ({path.stat().st_size / 1024:.0f} KB). İlk 1MB okunuyor..."

        # Metin dosyası olarak okumayı dene
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            content = path.read_text(encoding="latin-1")

        if len(content) > 10000:
            content = content[:10000] + "\n\n[... dosya kesildi, toplam karakter: " + str(len(content)) + " ...]"

        return f"📄 {path}\n\n{content}"

    except PermissionError:
        return f"🔒 Erişim reddedildi: {yol}"
    except Exception as e:
        logger.error(f"Dosya okuma hatası: {e}")
        return f"❌ Dosya okunurken hata: {str(e)}"


def dosya_yaz(yol: str, icerik: str) -> str:
    """Bir dosyaya içerik yaz (üzerine yazar)."""
    try:
        path = Path(yol).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(icerik, encoding="utf-8")
        return f"✅ Dosya yazıldı: {path} ({len(icerik)} karakter)"

    except PermissionError:
        return f"🔒 Yazma izni yok: {yol}"
    except Exception as e:
        logger.error(f"Dosya yazma hatası: {e}")
        return f"❌ Dosya yazılırken hata: {str(e)}"


def dosya_listele(yol: str = ".", detayli: bool = False) -> str:
    """Bir klasörün içeriğini listele."""
    try:
        path = Path(yol).expanduser().resolve()

        if not path.exists():
            return f"❌ Klasör bulunamadı: {path}"
        if not path.is_dir():
            return f"❌ Bu bir klasör değil: {path}"

        items = sorted(path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
        if not items:
            return f"📁 {path} — boş klasör"

        cikti = f"📁 {path}\n\n"
        for item in items[:100]:  # Max 100 öğe
            if item.name.startswith("."):
                continue  # Gizli dosyaları atla

            if item.is_dir():
                cikti += f"  📂 {item.name}/\n"
            else:
                if detayli:
                    boyut = item.stat().st_size
                    if boyut < 1024:
                        boyut_str = f"{boyut} B"
                    elif boyut < 1024 * 1024:
                        boyut_str = f"{boyut / 1024:.1f} KB"
                    else:
                        boyut_str = f"{boyut / (1024 * 1024):.1f} MB"
                    cikti += f"  📄 {item.name} ({boyut_str})\n"
                else:
                    cikti += f"  📄 {item.name}\n"

        if len(items) > 100:
            cikti += f"\n  ... ve {len(items) - 100} öğe daha"

        return cikti

    except PermissionError:
        return f"🔒 Erişim reddedildi: {yol}"
    except Exception as e:
        logger.error(f"Klasör listeleme hatası: {e}")
        return f"❌ Klasör listelenirken hata: {str(e)}"


def komut_calistir(komut: str, cwd: str = None, timeout: int = 30) -> str:
    """Terminal komutu çalıştır ve çıktısını döndür."""
    try:
        # Tehlikeli komut kontrolü (sadece uyarı, engelleme yok)
        tehlikeli = ["rm -rf /", "format", "del /s /q C:", ":(){", "mkfs"]
        for t in tehlikeli:
            if t in komut:
                return f"⚠️ Bu komut tehlikeli görünüyor: {komut}\nÇalıştırmak istediğinden emin misin?"

        # Platform'a göre shell seç
        is_windows = platform.system() == "Windows"

        result = subprocess.run(
            komut,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={**os.environ},
        )

        cikti = f"💻 Komut: {komut}\n"

        if result.stdout:
            stdout = result.stdout.strip()
            if len(stdout) > 5000:
                stdout = stdout[:5000] + "\n\n[... çıktı kesildi ...]"
            cikti += f"\n{stdout}\n"

        if result.stderr:
            stderr = result.stderr.strip()
            if len(stderr) > 2000:
                stderr = stderr[:2000] + "\n[... hata çıktısı kesildi ...]"
            cikti += f"\n⚠️ Stderr:\n{stderr}\n"

        if result.returncode != 0:
            cikti += f"\n❌ Çıkış kodu: {result.returncode}"
        else:
            cikti += f"\n✅ Başarılı"

        return cikti

    except subprocess.TimeoutExpired:
        return f"⏱️ Komut {timeout} saniyede tamamlanamadı: {komut}"
    except Exception as e:
        logger.error(f"Komut çalıştırma hatası: {e}")
        return f"❌ Komut çalıştırılırken hata: {str(e)}"


def uygulama_ac(hedef: str) -> str:
    """URL veya uygulamayı varsayılan programla aç."""
    try:
        if hedef.startswith(("http://", "https://", "www.")):
            webbrowser.open(hedef)
            return f"🌐 Tarayıcıda açıldı: {hedef}"

        # Platform'a göre dosya/uygulama aç
        sistem = platform.system()
        if sistem == "Windows":
            os.startfile(hedef)
        elif sistem == "Darwin":
            subprocess.Popen(["open", hedef])
        else:
            subprocess.Popen(["xdg-open", hedef])

        return f"✅ Açıldı: {hedef}"

    except Exception as e:
        logger.error(f"Uygulama açma hatası: {e}")
        return f"❌ Açılamadı: {str(e)}"


def sistem_bilgisi() -> str:
    """Sistem bilgilerini getir."""
    try:
        cpu_yuzde = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        cikti = "💻 Sistem Bilgileri:\n\n"
        cikti += f"  🖥️ İşletim Sistemi: {platform.system()} {platform.release()}\n"
        cikti += f"  🔧 İşlemci: {platform.processor() or 'Bilinmiyor'}\n"
        cikti += f"  ⚡ CPU Kullanımı: %{cpu_yuzde}\n"
        cikti += f"  🧠 RAM: {ram.used / (1024**3):.1f} / {ram.total / (1024**3):.1f} GB (%{ram.percent})\n"
        cikti += f"  💾 Disk: {disk.used / (1024**3):.1f} / {disk.total / (1024**3):.1f} GB (%{disk.percent})\n"

        return cikti

    except Exception as e:
        return f"❌ Sistem bilgisi alınamadı: {str(e)}"
