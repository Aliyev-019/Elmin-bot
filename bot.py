import os
import sys
import tempfile
import subprocess
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from groq import Groq
from gtts import gTTS

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
LOCAL_VIDEO_URL = os.environ.get("LOCAL_VIDEO_URL")

# Təhlükəsizlik: Yalnız sizin Telegram ID-niz idarəetmə əmrlərini verə bilsin
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

client = Groq(api_key=GROQ_API_KEY)

# Groq AI cavabı
def get_ai_response(text):
    completion = client.chat.completions.create(
        model="qwen-2.5-32b",
        messages=[{"role": "user", "content": text}]
    )
    return completion.choices[0].message.content

# Səsli cavab
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

# 4K Şəkil
async def generate_image(update: Update, prompt: str):
    await update.message.reply_text("🖼 4K Realistik şəkil hazırlanır...")
    image_url = f"https://image.pollinations.ai/prompt/{requests.utils.quote(prompt)}?width=3840&height=2160&model=flux&nologo=true"
    await update.message.reply_photo(photo=image_url, caption=f"✨ *Prompt:* {prompt}", parse_mode="Markdown")

# Lokal Kompüter üzərindən Video Generasiyası
async def generate_video(update: Update, prompt: str):
    if not LOCAL_VIDEO_URL:
        await update.message.reply_text("⚠️ Video generator keçidi təyin olunmayıb.")
        return

    await update.message.reply_text("🎬 Video sorğusu lokal kompüterə göndərilir, zəhmət olmasa gözləyin...")
    
    try:
        response = requests.post(
            f"{LOCAL_VIDEO_URL}/generate-video", 
            json={"prompt": prompt}, 
            timeout=180
        )
        
        if response.status_code == 200:
            video_data = response.content
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
                temp_video.write(video_data)
                temp_video_path = temp_video.name
            
            with open(temp_video_path, 'rb') as video_file:
                await update.message.reply_video(video=video_file, caption=f"🎥 *Prompt:* {prompt}", parse_mode="Markdown")
            
            if os.path.exists(temp_video_path):
                os.remove(temp_video_path)
        else:
            await update.message.reply_text("❌ Kompüterdə video hazırlama proqramı hazırda aktiv deyil və ya xəta baş verdi.")
            
    except Exception as e:
        await update.message.reply_text("💻 Kompüterlə əlaqə saxlanıla bilmədi. Kompüterin və ngrok-un açıq olduğundan əmin olun.")

# KOMPYUTERİ UZAQDAN İDARƏ ETMƏ FUNKSİYALARI
async def handle_system_commands(update: Update, text: str):
    # Təhlükəsizlik yoxlaması
    if ADMIN_CHAT_ID and str(update.message.chat_id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text("⛔ Bu əmri icra etmək üçün icazəniz yoxdur.")
        return True

    cmd_text = text.lower().strip()

    # Ekran görüntüsü almaq
    if cmd_text in ["skrin", "screenshot", "ekran"]:
        if not LOCAL_VIDEO_URL:
            await update.message.reply_text("💻 Kompüter aktiv deyil (ngrok sönülüdür).")
            return True
        try:
            res = requests.get(f"{LOCAL_VIDEO_URL}/screenshot", timeout=10)
            if res.status_code == 200:
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_img:
                    temp_img.write(res.content)
                    temp_img_path = temp_img.name
                with open(temp_img_path, 'rb') as photo:
                    await update.message.reply_photo(photo=photo, caption="🖥 Kompüterin anlıq ekranı")
                if os.path.exists(temp_img_path):
                    os.remove(temp_img_path)
            else:
                await update.message.reply_text("❌ Ekran görüntüsü alına bilmədi.")
        except Exception:
            await update.message.reply_text("💻 Kompüterə qoşulmaq mümkün olmadı.")
        return True

    # Kompüteri söndürmək
    if cmd_text in ["söndür", "shutdown"]:
        if not LOCAL_VIDEO_URL:
            await update.message.reply_text("💻 Kompüter artıq sönülüdür və ya ngrok aktiv deyil.")
            return True
        try:
            requests.post(f"{LOCAL_VIDEO_URL}/system-control", json={"action": "shutdown"}, timeout=5)
            await update.message.reply_text("🔴 Kompüter 10 saniyə ərzində söndürülür...")
        except Exception:
            await update.message.reply_text("⚠️ Əmr göndərildi (kompüter bağlantısı kəsildi).")
        return True

    # Kompüteri yenidən başlatmaq
    if cmd_text in ["yenidən başlat", "restart"]:
        if not LOCAL_VIDEO_URL:
            await update.message.reply_text("💻 Kompüter aktiv deyil.")
            return True
        try:
            requests.post(f"{LOCAL_VIDEO_URL}/system-control", json={"action": "restart"}, timeout=5)
            await update.message.reply_text("🔄 Kompüter yenidən başladılır...")
        except Exception:
            await update.message.reply_text("⚠️ Əmr göndərildi.")
        return True

    # Xüsusi CMD əmri çalıştırmaq (/cmd dir)
    if text.startswith("/cmd "):
        command_to_run = text.replace("/cmd ", "", 1)
        if not LOCAL_VIDEO_URL:
            await update.message.reply_text("💻 Kompüter aktiv deyil.")
            return True
        try:
            res = requests.post(f"{LOCAL_VIDEO_URL}/run-cmd", json={"command": command_to_run}, timeout=15)
            if res.status_code == 200:
                output = res.json().get("output", "İcra olundu.")
                await update.message.reply_text(f"💻 *CMD Nəticəsi:*\n```\n{output}\n```", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Əmr icra edilərkən xəta baş verdi.")
        except Exception as e:
            await update.message.reply_text("💻 Kompüterə qoşulmaq mümkün olmadı.")
        return True

    return False

# Mətn mesajları
async def reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    # Sistem idarəetmə əmri olub-olmadığını yoxlayır
    if await handle_system_commands(update, user_text):
        return

    # Video istəyi
    if user_text.lower().startswith("video"):
        prompt = user_text.replace("video", "", 1).strip()
        await generate_video(update, prompt)
        return

    # Şəkil istəyi
    if user_text.lower().startswith("şəkil") or user_text.lower().startswith("photo") or user_text.lower().startswith("draw"):
        await generate_image(update, user_text)
        return

    # Standart Mətn və Səs cavabı
    ai_text = get_ai_response(user_text)
    await update.message.reply_text(ai_text)
    await send_voice_response(update, ai_text)

# Səsli mesajlar
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

        if await handle_system_commands(update, user_text):
            return

        if user_text.lower().startswith("video"):
            prompt = user_text.replace("video", "", 1).strip()
            await generate_video(update, prompt)
            return

        ai_text = get_ai_response(user_text)
        await update.message.reply_text(f"🗣 *Dəqiqləşdirilmiş:* {user_text}\n\n🤖 *Cavab:* {ai_text}", parse_mode="Markdown")
        await send_voice_response(update, ai_text)
        
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply_text))
    app.add_handler(MessageHandler(filters.COMMAND, reply_text))
    app.add_handler(MessageHandler(filters.VOICE, reply_voice))
    app.run_polling()
