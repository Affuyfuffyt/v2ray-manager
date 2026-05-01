import json
import os
import sqlite3
import datetime

# تحديد مسارات قواعد البيانات (الـ JSON والـ SQLite)
home_dir = os.path.expanduser('~')
JSON_DB_PATH = f'{home_dir}/v2ray_manager/users_db.json'
SQLITE_DB_PATH = f'{home_dir}/v2ray_manager/bot_data.db'

# ==========================================
# 1️⃣ قسم قاعدة بيانات JSON (لضمان عمل أزرار البوت القديمة)
# ==========================================
def load_db():
    if not os.path.exists(JSON_DB_PATH):
        return {}
    try:
        with open(JSON_DB_PATH, 'r') as f:
            return json.load(f)
    except:
        return {}

def update_db(data):
    with open(JSON_DB_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def save_user(email, uuid, limit_bytes, expiry_time):
    data = load_db()
    data[email] = {
        'uuid': uuid, 
        'limit_bytes': limit_bytes, 
        'used_bytes': 0, 
        'expiry_time': expiry_time, 
        'is_active': True
    }
    update_db(data)

def renew_user(email, extra_bytes, new_expiry):
    data = load_db()
    if email in data:
        data[email]['limit_bytes'] = extra_bytes
        data[email]['expiry_time'] = new_expiry
        data[email]['is_active'] = True
        data[email]['used_bytes'] = 0 
        update_db(data)
        return True
    return False


# ==========================================
# 2️⃣ قسم قاعدة بيانات SQLite (لعمل المراقب الذكي والطرد التلقائي)
# ==========================================
def init_sqlite_db():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, uuid TEXT, port INTEGER, quota_bytes REAL, expiry_date TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage
                 (email TEXT, date TEXT, total_used REAL)''')
    conn.commit()
    conn.close()

def add_user(email, uuid, port, quota_bytes, expiry_date):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)", 
              (email, uuid, port, quota_bytes, str(expiry_date), 'active'))
    conn.commit()
    conn.close()

def get_active_users():
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, uuid, expiry_date FROM users WHERE status='active'")
    users = c.fetchall()
    conn.close()
    return users

def set_user_expired(email):
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET status='expired' WHERE email=?", (email,))
    conn.commit()
    conn.close()

# --- دوال الإحصائيات (مدمجة) ---
def log_daily_usage(email, total_used_bytes):
    today = str(datetime.date.today())
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO daily_usage VALUES (?, ?, ?)", (email, today, total_used_bytes))
    conn.commit()
    conn.close()

def get_usage_stats(email, current_total_used):
    today = str(datetime.date.today())
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    conn = sqlite3.connect(SQLITE_DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_used FROM daily_usage WHERE email=? AND date=?", (email, yesterday))
    y_data = c.fetchone()
    used_yesterday_total = y_data[0] if y_data else 0
    used_today = current_total_used - used_yesterday_total if current_total_used > used_yesterday_total else current_total_used
    conn.close()
    return used_today, used_yesterday_total


# ==========================================
# 3️⃣ كائن (db) لضمان التوافق مع بقية ملفات البوت
# ==========================================
class DummyDB:
    def init_db(self):
        init_sqlite_db() # إنشاء جداول SQLite تلقائياً
        
    def get_all_users(self):
        return list(load_db().keys())
        
    def log_daily_usage_obj(self, email, usage):
        log_daily_usage(email, usage)
        
    def get_user(self, email):
        return load_db().get(email)
        
    def delete_user(self, email):
        # يمسح المشترك من الـ JSON
        data = load_db()
        if email in data:
            del data[email]
            update_db(data)
        
        # يمسح المشترك من الـ SQLite
        try:
            conn = sqlite3.connect(SQLITE_DB_PATH)
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE email=?", (email,))
            conn.commit()
            conn.close()
        except:
            pass

# إنشاء الكائن وتفعيل القواعد عند التشغيل
db = DummyDB()
db.init_db()
