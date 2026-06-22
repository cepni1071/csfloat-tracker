"""Fiyat kontrol çekirdeği — GUI içermez.

Hem masaüstü uygulaması (`main.py`) hem de arka plan kontrolcüsü
(`checker.py`) bu modülü kullanır. Takip listesindeki her skini CSFloat'ta
kontrol eder, gerekiyorsa bildirim/e-posta gönderir ve DB'yi günceller.
"""
import database
import api
import config
import notifier


def check_all_skins(on_progress=None):
    """Takip listesini kontrol eder. Sonuç sözlüklerinin listesini döndürür.

    on_progress(name, price): her skin kontrol edildiğinde çağrılır (UI için).
    """
    results = []
    for skin in database.get_all_skins():
        skin_id, name, target, last_price, fmin, fmax, _, global_price = skin
        fmin = float(fmin or 0.0)
        fmax = float(fmax or 1.0)
        has_filter = (fmin != 0.0 or fmax != 1.0)

        # Wear olmayan (Floatsız) isimler tüm wearleri arar
        is_base = not any(f"({w})" in name for w in api.WEARS)
        if is_base:
            listing = api.get_lowest_across_wears(name, fmin, fmax)
        else:
            listing = api.get_lowest_listing(name, fmin, fmax)
        if not listing:
            continue
        new_price = listing["price"]

        # Float filtresi varsa genel (float'sız) fiyatı da çek
        new_global = None
        if has_filter:
            g = api.get_lowest_across_wears(name) if is_base else api.get_lowest_listing(name)
            new_global = g["price"] if g else None

        # Ani düşüş: eşik kadar düştüyse
        dropped = bool(last_price and new_price < last_price and
                       ((last_price - new_price) / last_price) * 100 >= config.PRICE_DROP_THRESHOLD)
        # Hedef: yalnızca eşiği YENİ geçtiyse (üstündeyken altına/eşitine indi)
        hit_target = bool(target and new_price <= target and
                          (not last_price or last_price > target))

        if dropped:
            notifier.notify_price_drop(name, last_price, new_price, target)
        if hit_target:
            notifier.notify_target_reached(name, new_price, target)

        database.update_last_price(skin_id, new_price, new_global)
        results.append({
            "name": name, "price": new_price, "target": target,
            "hit_target": hit_target, "dropped": dropped,
        })
        if on_progress:
            on_progress(name, new_price)
    return results
