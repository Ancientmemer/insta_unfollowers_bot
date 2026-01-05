import os, json, zipfile, csv, shutil
from pyrogram import Client, filters
from config import *

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Client(
    "json_unfollowers_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# per-user temp storage
user_data = {}

# ---------------- START ----------------
@app.on_message(filters.command("start") & filters.private)
async def start(_, m):
    uid = m.from_user.id
    user_data[uid] = {
        "followers": set(),
        "following": set()
    }
    await m.reply(
        "👋 Hi!\n\n"
        "📤 Upload **ANY** of these:\n"
        "• followers.json\n"
        "• following.json\n"
        "• Instagram ZIP export\n"
        "• CSV files\n\n"
        "🤖 Bot will auto-detect everything."
    )

# ---------------- FILE HANDLER ----------------
@app.on_message(filters.document & filters.private)
async def handle_file(_, m):
    uid = m.from_user.id
    if uid not in user_data:
        return await m.reply("❌ Send /start first")

    file_name = m.document.file_name.lower()
    base_path = f"{UPLOAD_DIR}/{uid}"
    os.makedirs(base_path, exist_ok=True)

    file_path = f"{base_path}/{file_name}"
    await m.download(file_path)

    try:
        if file_name.endswith(".zip"):
            await handle_zip(uid, file_path)
        elif file_name.endswith(".json"):
            handle_json(uid, file_path)
        elif file_name.endswith(".csv"):
            handle_csv(uid, file_path)
        else:
            return await m.reply("❌ Unsupported file type")

        await maybe_finish(uid, m)

    except Exception as e:
        await m.reply(f"⚠️ Error processing file: {e}")

# ---------------- ZIP HANDLER ----------------
async def handle_zip(uid, zip_path):
    extract_dir = zip_path.replace(".zip", "")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)

    for root, _, files in os.walk(extract_dir):
        for f in files:
            p = os.path.join(root, f)
            lf = f.lower()
            if lf.endswith(".json"):
                handle_json(uid, p)
            elif lf.endswith(".csv"):
                handle_csv(uid, p)

# ---------------- JSON HANDLER ----------------
def handle_json(uid, path):
    data = json.load(open(path, encoding="utf-8"))
    usernames = extract_usernames(data)

    key = detect_type(path, usernames)
    user_data[uid][key].update(usernames)

# ---------------- CSV HANDLER ----------------
def handle_csv(uid, path):
    usernames = set()
    with open(path, newline='', encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            for cell in row:
                if cell and "@" not in cell:
                    usernames.add(cell.strip())
    key = detect_type(path, usernames)
    user_data[uid][key].update(usernames)

# ---------------- TYPE DETECTION ----------------
def detect_type(path, usernames):
    name = path.lower()

    if "following" in name:
        return "following"
    if "follower" in name:
        return "followers"

    # heuristic fallback
    if len(usernames) > 0:
        return "following"
    return "followers"

# ---------------- USERNAME EXTRACT ----------------
def extract_usernames(data):
    result = set()

    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                if "username" in item:
                    result.add(item["username"])
                elif "string_list_data" in item:
                    result.add(item["string_list_data"][0]["value"])

    elif isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        if "username" in item:
                            result.add(item["username"])
                        elif "string_list_data" in item:
                            result.add(item["string_list_data"][0]["value"])

    return result

# ---------------- FINISH CHECK ----------------
async def maybe_finish(uid, m):
    f1 = user_data[uid]["followers"]
    f2 = user_data[uid]["following"]

    if not f1 or not f2:
        await m.reply("📥 File processed. Waiting for more files…")
        return

    unfollowers = sorted(f2 - f1)

    out = f"{UPLOAD_DIR}/{uid}_unfollowers.txt"
    with open(out, "w") as f:
        for u in unfollowers:
            f.write(u + "\n")

    await m.reply_document(
        out,
        caption=f"✅ Unfollowers found: {len(unfollowers)}"
    )

    # cleanup
    shutil.rmtree(f"{UPLOAD_DIR}/{uid}", ignore_errors=True)
    user_data.pop(uid, None)

# ---------------- RUN ----------------
print("🤖 Auto-Detect Unfollowers Bot running...")
app.run()
