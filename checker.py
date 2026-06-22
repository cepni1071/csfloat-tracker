#!/usr/bin/env python3
"""Arka plan fiyat kontrolü — uygulama AÇIK OLMASA da çalışır.

Takip listesindeki skinleri CSFloat'ta bir kez kontrol eder; hedef fiyatının
altına yeni düşen olursa e-posta gönderir, sonra çıkar. launchd/cron ile
periyodik çalıştırılır (bkz. com.cepni.csfloat-tracker.plist).
"""
import sys
import time

import database
import core


def main():
    database.init_db()
    started = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        results = core.check_all_skins()
    except Exception as e:
        print(f"[{started}] kontrol hatası: {e}", file=sys.stderr)
        return 1
    hits = [r for r in results if r["hit_target"]]
    print(f"[{started}] {len(results)} skin kontrol edildi, "
          f"{len(hits)} hedef fiyat altında"
          + (": " + ", ".join(r["name"] for r in hits) if hits else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
