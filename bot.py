import os
import logging
import asyncio
from aiohttp import web
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
# Using the test token from your screenshot
BOT_TOKEN = "8966040622:AAEFlHB3i84oSxQaeXBoB6bpTJTQCfbGDPQ" 
PORT = int(os.environ.get("PORT", 8080))
# Render will provide this URL. You will set this in the Render dashboard.
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://your-app-name.onrender.com")

# Enable logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# --- BOT HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 Welcome to the Lyrics & Song Bot!\n\n"
        "Use `/lyrics Artist - Song Name` to find lyrics.\n"
        "Or just type a song name to search for it!"
    )

async def get_lyrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("❌ Please use the format: `/lyrics Artist - Song Name`")
        return
    
    await update.message.reply_text(f"🔎 Searching lyrics for: {text}...")
    
    try:
        # Split by "-" to separate artist and title if provided
        if " - " in text:
            artist, title = text.split(" - ", 1)
        else:
            # If no hyphen, just search by title
            artist, title = "", text

        # Fetch lyrics from a free API (using asyncio.to_thread to prevent blocking)
        def fetch_lyrics():
            url = f"https://api.lyrics.ovh/v1/{artist}/{title}" if artist else f"https://api.lyrics.ovh/v1/Unknown/{title}"
            response = requests.get(url)
            if response.status_code == 200:
                return response.json().get("lyrics", "Lyrics not found.")
            return "Lyrics not found."

        lyrics = await asyncio.to_thread(fetch_lyrics)
        
        # Telegram has a 4096 character limit, so we truncate if needed
        if len(lyrics) > 4000:
            lyrics = lyrics[:4000] + "\n\n... (truncated)"
            
        await update.message.reply_text(lyrics)
    except Exception as e:
        logger.error(f"Error fetching lyrics: {e}")
        await update.message.reply_text("❌ Sorry, I couldn't find the lyrics for that song.")

async def search_song(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    # This is a placeholder for your song player logic
    await update.message.reply_text(f"🎧 Searching for the song: '{query}'\n\n(Downloader logic goes here...)")

# --- WEB SERVER & WEBHOOK SETUP ---
async def main():
    # 1. Initialize the Telegram Bot
    application = Application.builder().token(BOT_TOKEN).build()

    # 2. Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("lyrics", get_lyrics))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_song))

    # 3. Create a web server (aiohttp) to keep Render happy
    app = web.Application()

    # Health check endpoint for Render
    app.router.add_get("/", lambda r: web.Response(text="Bot is alive and running!"))

    # Webhook endpoint to receive messages from Telegram
    async def telegram_webhook(request):
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.update_queue.put(update)
        return web.Response(text="OK")

    app.router.add_post(f"/{BOT_TOKEN}", telegram_webhook)

    # 4. Set the Telegram Webhook
    webhook_path = f"{WEBHOOK_URL}/{BOT_TOKEN}"
    await application.bot.set_webhook(url=webhook_path)
    logger.info(f"Webhook set to {webhook_path}")

    # 5. Start the web server
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"Web server running on port {PORT}")

    # 6. Start the bot application
    await application.initialize()
    await application.start()
    
    # Keep the program running forever
    await asyncio.Event().wait()

if __name__ == "__main__":
    # We use asyncio.run() properly here to prevent the event loop errors
    asyncio.run(main())
