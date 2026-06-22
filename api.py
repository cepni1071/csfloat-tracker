import requests
import concurrent.futures
import re
import time
from urllib.parse import quote
import config

BASE_URL  = "https://csfloat.com/api/v1"
STEAM_IMG = "https://steamcommunity-a.akamaihd.net/economy/image"
STEAM_URL = "https://steamcommunity.com/market/search/render/"
UA        = {"User-Agent": "Mozilla/5.0"}

WEAPON_TAGS = {
    "ak47": "tag_weapon_ak47",        "ak-47": "tag_weapon_ak47",
    "m4a4": "tag_weapon_m4a1",        "m4a1": "tag_weapon_m4a1_silencer",
    "m4a1-s": "tag_weapon_m4a1_silencer",
    "awp": "tag_weapon_awp",
    "deagle": "tag_weapon_deagle",    "desert eagle": "tag_weapon_deagle",
    "usp": "tag_weapon_usp_silencer", "usp-s": "tag_weapon_usp_silencer",
    "glock": "tag_weapon_glock",      "glock-18": "tag_weapon_glock",
    "p250": "tag_weapon_p250",        "p2000": "tag_weapon_hkp2000",
    "mp9": "tag_weapon_mp9",          "mp5": "tag_weapon_mp5sd",
    "famas": "tag_weapon_famas",      "galil": "tag_weapon_galilar",
    "aug": "tag_weapon_aug",          "sg553": "tag_weapon_sg556",
    "ssg08": "tag_weapon_ssg08",      "ssg": "tag_weapon_ssg08",
    "karambit": "tag_weapon_knife_karambit",
    "butterfly": "tag_weapon_knife_butterfly",
    "m9": "tag_weapon_knife_m9_bayonet", "m9 bayonet": "tag_weapon_knife_m9_bayonet",
    "bayonet": "tag_weapon_knife_bayonet",
    "flip": "tag_weapon_knife_flip",  "gut": "tag_weapon_knife_gut",
    "falchion": "tag_weapon_knife_falchion",
    "shadow daggers": "tag_weapon_knife_push",
    "bowie": "tag_weapon_knife_survival_bowie",
    "huntsman": "tag_weapon_knife_tactical",
    "navaja": "tag_weapon_knife_gypsy_jackknife",
    "stiletto": "tag_weapon_knife_stiletto",
    "talon": "tag_weapon_knife_widowmaker",
    "ursus": "tag_weapon_knife_ursus",
    "paracord": "tag_weapon_knife_cord",
    "nomad": "tag_weapon_knife_nomad",
    "skeleton": "tag_weapon_knife_skeleton",
    "kukri": "tag_weapon_knife_kukri",
    "gloves": "tag_Type_Hands",       "eldiven": "tag_Type_Hands",
    "knife": "tag_CSGO_Type_Knife",   "knives": "tag_CSGO_Type_Knife",
    "bicak": "tag_CSGO_Type_Knife",   "bıçak": "tag_CSGO_Type_Knife",
}

# Steam "Type" kategorisi tag'leri category_730_Type[] ile sorgulanır;
# diğer silah tag'leri category_730_Weapon[] ile.
TYPE_TAGS = {"tag_Type_Hands", "tag_CSGO_Type_Knife"}

_cache: dict = {}  # key → (timestamp, list)

def get_headers():
    return {"Authorization": config.CSFLOAT_API_KEY}

# --- CSFloat ---

WEARS = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]

def get_lowest_listing(market_hash_name: str, float_min=0.0, float_max=1.0) -> dict | None:
    try:
        encoded = quote(market_hash_name, safe="")
        url = f"{BASE_URL}/listings?market_hash_name={encoded}&sort_by=lowest_price&limit=1"
        if float_min > 0.0:
            url += f"&min_float={float_min:.4f}"
        if float_max < 1.0:
            url += f"&max_float={float_max:.4f}"
        resp = requests.get(url, headers=get_headers(), timeout=10)
        resp.raise_for_status()
        listings = resp.json().get("data", [])
        if not listings:
            return None
        item = listings[0]
        return {
            "price":       item["price"] / 100,
            "float_value": item["item"].get("float_value"),
            "wear_name":   item["item"].get("wear_name"),
            "seller":      item.get("seller", {}).get("username", ""),
        }
    except requests.RequestException as e:
        print(f"CSFloat hatası ({market_hash_name}): {e}")
        return None

def get_lowest_across_wears(base_name: str, float_min=0.0, float_max=1.0) -> dict | None:
    """Normal (non-StatTrak) skin için tüm wearleri arar, en ucuzunu döndürür."""
    best = None
    for wear in WEARS:
        result = get_lowest_listing(f"{base_name} ({wear})", float_min, float_max)
        if result and (best is None or result["price"] < best["price"]):
            best = dict(result)
            best["wear_name"] = wear
    return best

# --- Steam Market ---

def _steam_page(params: dict) -> tuple[int, list]:
    try:
        resp = requests.get(STEAM_URL, params=params, headers=UA, timeout=12)
        resp.raise_for_status()
        data = resp.json()
        return data.get("total_count", 0), data.get("results", [])
    except Exception:
        return 0, []

def search_all_skins(query: str) -> list[dict]:
    """
    Silaha ait tüm unique base skin isimlerini döndürür.
    StatTrak, Souvenir hariç. Sonuçlar isme göre sıralı. 1 saat cache'lenir.
    """
    cache_key = query.strip().lower()
    if cache_key in _cache:
        ts, data = _cache[cache_key]
        if time.time() - ts < 3600:
            return data

    tag = WEAPON_TAGS.get(cache_key)
    params = {"appid": 730, "norender": 1,
              "sort_column": "name", "sort_dir": "asc", "count": 10}
    if tag:
        cat_key = "category_730_Type[]" if tag in TYPE_TAGS else "category_730_Weapon[]"
        params[cat_key] = tag
    elif len(cache_key) >= 2:
        params["query"] = query
        params["search_descriptions"] = 0
    else:
        return []

    # İlk sayfa + toplam sayı
    total, first_items = _steam_page({**params, "start": 0})
    if not first_items:
        return []

    # Kalan tüm sayfaları paralel çek
    all_items = list(first_items)
    offsets = list(range(10, total, 10))
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        for _, items in ex.map(lambda off: _steam_page({**params, "start": off}), offsets):
            all_items.extend(items)

    # Deduplicate: sadece Normal skinler (StatTrak/Souvenir hariç)
    seen = set()
    results = []
    for item in all_items:
        name = item.get("name", "")
        if "StatTrak™" in name or "Souvenir" in name:
            continue
        if "|" not in name and "Gloves" not in name and "Wraps" not in name:
            continue
        base = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        if base in seen:
            continue
        seen.add(base)
        icon = item.get("asset_description", {}).get("icon_url", "")
        results.append({
            "base":      base,
            "image_url": f"{STEAM_IMG}/{icon}/128x96" if icon else "",
            "is_knife":  "★" in base,
        })

    _cache[cache_key] = (time.time(), results)
    return results
