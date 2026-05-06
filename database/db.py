import json
import os
import time

# مسار ملف JSON
def get_db_path():
    home_dir = os.path.expanduser("~")
    # البحث عن اسم ملف البيانات القديم (حتى نتأكد من مساره)
    for json_name in ["database.json", "data.json", "users.json"]:
        json_path = os.path.join(home_dir, "v2ray_manager", json_name)
        if os.path.exists(json_path):
            return json_path
    # إذا ما لكاه، يرجع الافتراضي
    return os.path.join(home_dir, "v2ray_manager", "database.json")

def load_db():
    db_path = get_db_path()
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def update_db(data):
    db_path = get_db_path()
    try:
        with open(db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving DB: {e}")

def save_user(email, uuid_val, quota_bytes, expiry_time):
    db_data = load_db()
    db_data[email] = {
        'uuid': uuid_val,
        'limit_bytes': quota_bytes,
        'expiry_time': expiry_time,
        'used_bytes': 0,
        'is_active': True,
        'created_at': time.time()
    }
    update_db(db_data)

# 🔥 هاي الدالة السحرية الجديدة اللي راح تخلي التمديد يظهر بلوحة التفاصيل 🔥
def extend_json_expiry(email, extra_seconds):
    db_data = load_db()
    if email in db_data:
        # نبحث عن حقل الوقت الصحيح ونحدثه
        for key in ['expiry_time', 'expiry_date', 'expiry']:
            if key in db_data[email]:
                current_val = float(db_data[email][key])
                db_data[email][key] = current_val + extra_seconds
                db_data[email]['is_active'] = True # نرجع نفعله إذا كان طافي
                update_db(db_data)
                return True
    return False
