"""
🔮 Nazar — Fal Botu
Kahve, el ve tarot falı bakan Telegram botu.
Fotoğraf gönder → AI ile gerçek fal yorumu al.
"""

import os
import json
import time
import base64
import logging
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_KEY    = os.environ["ANTHROPIC_KEY"]

# Kullanıcı başına beklenen fal türü
user_state = {}  # chat_id → {"type": "kahve"|"el"|"tarot"}

PROMPTS = {
    "kahve": """Sen gizemli ve deneyimli bir Türk kahve falcısısın. Bu kahve fincanı fotoğrafını derinlemesine analiz et. Telve şekillerini, sembolleri ve desenleri yorumla.

Yanıtını TAM OLARAK bu JSON formatında ver (başka hiçbir şey yazma):
{
  "genel": "Fincan ve telvedeki sembollerin yorumu. 2-3 cümle.",
  "gercekler": "Bu kişinin hayatıyla ilgili 2-3 çarpıcı gerçek. Çok spesifik ol.",
  "ask": "Aşk ve ilişkiler hakkında yorum. 2 cümle.",
  "kariyer": "Kariyer ve para hakkında yorum. 2 cümle.",
  "uyari": "Dikkat edilmesi gereken tehlike veya uyarı. 1-2 cümle.",
  "gelecek": "Önümüzdeki 3-6 ay için gelecek tahmini. 2-3 cümle."
}""",

    "el": """Sen gizemli ve deneyimli bir el falcısısın. Bu el fotoğrafını derinlemesine analiz et. Avuç içindeki çizgileri, parmakları ve tümsekleri yorumla.

Yanıtını TAM OLARAK bu JSON formatında ver (başka hiçbir şey yazma):
{
  "genel": "Elin genel yapısı ve enerji analizi. 2-3 cümle.",
  "gercekler": "Bu kişinin hayatıyla ilgili 2-3 çarpıcı gerçek. Çok spesifik ol.",
  "ask": "Kalp çizgisine göre aşk yorumu. 2 cümle.",
  "kariyer": "Kader çizgisine göre kariyer yorumu. 2 cümle.",
  "uyari": "Elde gördüğün uyarı işaretleri. 1-2 cümle.",
  "gelecek": "Çizgilere göre gelecek tahmini. 2-3 cümle."
}""",

    "tarot": """Sen gizemli ve deneyimli bir tarot okuyucususun. Bu tarot kartı fotoğrafını derinlemesine yorumla. Sembolleri, figürleri ve pozisyonu analiz et.

Yanıtını TAM OLARAK bu JSON formatında ver (başka hiçbir şey yazma):
{
  "genel": "Kartın genel enerjisi ve temel mesajı. 2-3 cümle.",
  "gercekler": "Bu kart bu kişinin hayatı hakkında ne söylüyor? 2-3 içgörü.",
  "ask": "Kartın aşk konusundaki mesajı. 2 cümle.",
  "kariyer": "Kartın kariyer konusundaki mesajı. 2 cümle.",
  "uyari": "Kartın uyarı mesajı. 1-2 cümle.",
  "gelecek": "Kartın geleceğe dair kehaneti. 2-3 cümle."
}"""
}

TYPE_LABELS = {
    "kahve": "☕ Kahve Falı",
    "el":    "🤲 El Falı",
    "tarot": "🃏 Tarot"
}

# ── TELEGRAM ──────────────────────────────────────────────
def send(chat_id, text, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.error(f"Telegram hata: {e}")

def send_typing(chat_id):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5
        )
    except:
        pass

def get_file_url(file_id):
    r = requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
        params={"file_id": file_id}, timeout=10
    )
    path = r.json()["result"]["file_path"]
    return f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{path}"

def download_image(file_url):
    r = requests.get(file_url, timeout=20)
    return base64.b64encode(r.content).decode("utf-8")

def get_updates(offset=None):
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates",
            params={"timeout": 20, "allowed_updates": ["message"], "offset": offset},
            timeout=25
        )
        return r.json().get("result", [])
    except Exception as e:
        log.error(f"getUpdates hata: {e}")
        return []

# ── ANTHROPIC ─────────────────────────────────────────────
def analyze_image(image_b64, fal_type):
    prompt = PROMPTS.get(fal_type, PROMPTS["kahve"])
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "Content-Type": "application/json",
                "x-api-key": ANTHROPIC_KEY,
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_b64
                            }
                        },
                        {"type": "text", "text": prompt}
                    ]
                }]
            },
            timeout=30
        )
        data = r.json()
        if not r.ok:
            raise Exception(data.get("error", {}).get("message", "API hatası"))
        text = data["content"][0]["text"]
        cleaned = text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise Exception("Fal yorumu ayrıştırılamadı")
    except Exception as e:
        raise Exception(str(e))

# ── FORMAT ────────────────────────────────────────────────
def format_fortune(fortune, fal_type):
    label = TYPE_LABELS.get(fal_type, "🔮 Fal")
    lines = [
        f"✦ <b>{label} Sonucu</b> ✦\n",
        f"🔮 <b>Genel Enerji</b>",
        fortune.get("genel", ""),
        "",
        f"⚡ <b>Hayatından Çarpıcı Gerçekler</b>",
        fortune.get("gercekler", ""),
        "",
        f"💗 <b>Aşk & İlişkiler</b>",
        fortune.get("ask", ""),
        "",
        f"✨ <b>Kariyer & Bolluk</b>",
        fortune.get("kariyer", ""),
        "",
        f"⚠️ <b>Uyarı</b>",
        fortune.get("uyari", ""),
        "",
        f"🌙 <b>Gelecek Kehaneti</b>",
        fortune.get("gelecek", ""),
        "",
        "─────────────────",
        "<i>✦ Yeni fal için /fal yaz ✦</i>"
    ]
    return "\n".join(lines)

# ── KOMUTLAR ─────────────────────────────────────────────
def handle_message(update):
    msg = update.get("message", {})
    chat_id = str(msg.get("chat", {}).get("id", ""))
    text = msg.get("text", "")
    photo = msg.get("photo")

    if not chat_id:
        return

    # Yetki kontrolü
    if chat_id != str(TELEGRAM_CHAT_ID):
        send(chat_id, "🔮 Bu bot özeldir.")
        return

    # Komutlar
    if text:
        cmd = text.strip().lower().split("@")[0]

        if cmd in ["/start", "/merhaba"]:
            send(chat_id,
                "✦ <b>NAZAR — Dijital Falcı</b> ✦\n\n"
                "🔮 Fotoğrafını gönder, kaderine bak!\n\n"
                "Fal türünü seç:\n"
                "/kahve — ☕ Kahve Falı\n"
                "/el — 🤲 El Falı\n"
                "/tarot — 🃏 Tarot\n\n"
                "<i>Komuttan sonra fotoğrafını gönder.</i>"
            )

        elif cmd == "/kahve":
            user_state[chat_id] = {"type": "kahve"}
            send(chat_id,
                "☕ <b>Kahve Falı</b>\n\n"
                "Fincanının fotoğrafını gönder.\n"
                "<i>Telve çökmüş, fincan ters çevrilmiş olsun.</i>"
            )

        elif cmd == "/el":
            user_state[chat_id] = {"type": "el"}
            send(chat_id,
                "🤲 <b>El Falı</b>\n\n"
                "Avuç içinin fotoğrafını gönder.\n"
                "<i>İyi ışık altında, parmaklar açık olsun.</i>"
            )

        elif cmd == "/tarot":
            user_state[chat_id] = {"type": "tarot"}
            send(chat_id,
                "🃏 <b>Tarot</b>\n\n"
                "Tarot kartının fotoğrafını gönder.\n"
                "<i>Tek kart veya dizi olabilir.</i>"
            )

        elif cmd == "/fal":
            send(chat_id,
                "🔮 Hangi fal türü?\n\n"
                "/kahve — ☕ Kahve Falı\n"
                "/el — 🤲 El Falı\n"
                "/tarot — 🃏 Tarot"
            )

        else:
            if chat_id not in user_state:
                send(chat_id,
                    "🔮 Önce fal türünü seç:\n"
                    "/kahve · /el · /tarot"
                )

    # Fotoğraf geldi
    elif photo:
        fal_type = user_state.get(chat_id, {}).get("type", "kahve")
        label = TYPE_LABELS.get(fal_type, "🔮 Fal")

        send(chat_id,
            f"🔮 {label} okunuyor...\n"
            "<i>Semboller analiz ediliyor, biraz bekle...</i>"
        )
        send_typing(chat_id)

        try:
            # En yüksek kaliteli fotoğrafı al
            best_photo = max(photo, key=lambda p: p.get("file_size", 0))
            file_url = get_file_url(best_photo["file_id"])
            image_b64 = download_image(file_url)

            fortune = analyze_image(image_b64, fal_type)
            result_text = format_fortune(fortune, fal_type)
            send(chat_id, result_text)

            # State sıfırla
            user_state.pop(chat_id, None)

        except Exception as e:
            log.error(f"Fal hatası: {e}")
            send(chat_id,
                f"⚠️ Fal okunurken bir sorun oluştu.\n"
                f"<i>{str(e)[:100]}</i>\n\n"
                "Tekrar dene: /kahve · /el · /tarot"
            )
    else:
        if chat_id not in user_state:
            send(chat_id, "🔮 Fal türü seç: /kahve · /el · /tarot")

# ── ANA LOOP ──────────────────────────────────────────────
def main():
    log.info("🔮 Nazar Fal Botu başladı...")
    offset = None
    start = time.time()

    # İlk çalışmada hoş geldin mesajı gönder
    send(TELEGRAM_CHAT_ID,
        "✦ <b>Nazar Fal Botu aktif!</b> ✦\n\n"
        "/kahve · /el · /tarot\n"
        "<i>Fotoğraf gönder, kaderine bak.</i>"
    )

    while time.time() - start < 50:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            handle_message(update)
        time.sleep(1)

    log.info("Bot loop tamamlandı.")

if __name__ == "__main__":
    main()
