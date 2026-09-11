import os
import tempfile
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from groq import Groq
from gtts import gTTS

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

# Groq AI cavabı
def get_ai_response(text):
    completion = client.chat.completions.create(
        model="qwen-2.5-32b",
        messages=[{"role": "user", "content": text}]
    )
    return completion.choices[0].message.content

# Səsli cavab yaradan funksiya
async def send_voice_response(update: Update, text_to_speak: str):
    tts = gTTS(text=text_to_speak, lang='az')
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
        tts.save(temp_audio.name)
        temp_audio_path = temp_audio.name

    try:
        with open(temp_audio_path, 'rb') as voice:
            await update.message.reply_voice(voice=voice)
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# 4K Realistik Şəkil Generasiyası
async def generate_image(update: Update, prompt: str):
    await update.message.reply_text("🖼 4K Realistik şəkil hazırlanır, zəhmət olmasa gözləyin...")
    image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=3840&height=2160&model=flux&nologo=true"
    await update.message.reply_photo(photo=image_url, caption=f"✨ *Prompt:* {prompt}", parse_mode="Markdown")

# Mətn mesajlarına cavab (Həm SMS, həm Səs)
async def reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    # Əgər istifadəçi şəkil istəyirsə (məsələn: /img və ya "şəkil çek ...")
    if user_text.lower().startswith("şəkil") or user_text.lower().startswith("photo") or user_text.lower().startswith("draw"):
        await generate_image(update, user_text)
        return

    ai_text = get_ai_response(user_text)
    
    # Həm SMS (mətn) kimi göndərir
    await update.message.reply_text(ai_text)
    # Həm də Səsli mesaj kimi göndərir
    await send_voice_response(update, ai_text)

# Səsli mesajlara cavab
async def reply_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as temp_audio:
        await voice_file.download_to_drive(temp_audio.name)
        temp_audio_path = temp_audio.name

    try:
        with open(temp_audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=(temp_audio_path, audio_file.read()),
                model="whisper-large-v3",
                response_format="text"
            )
        
        user_text = str(transcription)
        ai_text = get_ai_response(user_text)
        
        await update.message.reply_text(f"🗣 *Dediğiniz:* {user_text}\n\n🤖 *Cavab:* {ai_text}", parse_mode="Markdown")
        await send_voice_response(update, ai_text)
        
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_text))
    app.add_handler(MessageHandler(filters.VOICE, reply_voice))
    app.run_polling()
