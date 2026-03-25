import requests
from django.conf import settings


def send_telegram_message(message):
    bot_token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)

    if not bot_token or not chat_id:
        return {'success': False, 'error': 'Telegram settings missing.'}

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'HTML',
    }

    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            return {'success': True, 'response': response.json()}
        return {'success': False, 'error': response.text}
    except Exception as e:
        return {'success': False, 'error': str(e)}