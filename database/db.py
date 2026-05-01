import sqlite3
import datetime
import os

# تحديد مسار قاعدة البيانات ليكون دائم وما يضيع
home_dir = os.path.expanduser("~")
DB_PATH = f'{home_dir}/v2ray_manager/bot_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # جدول المشتركين
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, uuid TEXT, port INTEGER, quota_bytes REAL, expiry_date TEXT, status TEXT)''')
    # جدول الاستهلاك اليومي
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage
                 (email TEXT, date TEXT, total_used REAL)''')
    conn.commit()
    conn.close()

def add_user(email, uuid, port, quota_bytes, expiry_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # نحفظ الوقت كنص (String) حتى ما يصير بي مشاكل
    c.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?, ?)", 
              (email, uuid, port, quota_bytes, str(expiry_date), 'active'))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

# ==========================================
# 🔥 هذي هي الدوال الناقصة اللي خلت البوت يوكف 🔥
# ==========================================

# دالة لجلب المشتركين الفعالين فقط لفحص وقتهم
def get_active_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, uuid, expiry_date FROM users WHERE status='active'")
    users = c.fetchall()
    conn.close()
    return users

# دالة لتحويل حالة المشترك إلى منتهي (مطرود)
def set_user_expired(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET status='expired' WHERE email=?", (email,))
    conn.commit()
    conn.close()

# ==========================================

def log_daily_usage(email, total_used_bytes):
    today = str(datetime.date.today())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO daily_usage VALUES (?, ?, ?)", (email, today, total_used_bytes))
    conn.commit()
    conn.close()

def get_usage_stats(email, current_total_used):
    # دالة تحسب استهلاك اليوم والبارحة بناءً على السجلات
    today = str(datetime.date.today())
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    c.execute("SELECT total_used FROM daily_usage WHERE email=? AND date=?", (email, yesterday))
    y_data = c.fetchone()
    used_yesterday_total = y_data[0] if y_data else 0
    
    # صرف اليوم = الاستهلاك الكلي الحالي - الاستهلاك الكلي لحد البارحة
    used_today = current_total_used - used_yesterday_total if current_total_used > used_yesterday_total else current_total_used
    
    conn.close()
    return used_today, used_yesterday_total
