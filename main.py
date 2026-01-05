import os
import json
import zipfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = 22852603        # <-- your api id
API_HASH = "505a27a08aac31787f203120dcbc255c"  # <-- your api hash
BOT_TOKEN = "8242910847:AAEtjFQl5dBwswCHonJ4k4F3MECcgtMEa-A"

app = Client(
    "insta_unfollowers_detector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

STATE = {}  # chat_id -> {"followers": set(), "following": set()}

# ---------------- HELP ----------------
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "👋 **Instagram Unfollowers Detector**\n\n"
        "📂 Upload:\n"
        "• Instagram ZIP export\n"
        "• followers.json\n"
        "• following.json\n\n"
        "🤖 Auto-detect enabled\n"
        "➡️ Then use /unfollowers"
    )

# ---------------- FILE HANDLER ----------------
@app.on_message(filters.document)
async def handle_file(_, m: Message):
    chat_id = m.chat.id
    STATE[chat_id] = {"followers": set(), "following": set()}

    await m.reply("⏳ Processing file...")

    path = await m.download(file_name=f"{DATA_DIR}/{m.document.file_name}")

    try:
        if path.endswith(".zip"):
            process_zip(chat_id, path)
        elif path.endswith(".json"):
            process_json(chat_id, path)
        else:
            await m.reply("❌ Unsupported file format")
            return

        await m.reply("✅ File processed successfully")

    except Exception as e:
        await m.reply(f"❌ Error: {e}")

# ---------------- PROCESS ZIP ----------------
def process_zip(chat_id, zip_path):
    temp = f"{DATA_DIR}/temp_{chat_id}"
    shutil.rmtree(temp, ignore_errors=True)
    os.makedirs(temp)

    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(temp)

    base = os.path.join(
        temp, "connections", "followers_and_following"
    )

    followers_path = os.path.join(base, "followers_1.json")
    following_path = os.path.join(base, "following.json")

    if os.path.exists(followers_path):
        process_json(chat_id, followers_path)

    if os.path.exists(following_path):
        process_json(chat_id, following_path)

    shutil.rmtree(temp, ignore_errors=True)

# ---------------- PROCESS JSON ----------------
def process_json(chat_id, json_path):
    data = json.load(open(json_path))

    # followers_*.json → LIST
    if isinstance(data, list):
        for item in data:
            sld = item.get("string_list_data", [])
            if sld and "value" in sld[0]:
                STATE[chat_id]["followers"].add(sld[0]["value"])

    # following.json → DICT
    elif isinstance(data, dict):
        items = data.get("relationships_following", [])
        for item in items:
            if "title" in item:
                STATE[chat_id]["following"].add(item["title"])

# ---------------- UNFOLLOWERS ----------------
@app.on_message(filters.command("unfollowers"))
async def unfollowers(_, m: Message):
    chat_id = m.chat.id
    if chat_id not in STATE:
        return await m.reply("❌ Upload files first")

    followers = STATE[chat_id]["followers"]
    following = STATE[chat_id]["following"]

    if not followers or not following:
        return await m.reply(
            "❌ Missing data\n"
            "Upload Instagram ZIP or both followers & following files"
        )

    unf = sorted(following - followers)

    if not unf:
        return await m.reply("🎉 No unfollowers found!")

    text = "🚫 **Unfollowers List**\n\n"
    for u in unf:
        text += f"• [{u}](https://www.instagram.com/{u}/)\n"

    await m.reply(text, disable_web_page_preview=True)

# ---------------- RUN ----------------
print("🤖 Instagram Unfollowers Bot running...")
app.run()
