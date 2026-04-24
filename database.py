import json
import os

DB_PATH = os.path.expanduser('~/v2ray_manager/users_db.json')

def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_user(email, uuid, limit):
    db = load_db()
    # حفظ بيانات المشترك مع عدد أجهزته وحالة الحظر
    db[email] = {'uuid': uuid, 'limit': limit, 'banned_until': 0}
    update_db(db)

def update_db(db):
    with open(DB_PATH, 'w') as f:
        json.dump(db, f, indent=2)
