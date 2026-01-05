import os
import json
import zipfile
import csv
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message

# ================= CONFIG =================
API_ID = "API_ID"        # <-- your api id
API_HASH = "API_HASH"  # <-- your api hash
BOT_TOKEN = "BOT_TOKEN"

DOWNLOAD_DIR = "downloads"
TEMP_DIR = "temp"
EXPORT_DIR = "exports"

os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

app = Client(
    "instagram_unfollowers_detector",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# ================= STATE =================
USER_DATA = {}  # chat_id -> {"followers": set(), "following": set()}

# ================= UTILS =================
def clean_temp():
    shutil.rmtree(TEMP_DIR, ignore_errors=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

def extract_usernames(data):
    usernames = set()

    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k == "string_list_data" and isinstance(v, list):
                    for i in v:
                        if isinstance(i, dict) and "value" in i:
                            usernames.add(i["value"])
                elif k == "username" and isinstance(v, str):
                    usernames.add(v)
                else:
                    walk(v)
        elif isinstance(obj, list):
            for i in obj:
                walk(i)

    walk(data)
    return usernames

def read_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def read_csv(path):
    usernames = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                usernames.add(row[0].strip())
    return usernames

def detect_type(filename, usernames):
    name = filename.lower()
    if "following" in name:
        return "following"
    if "follower" in name:
        return "followers"
    # fallback
    return "followers" if len(usernames) < 2000 else "following"

def process_file(chat_id, path):
    ext = path.lower()

    if ext.endswith(".json"):
        data = read_json(path)
        users = extract_usernames(data)
        t = detect_type(path, users)
        USER_DATA.setdefault(chat_id, {})[t] = users

    elif ext.endswith(".csv"):
        users = read_csv(path)
        t = detect_type(path, users)
        USER_DATA.setdefault(chat_id, {})[t] = users

    elif ext.endswith(".zip"):
        with zipfile.ZipFile(path, "r") as z:
            z.extractall(TEMP_DIR)

        for root, _, files in os.walk(TEMP_DIR):
            for f in files:
                fp = os.path.join(root, f)
                if f.endswith(".json"):
                    try:
                        data = read_json(fp)
                        users = extract_usernames(data)
                        t = detect_type(f, users)
                        USER_DATA.setdefault(chat_id, {})[t] = users
                    except:
                        pass
                elif f.endswith(".csv"):
                    users = read_csv(fp)
                    t = detect_type(f, users)
                    USER_DATA.setdefault(chat_id, {})[t] = users

# ================= COMMANDS =================
@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "👋 **Instagram Unfollowers Detector**\n\n"
        "📤 Upload ANY of these:\n"
        "• followers.json\n"
        "• following.json\n"
        "• Instagram ZIP export\n"
        "• CSV files\n\n"
        "🤖 Bot auto-detects everything.\n"
        "📄 After upload, use /unfollowers"
    )

@app.on_message(filters.document)
async def handle_file(_, m: Message):
    chat_id = m.chat.id
    clean_temp()

    path = await m.download(file_name=DOWNLOAD_DIR)
    try:
        process_file(chat_id, path)
        await m.reply("✅ File processed successfully")
    except Exception as e:
        await m.reply(f"⚠️ Error processing file: `{e}`")

@app.on_message(filters.command("unfollowers"))
async def unfollowers(_, m: Message):
    chat_id = m.chat.id
    data = USER_DATA.get(chat_id)

    if not data or "followers" not in data or "following" not in data:
        return await m.reply(
            "❌ Missing data\n"
            "Upload BOTH followers & following files"
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
    await m.reply("♻️ Data reset. Upload files again.")

# ================= RUN =================
print("🤖 Instagram Unfollowers Bot running...")
app.run()
