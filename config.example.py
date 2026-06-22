CSFLOAT_API_KEY = ""       # csfloat.com > Settings > API Key
TELEGRAM_BOT_TOKEN = ""    # @BotFather'dan alacaksın
TELEGRAM_CHAT_ID = ""      # @userinfobot'tan alacaksın

CHECK_INTERVAL_MINUTES = 5  # Kaç dakikada bir kontrol etsin
PRICE_DROP_THRESHOLD = 5    # % kaç düşünce bildirim gelsin
CSFLOAT_MIN_INTERVAL = 1.2  # CSFloat istekleri arası en az saniye (429'a takılmamak için)

# E-posta bildirimi (hedef fiyatın altına düşünce mail gelir)
EMAIL_ENABLED = False
EMAIL_TO      = ""                # mailin gideceği adres
SMTP_HOST     = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = ""                # gönderen Gmail adresin
SMTP_PASSWORD = ""                # Gmail "Uygulama Şifresi" (App Password)
