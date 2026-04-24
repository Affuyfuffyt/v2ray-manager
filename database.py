import json
import os

DB_PATH = os.path.expanduser('~/v2ray_manager/users_db.json')

# ==========================================
# 1. دوال نظام الطرد التكتيكي (Anti-Share)
# ==========================================
def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_user(email, uuid, limit):
    data = load_db()
    # حفظ بيانات المشترك مع عدد أجهزته وحالة الحظر
    data[email] = {'uuid': uuid, 'limit': limit, 'banned_until': 0}
    update_db(data)

def update_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

# ==========================================
# 2. كائن (db) لحل مشكلة الإيرور في البوت
# ==========================================
class DummyDB:
    def init_db(self):
        pass
        
    def get_all_users(self):
        return list(load_db().keys())
        
    def log_daily_usage(self, email, usage):
        pass
        
    def get_user(self, email):
        return load_db().get(email)
        
    def delete_user(self, email):
        data = load_db()
        if email in data:
            del data[email]
            update_db(data)

# إنشاء الكائن حتى يقرأه البوت بدون مشاكل
db = DummyDB()
