#!/usr/bin/env python3
"""ByMykel açık-kaynak CS2 veri setinden tüm skin isim / float / görsel
verisini indirip yerel `data/skins.json` dosyasına yazar.

Bir kez çalıştırılır. Uygulama çalışırken Steam'e GİTMEZ; isimleri ve
float aralıklarını bu yerel dosyadan okur (bkz. skindata.py). CS güncellemesi
yeni skinler eklediğinde tekrar çalıştırıp dosyayı yenileyebilirsin:

    python3 build_skindata.py
"""
import json
import datetime
from pathlib import Path

import requests

SRC = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"
OUT_DIR = Path(__file__).parent / "data"


def main():
    OUT_DIR.mkdir(exist_ok=True)
    print("indiriliyor:", SRC)
    resp = requests.get(SRC, headers={"User-Agent": "Mozilla/5.0"}, timeout=60)
    resp.raise_for_status()
    raw = resp.json()

    seen = set()
    out = []
    for s in raw:
        name = s.get("name")
        if not name or name in seen:          # Doppler fazları aynı ismi paylaşır
            continue
        seen.add(name)
        mn, mx = s.get("min_float"), s.get("max_float")
        out.append({
            "base":      name,
            "weapon":    (s.get("weapon") or {}).get("name", ""),
            "category":  (s.get("category") or {}).get("name", ""),
            "image":     s.get("image", ""),
            "min_float": 0.0 if mn is None else round(float(mn), 4),
            "max_float": 1.0 if mx is None else round(float(mx), 4),
            "stattrak":  bool(s.get("stattrak")),
        })

    out.sort(key=lambda x: x["base"])
    (OUT_DIR / "skins.json").write_text(
        json.dumps(out, ensure_ascii=False), encoding="utf-8")
    (OUT_DIR / "meta.json").write_text(json.dumps({
        "source": SRC,
        "generated": datetime.date.today().isoformat(),
        "count": len(out),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"yazıldı: {len(out)} skin -> {OUT_DIR / 'skins.json'}")


if __name__ == "__main__":
    main()
