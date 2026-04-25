import json
import os

DB_PATH = os.path.expanduser('~/v2ray_manager/users_db.json')

# --- دوال التعامل مع الملف ---
def load_db():
    if not os.path.exists(DB_PATH):
        return {}
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return {}

def update_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

# --- دالة الحفظ مع دعم وقت الانتهاء ---
def save_user(email, uuid, limit_bytes, expiry_time):
    data = load_db()
    # يتم حفظ البيانات كـ كائن يحتوي على كل التفاصيل
    data[email] = {
        'uuid': uuid, 
        'limit_bytes': limit_bytes, 
        'used_bytes': 0, 
        'expiry_time': expiry_time, # وقت الانتهاء بنظام Timestamp
        'is_active': True
    }
    update_db(data)

# --- دالة التجديد (تمديد الوقت والسعة) ---
def renew_user(email, extra_bytes, new_expiry):
    data = load_db()
    if email in data:
        # تصفير الاستهلاك القديم أو إضافة سعة جديدة
        data[email]['limit_bytes'] = extra_bytes
        data[email]['expiry_time'] = new_expiry
        data[email]['is_active'] = True
        # ملاحظة: لا نصفر used_bytes إلا إذا أردت بدء الحساب من الصفر
        data[email]['used_bytes'] = 0 
        update_db(data)
        return True
    return False

# ==========================================
# 2. كائن (db) لضمان التوافق مع بقية ملفات البوت
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

# إنشاء الكائن لاستخدامه في الملفات الأخرى
db = DummyDB()
