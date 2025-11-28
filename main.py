import os
import logging
from pyrogram import Client, filters
from pyrogram.types import Message
from telethon.sessions import StringSession
from telethon.sync import TelegramClient

# लॉगिंग सेट (Logging setup)
logging.basicConfig(level=logging.INFO)
LOG = logging.getLogger(__name__)

# --- Render Environment Variables ---
try:
    # यह बॉट अपना API ID/HASH Render के Environment Variables से लेगा।
    API_ID = os.environ.get("API_ID")
    API_HASH = os.environ.get("API_HASH")
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    if not all([API_ID, API_HASH, BOT_TOKEN]):
        raise ValueError("Configuration Error: Please set API_ID, API_HASH, and BOT_TOKEN in Render.")
except ValueError as e:
    LOG.error(f"❌ {e}")
    # बॉट शुरू नहीं होगा अगर वेरिएबल्स सेट नहीं हैं
    exit(1)

# Pyrogram Client for the BOT (यह आपके बॉट को चलाएगा)
bot = Client(
    "StringSessionBot",
    api_id=int(API_ID),
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

@bot.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    await message.reply_text(
        "नमस्ते! मैं Telethon String Session Generator बॉट हूँ।\n"
        "सेशन जनरेट करने के लिए `/generate` कमांड चलाएँ।"
    )

@bot.on_message(filters.command("generate"))
async def generate_handler(client: Client, message: Message):
    user_id = message.from_user.id

    try:
        # --- स्टेप 1: API ID प्राप्त करें ---
        await message.reply_text("कृपया अपना **API ID** (केवल अंक) भेजें:")
        api_id_msg = await client.listen(user_id, filters.text, timeout=300)
        user_api_id = api_id_msg.text.strip()
        
        if not user_api_id.isdigit():
            await message.reply_text("❌ अमान्य API ID. कृपया केवल अंक भेजें। प्रक्रिया रद्द की गई।")
            return

        # --- स्टेप 2: API HASH प्राप्त करें ---
        await api_id_msg.reply_text("अब अपना **API HASH** (32-character string) भेजें:")
        api_hash_msg = await client.listen(user_id, filters.text, timeout=300)
        user_api_hash = api_hash_msg.text.strip()

        # --- स्टेप 3: फ़ोन नंबर प्राप्त करें ---
        await api_hash_msg.reply_text("अब अपना **फ़ोन नंबर** (अंतर्राष्ट्रीय फ़ॉर्मेट में, जैसे `+911234567890`) भेजें:")
        phone_msg = await client.listen(user_id, filters.text, timeout=300)
        phone_number = phone_msg.text.strip()
        
        # --- Telethon Session Generation शुरू करें ---
        temp_message = await phone_msg.reply_text(
            "🔑 लॉगिन शुरू कर रहा हूँ... कोड के लिए अपने Telegram Saved Messages/Device Notifications चेक करें।"
        )
        
        # Telethon Client को इनिशियलाइज़ (Initialize) करें
        session_client = TelegramClient(
            StringSession(), 
            int(user_api_id), 
            user_api_hash
        )

        try:
            await session_client.connect()
            await session_client.send_code_request(phone_number)
            
            # --- स्टेप 4: कोड प्राप्त करें ---
            await temp_message.edit_text("कृपया अपने Telegram अकाउंट पर प्राप्त हुआ **लॉगिन कोड** भेजें:")
            code_msg = await client.listen(user_id, filters.text, timeout=300)
            phone_code = code_msg.text.strip()
            
            # --- लॉगिन का प्रयास ---
            try:
                # कोड से साइन इन करें
                await session_client.sign_in(phone_number, phone_code)
                
            except Exception as e:
                # 2FA पासवर्ड की जाँच करें
                if "AUTH_REFUSED" in str(e): 
                    await code_msg.reply_text("🔒 Two-Factor Authentication (2FA) पासवर्ड की ज़रूरत है। कृपया अपना **क्लाउड पासवर्ड** भेजें:")
                    password_msg = await client.listen(user_id, filters.text, timeout=300)
                    password = password_msg.text.strip()
                    
                    await session_client.sign_in(password=password) # पासवर्ड से साइन इन करें
                else:
                    raise e # अन्य त्रुटियों को आगे बढ़ाएँ

            # --- सफलता: String जनरेट करें और भेजें ---
            string_session = session_client.session.save()
            
            # String Session को यूज़र को भेजें
            await client.send_message(
                user_id,
                "**✅ आपकी Telethon String Session सफलतापूर्वक जनरेट हो गई है:**\n\n"
                f"```python\n{string_session}\n```\n\n"
                "**⚠️ सुरक्षा चेतावनी:** यह स्ट्रिंग आपके Telegram अकाउंट का पूरा एक्सेस देती है। इसे इस्तेमाल करने के तुरंत बाद **Active Sessions** में जाकर इस सेशन को **हटा दें (Terminate)**।"
            )

        finally:
            await session_client.disconnect() # क्लाइंट को डिस्कनेक्ट करें

    except TimeoutError:
        await message.reply_text("⏰ समय समाप्त हो गया। कृपया `/generate` कमांड चलाकर फिर से शुरू करें।")
    except Exception as e:
        LOG.error(f"❌ String जनरेशन में त्रुटि: {e}")
        error_message = f"❌ String जनरेशन के दौरान एक त्रुटि हुई:\n\n`{e}`\n\n"
        if "API_ID_INVALID" in str(e) or "API_ID_BLANK" in str(e):
            error_message += "त्रुटि: API ID या API HASH गलत है। कृपया my.telegram.org से दोबारा जाँच करें।"
        elif "PHONE_NUMBER_INVALID" in str(e):
             error_message += "त्रुटि: फ़ोन नंबर अमान्य है। कृपया अंतर्राष्ट्रीय फ़ॉर्मेट (+देश कोड) में डालें।"
        
        await client.send_message(user_id, error_message)
    
if __name__ == "__main__":
    LOG.info("Bot starting...")
    bot.run()
      
