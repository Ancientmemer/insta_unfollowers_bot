import os
import json
import zipfile
import csv
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message

# ============ CONFIG ============
API_ID = 22852603
API_HASH = "505a27a08aac31787f203120dcbc255c"
BOT_TOKEN = "8242910847:AAEtjFQl5dBwswCHonJ4k4F3MECcgtMEa-A"

BASE = os.getcwd()
DOWNLOAD_DIR = os.path.join(BASE, "downloads")
TEMP_DIR = os.path.join(BASE, "temp")
EXPORT_DIR = os.path.join(BASE, "exports")

for d in (DOWNLOAD_DIR, TEMP_DIR, EXPORT_DIR):
    os.makedirs(d, exist_ok=True)

app = Client(
    "ig_unfollowers_detector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

USER_DATA = {}  # chat_id -> {"followers": set(), "following": set()}

# ============ HELPERS ============
def clean_temp():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

def extract_instagram_json(path):
    """
    Instagram followers/following JSON parser
    """
    usernames = set()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        for item in data:
            for s in item.get("string_list_data", []):
                if "value" in s:
                    usernames.add(s["value"])
    return usernames

def extract_csv(path):
    users = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if row and row[0]:
                users.add(row[0].strip())
    return users

def process_zip(chat_id, zip_path):
    clean_temp()
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(TEMP_DIR)

    followers = set()
    following = set()

    for root, _, files in os.walk(TEMP_DIR):
        for f in files:
            fp = os.path.join(root, f)
            name = f.lower()

            try:
                if f.endswith(".json"):
                    users = extract_instagram_json(fp)
                    if "follower" in name:
                        followers |= users
                    elif "following" in name:
                        following |= users

                elif f.endswith(".csv"):
                    users = extract_csv(fp)
                    if "follower" in name:
                        followers |= users
                    elif "following" in name:
                        following |= users
            except:
                pass

    if followers:
        USER_DATA.setdefault(chat_id, {})["followers"] = followers
    if following:
        USER_DATA.setdefault(chat_id, {})["following"] = following

# ============ COMMANDS ============
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "👋 **Instagram Unfollowers Detector**\n\n"
        "📤 Upload **Instagram ZIP export**\n"
        "or followers.json / following.json\n\n"
        "🤖 Auto-detect enabled\n"
        "📄 Then use /unfollowers"
    )

@app.on_message(filters.document)
async def file_handler(_, m: Message):
    chat_id = m.chat.id
    path = await m.download(file_name=DOWNLOAD_DIR)

    try:
        if path.endswith(".zip"):
            process_zip(chat_id, path)
        elif path.endswith(".json"):
            users = extract_instagram_json(path)
            key = "following" if "following" in path.lower() else "followers"
            USER_DATA.setdefault(chat_id, {})[key] = users
        elif path.endswith(".csv"):
            users = extract_csv(path)
            key = "following" if "following" in path.lower() else "followers"
            USER_DATA.setdefault(chat_id, {})[key] = users

        await m.reply("✅ File processed successfully")

    except Exception as e:
        await m.reply(f"⚠️ Error: `{e}`")

@app.on_message(filters.command("unfollowers"))
async def unfollowers(_, m: Message):
    chat_id = m.chat.id
    data = USER_DATA.get(chat_id, {})

    if not data.get("followers") or not data.get("following"):
        return await m.reply(
            "❌ Missing data\n"
            "Upload Instagram ZIP or both files"
        )

    unf = sorted(data["following"] - data["followers"])

    if not unf:
        return await m.reply("🎉 No unfollowers found")

    out = os.path.join(EXPORT_DIR, f"unfollowers_{chat_id}.txt")
    with open(out, "w") as f:
        for u in unf:
            f.write(u + "\n")

    await m.reply_document(out, caption=f"🚫 Unfollowers: {len(unf)}")

@app.on_message(filters.command("reset"))
async def reset(_, m: Message):
    USER_DATA.pop(m.chat.id, None)
    await m.reply("♻️ Reset done. Upload files again.")

print("🤖 Instagram Unfollowers Bot running...")
app.run()
