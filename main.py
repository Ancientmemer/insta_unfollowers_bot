import os, json, zipfile, shutil
from pyrogram import Client, filters
from pyrogram.types import Message

API_ID = 22852603
API_HASH = "505a27a08aac31787f203120dcbc255c"
BOT_TOKEN = "8242910847:AAEtjFQl5dBwswCHonJ4k4F3MECcgtMEa-A"

app = Client("insta_unfollowers_bot",
             api_id=API_ID,
             api_hash=API_HASH,
             bot_token=BOT_TOKEN)

BASE = "user_data"
os.makedirs(BASE, exist_ok=True)

# ---------------- UTILS ----------------

def udir(uid):
    path = f"{BASE}/{uid}"
    os.makedirs(path, exist_ok=True)
    return path

def extract(zipf, out):
    with zipfile.ZipFile(zipf, "r") as z:
        z.extractall(out)

def find_all_json(root):
    res = []
    for r, _, f in os.walk(root):
        for x in f:
            if x.endswith(".json"):
                res.append(os.path.join(r, x))
    return res

def parse_followers(path):
    users = set()
    data = json.load(open(path, encoding="utf-8"))

    for item in data:
        try:
            users.add(item["string_list_data"][0]["value"])
        except:
            pass
    return users

def parse_following(path):
    users = set()
    data = json.load(open(path, encoding="utf-8"))

    for item in data.get("relationships_following", []):
        try:
            users.add(item["string_list_data"][0]["value"])
        except:
            pass
    return users

# ---------------- START ----------------

@app.on_message(filters.command("start"))
async def start(_, m):
    await m.reply(
        "👋 **Instagram Unfollowers Detector**\n\n"
        "📦 Upload **Instagram ZIP export**\n"
        "🤖 Bot auto-detects followers & following\n\n"
        "📌 Then use /unfollowers",
        disable_web_page_preview=True
    )

# ---------------- FILE HANDLER ----------------

@app.on_message(filters.document)
async def file_handler(_, m: Message):
    uid = m.from_user.id
    ud = udir(uid)

    await m.reply("⏳ Processing Instagram export...")

    file = await m.download(file_name=f"{ud}/{m.document.file_name}")

    followers, following = set(), set()

    try:
        if file.endswith(".zip"):
            ext = f"{ud}/extract"
            if os.path.exists(ext):
                shutil.rmtree(ext)
            os.makedirs(ext)

            extract(file, ext)
            jsons = find_all_json(ext)

            for jf in jsons:
                name = jf.lower()
                if "followers_" in name:
                    followers |= parse_followers(jf)
                elif "following.json" in name:
                    following |= parse_following(jf)

        if not followers or not following:
            return await m.reply(
                "❌ Could not detect followers/following\n"
                "Make sure this is **official Instagram ZIP export**"
            )

        json.dump(list(followers), open(f"{ud}/followers.json", "w"))
        json.dump(list(following), open(f"{ud}/following.json", "w"))

        await m.reply(
            f"✅ Data loaded successfully\n\n"
            f"👥 Followers: {len(followers)}\n"
            f"➡️ Following: {len(following)}\n\n"
            "📌 Now use /unfollowers"
        )

    except Exception as e:
        await m.reply(f"❌ Error: {e}")

# ---------------- UNFOLLOWERS ----------------

@app.on_message(filters.command("unfollowers"))
async def unf(_, m):
    uid = m.from_user.id
    ud = udir(uid)

    f1 = f"{ud}/followers.json"
    f2 = f"{ud}/following.json"

    if not os.path.exists(f1) or not os.path.exists(f2):
        return await m.reply("❌ Upload Instagram ZIP first")

    followers = set(json.load(open(f1)))
    following = set(json.load(open(f2)))

    unf = sorted(following - followers)

    if not unf:
        return await m.reply("✅ No unfollowers found")

    out = f"{ud}/unfollowers.txt"
    with open(out, "w") as f:
        for u in unf:
            f.write(f"https://instagram.com/{u}\n")

    msg = f"🔻 <b>Unfollowers ({len(unf)})</b>\n\n"
    for u in unf[:20]:
        msg += f"• <a href='https://instagram.com/{u}'>@{u}</a>\n"

    if len(unf) > 20:
        msg += f"\n… and {len(unf)-20} more"

    await m.reply(msg, parse_mode="html", disable_web_page_preview=True)
    await m.reply_document(out)

# ---------------- RUN ----------------

print("🤖 Bot running...")
app.run()
