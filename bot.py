import os
from telegram import Update 
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from groq import Groq

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN") 
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE): 
  user_text = update.message.text
  completion = client.chat.completions.create( 
    model="qwen-2.5-32b",
    messages=[{"role": "user", "content": user_text}]
  ) 
  await update.message.reply_text(completion.choices[0].message.content)
if __name__ == '__main__': 
  app = ApplicationBuilder().token(TELEGRAM_TOKEN).build() 
  app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))
  app.run_polling()
