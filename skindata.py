"""Yerel skin veri tabanı.

Tüm skin isimleri, kategorileri ve float aralıkları `data/skins.json`
dosyasından okunur — arama/otomatik-tamamlama için Steam'e GİDİLMEZ. Veri
statiktir ve `build_skindata.py` ile üretilir/yenilenir. Fiyatlar bu modülde
yoktur; onlar yalnızca CSFloat'tan (Güncelle) alınır.
"""
import json
from pathlib import Path

_FILE = Path(__file__).parent / "data" / "skins.json"
_skins = None


def _all():
    global _skins
    if _skins is None:
        try:
            with open(_FILE, encoding="utf-8") as f:
                _skins = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _skins = []
    return _skins


def _row(s):
    """Dropdown'un beklediği biçime çevirir."""
    base = s["base"]
    return {
        "base":      base,
        "image_url": s.get("image", ""),
        "is_knife":  "★" in base and s.get("category") == "Knives",
        "min_float": s.get("min_float", 0.0),
        "max_float": s.get("max_float", 1.0),
        "stattrak":  s.get("stattrak", False),
    }


def search(query, limit=400):
    """İsmi `query`'yi içeren skinleri yerel veriden döndürür (isim sıralı)."""
    q = (query or "").strip().lower()
    if len(q) < 2:
        return []
    out = [_row(s) for s in _all() if q in s["base"].lower()]
    out.sort(key=lambda r: r["base"])
    return out[:limit]


def count():
    return len(_all())
