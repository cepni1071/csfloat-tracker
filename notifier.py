import smtplib
from email.message import EmailMessage

import requests
import config
import database

def send_email(subject: str, body: str):
    """SMTP üzerinden e-posta gönderir. config.EMAIL_ENABLED ve SMTP_* dolu
    değilse sessizce çıkar. (Gmail için 'uygulama şifresi' gerekir.)

    Alıcı adresi öncelikle uygulamada girilen ayardan (DB 'notify_email')
    alınır; yoksa config.EMAIL_TO'ya, o da yoksa gönderen adrese düşer."""
    if not getattr(config, "EMAIL_ENABLED", False):
        return
    host = getattr(config, "SMTP_HOST", "")
    user = getattr(config, "SMTP_USER", "")
    pwd  = getattr(config, "SMTP_PASSWORD", "")
    try:
        to = database.get_setting("notify_email") or getattr(config, "EMAIL_TO", "") or user
    except Exception:
        to = getattr(config, "EMAIL_TO", "") or user
    if not (host and user and pwd and to):
        return
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to
        msg.set_content(body)
        with smtplib.SMTP(host, int(getattr(config, "SMTP_PORT", 587)), timeout=20) as s:
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
    except Exception as e:
        print(f"E-posta hatası: {e}")

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
    send_email(
        f"🎯 Hedef fiyat altında: {skin_name}",
        f"{skin_name}\n\n"
        f"Şu anki en düşük fiyat: ${price:.2f}\n"
        f"Hedef fiyatın: ${target:.2f}\n\n"
        f"Bu item hedef fiyatının altına/eşitine düştü — CSFloat'ta kontrol et.\n"
        f"https://csfloat.com/search?market_hash_name={skin_name.replace(' ', '%20')}"
    )
