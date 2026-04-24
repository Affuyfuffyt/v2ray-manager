import sqlite3
import datetime

def init_db():
    conn = sqlite3.connect('database/bot_data.db')
    c = conn.cursor()
    # جدول المشتركين
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (name TEXT PRIMARY KEY, uuid TEXT, quota REAL, created_at DATE)''')
    # جدول الاستهلاك اليومي (السر القوي بالأداة)
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage
                 (name TEXT, date DATE, total_used_until_today REAL)''')
    conn.commit()
    conn.close()

def log_daily_usage(name, total_used_from_server):
    # تشتغل يومياً لحفظ استهلاك البارحة
    today = datetime.date.today()
    conn = sqlite3.connect('database/bot_data.db')
    conn.execute("INSERT INTO daily_usage VALUES (?, ?, ?)", (name, today, total_used_from_server))
    conn.commit()
