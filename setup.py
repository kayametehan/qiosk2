"""
Qiosk2 Kurulum Sihirbazı — Artık python main.py ile otomatik çalışıyor.
Bu dosyayı sadece ayarları sıfırlamak istersen kullan: python setup.py
"""

import sys
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"


def setup():
    """Token'ları sıfırla / yeniden yapılandır."""
    # main.py'deki fonksiyonu kullan
    from main import _env_yapılandir, _bagimliliklari_kur, _ffmpeg_kontrol
    _env_yapılandir()
    cevap = input("📦 Bağımlılıkları da yeniden kurayım mı? (e/h): ").strip().lower()
    if cevap == "e":
        _bagimliliklari_kur()
        _ffmpeg_kontrol()
    print("🚀 Botu başlatmak için: python main.py\n")


if __name__ == "__main__":
    setup()
