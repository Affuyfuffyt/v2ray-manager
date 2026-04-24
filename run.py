import telebot
import schedule
import threading
import time
import config
from database import db
from xray_core.panel_api import PanelAPI
from handlers import admin_start, create_flow, manage_flow
from anti_share import start_monitor # 👈 استيراد نظام الحماية الجديد

# 1. تهيئة البوت والـ API وقاعدة البيانات
bot = telebot.TeleBot(config.BOT_TOKEN)
api = PanelAPI()
db.init_db()

# 2. إضافة فلتر الحماية (للأدمن فقط)
class IsAdmin(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_admin'
    def check(self, message):
        return message.chat.id == config.ADMIN_ID

bot.add_custom_filter(IsAdmin())

# 3. تسجيل معالجات الأزرار والرسائل (Handlers)
# ملاحظة: نمرر البوت لكل ملف ليتعرف على الأوامر
create_flow.register_create_handlers(bot)
manage_flow.register_manage_handlers(bot)

@bot.message_handler(commands=['start'], is_admin=True)
def start(message):
    admin_start.show_main_menu(bot, message.chat.id)

# ---------------------------------------------------------
# 4. نظام المجدول (حساب استهلاك البارحة واليوم)
# ---------------------------------------------------------
def daily_job():
    print("⏳ جاري تسجيل الاستهلاك اليومي للمشتركين...")
    users = db.get_all_users()
    for email in users:
        current_usage = api.get_client_traffic(email)
        db.log_daily_usage(email, current_usage)
    print("✅ تم تحديث سجلات الاستهلاك بنجاح.")

def run_scheduler():
    # ضبط المجدول ليعمل كل يوم عند منتصف الليل
    schedule.every().day.at("00:00").do(daily_job)
    while True:
        schedule.run_pending()
        time.sleep(60) # فحص كل دقيقة

# تشغيل المجدول في خيط (Thread) منفصل لكي لا يتوقف البوت
scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
scheduler_thread.start()

# ---------------------------------------------------------
# 5. تشغيل البوت ونظام الحماية
# ---------------------------------------------------------
if __name__ == "__main__":
    print(f"🚀 البوت يعمل الآن للأدمن ID: {config.ADMIN_ID}")
    
    # 👈 تشغيل نظام الطرد الذكي في خيط (Thread) منفصل
    monitor_thread = threading.Thread(target=start_monitor, daemon=True)
    monitor_thread.start()
    print("🛡️ تم تشغيل نظام الحماية Anti-Share بالخلفية.")

    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ في البوت: {e}")
