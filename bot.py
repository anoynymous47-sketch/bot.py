import requests, glob, asyncio, urllib.parse
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

BOT_TOKEN = "8966040622:AAEFlHB3i84oSxQaeXBoB6bpTJTQCfbGDPQ"

def search_music(q):
    try:
        r = requests.get("https://itunes.apple.com/search", params={"term": q, "media": "music", "limit": 7}, timeout=10)
        if r.ok and r.json().get("results"): 
            return r.json()["results"]
    except: pass
    try:
        r = requests.get("https://api.deezer.com/search", params={"q": q}, timeout=10)
        if r.ok and r.json().get("data"):
            return [{"artistName": d["artist"]["name"], "trackName": d["title"]} for d in r.json()["data"][:7]]
    except: pass
    return []

def get_lyrics(artist, track):
    try:
        r = requests.get("https://lrclib.net/api/get", params={"artist_name": artist, "track_name": track}, timeout=10)
        if r.ok and r.json().get("plainLyrics"):
            return {"src": "lrclib.net", "plain": r.json().get("plainLyrics"), "synced": r.json().get("syncedLyrics")}
    except: pass
    try:
        r = requests.get("https://lrclib.net/api/search", params={"q": f"{artist} {track}"}, timeout=10)
        if r.ok and r.json() and r.json()[0].get("plainLyrics"):
            j = r.json()[0]
            return {"src": "lrclib.net", "plain": j.get("plainLyrics"), "synced": j.get("syncedLyrics")}
    except: pass
    try:
        url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(artist)}/{urllib.parse.quote(track)}"
        r = requests.get(url, timeout=10)
        if r.ok and r.json().get("lyrics"):
            return {"src": "lyrics.ovh", "plain": r.json()["lyrics"], "synced": None}
    except: pass
    return None

def download_audio(artist, track):
    import yt_dlp, os
    for f in glob.glob("/tmp/song.*"):
        try: os.remove(f)
        except: pass
    opts = {'format':'bestaudio[ext=m4a]/bestaudio','outtmpl':'/tmp/song.%(ext)s','noplaylist':True,'quiet':True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(f"ytsearch1:{artist} {track} audio", download=True)
        files = glob.glob("/tmp/song.*")
        return files[0] if files else None
    except: return None

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("v12 RENDER NO PROXY ✅\nSend: bahagia lagi")

async def search_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()
    if len(q) < 2: return
    results = await asyncio.to_thread(search_music, q)
    if not results:
        await update.message.reply_text("No results")
        return
    buttons = []; msg = f"Found {len(results)}:\n"
    for r in results:
        artist = r.get("artistName","").strip(); track = r.get("trackName","").strip()
        msg += f"• {artist} - {track}\n"
        buttons.append([InlineKeyboardButton(f"▶️ {artist} - {track}"[:60], callback_data=f"{artist[:20]}@@{track[:20]}")])
    await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(buttons))

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    print(f"TAPPED {q.data}")
    await q.answer(text="Loading...")
    artist, track = q.data.split("@@")
    await q.edit_message_text(f"⏳ Loading {artist.strip()} - {track.strip()}...")
    lrc = await asyncio.to_thread(get_lyrics, artist.strip(), track.strip())
    if lrc:
        await ctx.bot.send_message(chat_id=q.message.chat_id, text=f"✅ From {lrc['src']}:\n\n{lrc['plain'][:4000]}")
        if lrc.get("synced"):
            path = f"/tmp/{track}.lrc"
            open(path,"w",encoding="utf-8").write(lrc["synced"])
            await ctx.bot.send_document(chat_id=q.message.chat_id, document=open(path,"rb"), caption=f"LRC {lrc['src']}")
    else:
        await ctx.bot.send_message(chat_id=q.message.chat_id, text="❌ Lyrics not found on both servers")
    apath = await asyncio.to_thread(download_audio, artist.strip(), track.strip())
    if apath:
        await ctx.bot.send_audio(chat_id=q.message.chat_id, audio=open(apath,"rb"), title=track, performer=artist)

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler))
print("v12 RENDER - NO PROXY")
app.run_polling()
