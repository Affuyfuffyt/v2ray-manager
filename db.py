import sqlite3
import datetime
import os

# تحديد مسار قاعدة البيانات ليكون دائم وما يضيع
home_dir = os.path.expanduser("~")
DB_PATH = f'{home_dir}/v2ray_manager/bot_data.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 1. جدول المشتركين (الأساسي)
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (email TEXT PRIMARY KEY, uuid TEXT, port INTEGER, quota_bytes REAL, expiry_date TEXT, status TEXT)''')
                 
    # 2. جدول الاستهلاك اليومي للبيانات (بايتات)
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage
                 (email TEXT, date TEXT, total_used REAL)''')
                 
    # 🔥 تحديثات الرادار (آخر ظهور + الوقت الكلي بالثواني)
    try:
        c.execute("ALTER TABLE users ADD COLUMN last_seen TEXT")
    except:
        pass 
    try:
        c.execute("ALTER TABLE users ADD COLUMN total_connection_seconds REAL DEFAULT 0")
    except:
        pass 

    # 🔥 تحديث نظام الدعوات (كود الدعوة الخاص بالمشترك)
    try:
        c.execute("ALTER TABLE users ADD COLUMN ref_code TEXT")
    except:
        pass

    # 3. جدول أرشيف وقت الاتصال اليومي (للرادار الشامل)
    c.execute('''CREATE TABLE IF NOT EXISTS daily_connection
                 (email TEXT, date TEXT, connection_seconds REAL, PRIMARY KEY (email, date))''')

    # 🔥 4. الجدول الجديد للمكافآت المعلقة (النظام الذكي) 🔥
    # يحفظ: إيميل الداعي، إيميل المدعو الجديد، قيمة المكافأة، وتات الأدمين لإخطاره
    c.execute('''CREATE TABLE IF NOT EXISTS pending_rewards
                 (referrer_email TEXT, invited_email TEXT, reward_seconds REAL, chat_id TEXT)''')

    conn.commit()
    conn.close()

def add_user(email, uuid, port, quota_bytes, expiry_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE email=?", (email,))
    if c.fetchone():
        c.execute("UPDATE users SET uuid=?, port=?, quota_bytes=?, expiry_date=?, status='active' WHERE email=?",
                  (uuid, port, quota_bytes, str(expiry_date), email))
    else:
        c.execute("INSERT INTO users (email, uuid, port, quota_bytes, expiry_date, status, last_seen, total_connection_seconds, ref_code) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, NULL)", 
                  (email, uuid, port, quota_bytes, str(expiry_date), 'active'))
    conn.commit()
    conn.close()

# ==========================================
# 🎁 دوال نظام الدعوات والمكافآت 🎁
# ==========================================

def assign_ref_code(email, ref_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET ref_code=? WHERE email=?", (ref_code, email))
    conn.commit()
    conn.close()

def get_user_by_ref_code(ref_code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, expiry_date FROM users WHERE ref_code=?", (ref_code,))
    data = c.fetchone()
    conn.close()
    return data

def extend_user_expiry(email, extra_seconds):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT expiry_date FROM users WHERE email=?", (email,))
    data = c.fetchone()
    if data and data[0]:
        current_expiry = float(data[0])
        new_expiry = current_expiry + extra_seconds
        c.execute("UPDATE users SET expiry_date=?, status='active' WHERE email=?", (str(new_expiry), email))
        conn.commit()
        conn.close()
        return new_expiry
    return None

# ==========================================
# ⏳ دوال المكافآت المعلقة (Referral Fraud Protection) ⏳
# ==========================================

# إضافة مكافأة للانتظار (تتنفذ من يكنك المدعو دقيقة)
def add_pending_reward(referrer, invited, seconds, chat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO pending_rewards VALUES (?, ?, ?, ?)", (referrer, invited, seconds, str(chat_id)))
    conn.commit()
    conn.close()

# جلب كل المكافآت اللي ننتظر تفعيلها
def get_all_pending_rewards():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT referrer_email, invited_email, reward_seconds, chat_id FROM pending_rewards")
    rows = c.fetchall()
    conn.close()
    return rows

# حذف مكافأة بعد ما نفذناها
def remove_pending_reward(invited_email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM pending_rewards WHERE invited_email=?", (invited_email,))
    conn.commit()
    conn.close()

# دالة ذكية لمعرفة كم ثانية كنك المشترك (للمقارنة بالشرط: دقيقة واحدة)
def get_user_connection_seconds(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_connection_seconds FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 0

# ==========================================
# 📡 دوال الرادار (اللوحة الشاملة) 📡
# ==========================================

def update_radar_data(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_str = str(datetime.date.today())
    c.execute("UPDATE users SET last_seen=?, total_connection_seconds = COALESCE(total_connection_seconds, 0) + 60 WHERE email=?", (now_str, email))
    c.execute("INSERT INTO daily_connection (email, date, connection_seconds) VALUES (?, ?, 60) ON CONFLICT(email, date) DO UPDATE SET connection_seconds = connection_seconds + 60", (email, today_str))
    conn.commit()
    conn.close()

def get_full_radar_stats(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT last_seen, total_connection_seconds FROM users WHERE email=?", (email,))
    user_data = c.fetchone()
    if not user_data:
        conn.close()
        return None
    last_seen, total_sec = user_data
    total_sec = total_sec or 0
    c.execute("SELECT date, connection_seconds FROM daily_connection WHERE email=? ORDER BY date DESC", (email,))
    history = c.fetchall()
    conn.close()
    today_str = str(datetime.date.today())
    today_sec = 0
    archive = []
    for row in history:
        date_str, sec = row
        if date_str == today_str: today_sec = sec
        else: archive.append({"date": date_str, "seconds": sec})
    return {"last_seen": last_seen, "total_seconds": total_sec, "today_seconds": today_sec, "history": archive}

# ==========================================
# 🔥 دوال المراقب والطرد التلقائي 🔥
# ==========================================

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def get_active_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email, uuid, expiry_date FROM users WHERE status='active'")
    users = c.fetchall()
    conn.close()
    return users

def set_user_expired(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE users SET status='expired' WHERE email=?", (email,))
    conn.commit()
    conn.close()

# ==========================================
# 📊 دوال الإحصائيات (بايتات)
# ==========================================

def log_daily_usage(email, total_used_bytes):
    today = str(datetime.date.today())
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO daily_usage VALUES (?, ?, ?)", (email, today, total_used_bytes))
    conn.commit()
    conn.close()

def get_usage_stats(email, current_total_used):
    today = str(datetime.date.today())
    yesterday = str(datetime.date.today() - datetime.timedelta(days=1))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT total_used FROM daily_usage WHERE email=? AND date=?", (email, yesterday))
    y_data = c.fetchone()
    used_yesterday_total = y_data[0] if y_data else 0
    used_today = current_total_used - used_yesterday_total if current_total_used > used_yesterday_total else current_total_used
    conn.close()
    return used_today, used_yesterday_total

init_db()
