import os
import json
import zipfile
import shutil
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = 22852603          # <-- your api_id
API_HASH = "505a27a08aac31787f203120dcbc255c"    # <-- your api_hash
BOT_TOKEN = "8242910847:AAEtjFQl5dBwswCHonJ4k4F3MECcgtMEa-A"  # <-- your bot token

app = Client(
    "insta_unfollowers_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

BASE_DIR = "user_data"
os.makedirs(BASE_DIR, exist_ok=True)

# ---------------- UTILS ----------------

def user_dir(uid):
    path = f"{BASE_DIR}/{uid}"
    os.makedirs(path, exist_ok=True)
    return path

def extract_zip(zip_path, out_dir):
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(out_dir)

def find_json_files(root):
    files = []
    for r, _, f in os.walk(root):
        for x in f:
            if x.endswith(".json"):
                files.append(os.path.join(r, x))
    return files

def parse_instagram_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    users = set()

    # Instagram export formats
    if isinstance(data, dict) and "relationships_followers" in path:
        data = data.get("relationships_followers", [])
    elif isinstance(data, dict) and "relationships_following" in path:
        data = data.get("relationships_following", [])

    for item in data:
        try:
            users.add(item["string_list_data"][0]["value"])
        except:
            pass

    return users

# ---------------- START ----------------

@app.on_message(filters.command("start"))
async def start(_, m: Message):
    await m.reply(
        "👋 **Instagram Unfollowers Detector**\n\n"
        "📦 Upload any of these:\n"
        "• Instagram ZIP export\n"
        "• followers.json\n"
        "• following.json\n\n"
        "🤖 Bot auto-detects everything\n"
        "📌 Then use /unfollowers",
        disable_web_page_preview=True
    )

# ---------------- FILE HANDLER ----------------

@app.on_message(filters.document)
async def handle_file(_, m: Message):
    uid = m.from_user.id
    udir = user_dir(uid)

    await m.reply("⏳ Processing file...")

    file_path = await m.download(file_name=f"{udir}/{m.document.file_name}")

    followers = set()
    following = set()

    try:
        # ZIP
        if file_path.endswith(".zip"):
            extract_dir = f"{udir}/zip"
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)

            extract_zip(file_path, extract_dir)
            json_files = find_json_files(extract_dir)

            for jf in json_files:
                lname = jf.lower()
                if "followers" in lname:
                    followers |= parse_instagram_json(jf)
                elif "following" in lname:
                    following |= parse_instagram_json(jf)

        # JSON
        elif file_path.endswith(".json"):
            lname = file_path.lower()
            if "followers" in lname:
                followers = parse_instagram_json(file_path)
            elif "following" in lname:
                following = parse_instagram_json(file_path)

        # Save
        if followers:
            json.dump(list(followers), open(f"{udir}/followers.json", "w"))
        if following:
            json.dump(list(following), open(f"{udir}/following.json", "w"))

        await m.reply("✅ File processed successfully")

    except Exception as e:
        await m.reply(f"❌ Error processing file: {e}")

# ---------------- UNFOLLOWERS ----------------

@app.on_message(filters.command("unfollowers"))
async def unfollowers(_, m: Message):
    uid = m.from_user.id
    udir = user_dir(uid)

    f1 = f"{udir}/followers.json"
    f2 = f"{udir}/following.json"

    if not os.path.exists(f1) or not os.path.exists(f2):
        return await m.reply(
            "❌ Missing data\n"
            "Upload **Instagram ZIP** or both followers & following files"
        )

    followers = set(json.load(open(f1)))
    following = set(json.load(open(f2)))

    unf = sorted(following - followers)

    if not unf:
        return await m.reply("✅ No unfollowers found")

    # -------- FILE --------
    out = f"{udir}/unfollowers.txt"
    with open(out, "w") as f:
        for u in unf:
            f.write(f"https://instagram.com/{u}\n")

    # -------- MESSAGE --------
    msg = f"🔻 <b>Unfollowers ({len(unf)})</b>\n\n"
    for u in unf[:20]:
        msg += f"• <a href='https://instagram.com/{u}'>@{u}</a>\n"

    if len(unf) > 20:
        msg += f"\n… and {len(unf)-20} more (see file)"

    await m.reply(msg, parse_mode="html", disable_web_page_preview=True)
    await m.reply_document(out)

# ---------------- RUN ----------------

print("🤖 Instagram Unfollowers Bot running...")
app.run()
