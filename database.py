"""Veri katmanı — Supabase (bulut Postgres) üzerinden REST API ile.

Hem masaüstü arayüzü hem de GitHub Actions checker'ı AYNI bulut DB'yi kullanır,
böylece yerelde-kalan veri/kopukluk olmaz. Bağlantı bilgisi config.py'den
(SUPABASE_URL / SUPABASE_KEY) ya da ortam değişkenlerinden (GitHub Secrets)
okunur. Fonksiyon imzaları ve dönüş biçimleri eski SQLite sürümüyle aynıdır,
böylece main.py / core.py değişmeden çalışır.
"""
import os
import requests
import config

SUPABASE_URL = (getattr(config, "SUPABASE_URL", "") or os.environ.get("SUPABASE_URL", "")).rstrip("/")
SUPABASE_KEY = getattr(config, "SUPABASE_KEY", "") or os.environ.get("SUPABASE_KEY", "")

_SKIN_COLS = "id,market_hash_name,target_price,last_price,float_min,float_max,image_url,global_price"


def _headers(extra=None):
    h = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }
    if extra:
        h.update(extra)
    return h


def _rest(path):
    return f"{SUPABASE_URL}/rest/v1/{path}"


def _num(v):
    return float(v) if v is not None else None


def init_db():
    """Tablolar Supabase'de SQL ile bir kez oluşturulur; burada iş yok.
    Bağlantı eksikse uyarı verir."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        print("UYARI: SUPABASE_URL / SUPABASE_KEY ayarlı değil (config.py veya ortam değişkeni).")


def get_all_skins():
    try:
        r = requests.get(
            _rest(f"skins?select={_SKIN_COLS}&order=market_hash_name.asc"),
            headers=_headers(), timeout=20)
        r.raise_for_status()
        rows = r.json()
    except Exception as e:
        print(f"Supabase get_all_skins hatası: {e}")
        return []
    out = []
    for d in rows:
        out.append((
            d["id"], d["market_hash_name"], _num(d.get("target_price")),
            _num(d.get("last_price")),
            _num(d.get("float_min")) if d.get("float_min") is not None else 0.0,
            _num(d.get("float_max")) if d.get("float_max") is not None else 1.0,
            d.get("image_url"), _num(d.get("global_price")),
        ))
    return out


def add_skin(market_hash_name, target_price=None, float_min=0.0, float_max=1.0, image_url=None):
    body = {
        "market_hash_name": market_hash_name, "target_price": target_price,
        "float_min": float_min, "float_max": float_max, "image_url": image_url,
    }
    try:
        r = requests.post(_rest("skins"), headers=_headers({"Prefer": "return=minimal"}),
                          json=body, timeout=20)
        if r.status_code in (200, 201, 204):
            return True
        if r.status_code == 409:          # UNIQUE ihlali — zaten listede
            return False
        r.raise_for_status()
    except Exception as e:
        print(f"Supabase add_skin hatası: {e}")
    return False


def remove_skin(skin_id):
    try:
        requests.delete(_rest(f"skins?id=eq.{skin_id}"),
                        headers=_headers(), timeout=20).raise_for_status()
    except Exception as e:
        print(f"Supabase remove_skin hatası: {e}")


def update_last_price(skin_id, price, global_price=None):
    body = {"last_price": price}
    if global_price is not None:
        body["global_price"] = global_price
    try:
        requests.patch(_rest(f"skins?id=eq.{skin_id}"),
                       headers=_headers(), json=body, timeout=20).raise_for_status()
    except Exception as e:
        print(f"Supabase update_last_price hatası: {e}")


def update_target_price(skin_id, target_price):
    try:
        requests.patch(_rest(f"skins?id=eq.{skin_id}"), headers=_headers(),
                       json={"target_price": target_price}, timeout=20).raise_for_status()
    except Exception as e:
        print(f"Supabase update_target_price hatası: {e}")


def get_setting(key, default=None):
    try:
        r = requests.get(_rest(f"settings?key=eq.{key}&select=value"),
                         headers=_headers(), timeout=20)
        r.raise_for_status()
        rows = r.json()
        return rows[0]["value"] if rows else default
    except Exception as e:
        print(f"Supabase get_setting hatası: {e}")
        return default


def set_setting(key, value):
    body = {"key": key, "value": str(value)}
    try:
        requests.post(_rest("settings"),
                      headers=_headers({"Prefer": "resolution=merge-duplicates"}),
                      json=body, timeout=20).raise_for_status()
    except Exception as e:
        print(f"Supabase set_setting hatası: {e}")
