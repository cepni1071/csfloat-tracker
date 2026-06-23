"""Yerel skin veri tabanı.

Tüm skin isimleri, kategorileri ve float aralıkları `data/skins.json`
dosyasından okunur — arama/otomatik-tamamlama için Steam'e GİDİLMEZ. Veri
statiktir ve `build_skindata.py` ile üretilir/yenilenir. Fiyatlar bu modülde
yoktur; onlar yalnızca CSFloat'tan (Güncelle) alınır.
"""
import json
import re
from pathlib import Path

_FILE = Path(__file__).parent / "data" / "skins.json"
_skins = None
_norm_names = None   # her skinin tire/boşluk/noktalamadan arındırılmış adı


def _norm(s):
    """Eşleştirme için sadeleştirir: harf+rakam dışını atar, küçük harfe çevirir.
    Böylece 'm4a1s' = 'M4A1-S', 'ak47' = 'AK-47' gibi yazımlar da eşleşir."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _all():
    global _skins, _norm_names
    if _skins is None:
        try:
            with open(_FILE, encoding="utf-8") as f:
                _skins = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _skins = []
        _norm_names = [_norm(s["base"]) for s in _skins]
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
    """İsmi `query`'yi içeren skinleri yerel veriden döndürür (isim sıralı).
    Tire/boşluk/noktalama yok sayılır: 'm4a1s', 'ak47' de eşleşir."""
    q = _norm(query)
    if len(q) < 2:
        return []
    _all()  # _skins ve _norm_names'i yükle
    out = [_row(_skins[i]) for i, name in enumerate(_norm_names) if q in name]
    out.sort(key=lambda r: r["base"])
    return out[:limit]


def count():
    return len(_all())
