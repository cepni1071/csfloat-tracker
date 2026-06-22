import requests
import config

def send_telegram(message: str):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": config.TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as e:
        print(f"Telegram hatası: {e}")

def send_desktop(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, app_name="CSFloat Tracker", timeout=8)
    except Exception:
        pass

def notify_price_drop(skin_name: str, old_price: float, new_price: float, target: float | None):
    drop_pct = ((old_price - new_price) / old_price) * 100
    msg = (
        f"📉 <b>Fiyat Düştü!</b>\n"
        f"<b>{skin_name}</b>\n"
        f"${old_price:.2f} → <b>${new_price:.2f}</b> ({drop_pct:.1f}% düşüş)"
    )
    if target and new_price <= target:
        msg += f"\n✅ Hedef fiyatına ulaştı! (${target:.2f})"

    send_telegram(msg)
    send_desktop(
        "CSFloat Tracker — Fiyat Düştü!",
        f"{skin_name}: ${old_price:.2f} → ${new_price:.2f}"
    )

def notify_target_reached(skin_name: str, price: float, target: float):
    msg = (
        f"🎯 <b>Hedef Fiyat!</b>\n"
        f"<b>{skin_name}</b>\n"
        f"Şu an: <b>${price:.2f}</b> (Hedef: ${target:.2f})"
    )
    send_telegram(msg)
    send_desktop("CSFloat Tracker — Hedef Fiyat!", f"{skin_name}: ${price:.2f}")
