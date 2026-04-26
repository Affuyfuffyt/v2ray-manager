import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import threading
import subprocess
import time
import config
from xray_core.panel_api import PanelAPI
from handlers import admin_start, create_flow, manage_flow, speed_test
from quota_monitor import start_quota_monitor

# 1. تهيئة البوت والـ API
bot = telebot.TeleBot(config.BOT_TOKEN)
api = PanelAPI()

# 2. إضافة فلتر الحماية (للأدمن فقط)
class IsAdmin(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_admin'
    def check(self, message):
        return message.chat.id == config.ADMIN_ID

bot.add_custom_filter(IsAdmin())

# ==========================================
# 📊 قسم حالة الخادم (Server Status)
# ==========================================
live_monitors = {}

def get_server_status_text():
    try:
        cpu_usage = subprocess.getoutput("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        cpu_usage = float(cpu_usage) if cpu_usage else 0.0
        
        ram_total = int(subprocess.getoutput("free -m | grep Mem | awk '{print $2}'"))
        ram_used = int(subprocess.getoutput("free -m | grep Mem | awk '{print $3}'"))
        ram_percent = int((ram_used / ram_total) * 100) if ram_total > 0 else 0
        
        disk_total = subprocess.getoutput("df -h / | tail -1 | awk '{print $2}'")
        disk_used = subprocess.getoutput("df -h / | tail -1 | awk '{print $3}'")
        disk_percent_str = subprocess.getoutput("df -h / | tail -1 | awk '{print $5}'").replace('%', '')
        disk_percent = int(disk_percent_str) if disk_percent_str.isdigit() else 0

        def make_bar(percent):
            filled = int(percent / 10)
            return '█' * filled + '▒' * (10 - filled)

        text = f"🖥️ | 𝗦𝗘𝗥𝗩𝗘𝗥 𝗥𝗘𝗦𝗢𝗨𝗥𝗖𝗘𝗦\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"⚙️ **CPU:** `[{make_bar(cpu_usage)}]` {cpu_usage:.1f}%\n"
        text += f"🗄️ **RAM:** `[{make_bar(ram_percent)}]` {ram_percent}%\n"
        text += f"   └ 📊 {ram_used}MB / {ram_total}MB\n"
        text += f"💾 **Disk:** `[{make_bar(disk_percent)}]` {disk_percent}%\n"
        text += f"   └ 📊 {disk_used} / {disk_total}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"⏱️ _آخر تحديث: {time.strftime('%H:%M:%S')}_\n"
        
        return text
    except Exception as e:
        return "⚠️ حدث خطأ أثناء جلب بيانات السيرفر."

def get_status_keyboard(is_live=False):
    markup = InlineKeyboardMarkup(row_width=2)
    if not is_live:
        btn_refresh = InlineKeyboardButton("🔄 تحديث الآن", callback_data="status_refresh")
        btn_live = InlineKeyboardButton("📡 تحديث مستمر (2 دقيقة)", callback_data="status_live")
        markup.add(btn_refresh, btn_live)
    else:
        btn_stop = InlineKeyboardButton("🛑 إيقاف التحديث", callback_data="status_stop")
        markup.add(btn_stop)
    return markup

# ==========================================
# 3. تسجيل المعالجات (Handlers) لجميع الأقسام
# ==========================================
create_flow.register_create_handlers(bot)
manage_flow.register_manage_handlers(bot)
speed_test.register_speed_handlers(bot)

@bot.message_handler(commands=['start'], is_admin=True)
def start(message):
    admin_start.show_main_menu(bot, message.chat.id)

# ----------------- أوامر حالة الخادم -----------------
@bot.message_handler(func=lambda message: message.text == "🖥️ حالة الخادم", is_admin=True)
def send_server_status(message):
    text = get_server_status_text()
    markup = get_status_keyboard()
    bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
def handle_status_callbacks(call):
    chat_id = call.message.chat.id
    msg_id = call.message.message_id
    
    if call.data == "status_refresh":
        text = get_server_status_text()
        markup = get_status_keyboard()
        bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
        bot.answer_callback_query(call.id, "✅ تم تحديث بيانات السيرفر!")
        
    elif call.data == "status_live":
        bot.answer_callback_query(call.id, "📡 تم تفعيل المراقبة الحية لمدة دقيقتين!")
        live_monitors[msg_id] = True
        
        markup = get_status_keyboard(is_live=True)
        bot.edit_message_reply_markup(chat_id, msg_id, reply_markup=markup)
        
        def live_update_thread():
            end_time = time.time() + 120
            while time.time() < end_time and live_monitors.get(msg_id, False):
                time.sleep(3)
                if not live_monitors.get(msg_id, False): 
                    break
                try:
                    text = get_server_status_text()
                    markup = get_status_keyboard(is_live=True)
                    bot.edit_message_text(text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
                except Exception:
                    pass
            
            live_monitors[msg_id] = False
            try:
                final_text = get_server_status_text() + "\n*(انتهت المراقبة المستمرة)*"
                markup = get_status_keyboard(is_live=False)
                bot.edit_message_text(final_text, chat_id, msg_id, reply_markup=markup, parse_mode="Markdown")
            except:
                pass

        threading.Thread(target=live_update_thread).start()
        
    elif call.data == "status_stop":
        live_monitors[msg_id] = False
        bot.answer_callback_query(call.id, "🛑 تم إيقاف المراقبة الحية.")

# ==========================================
# 4. تشغيل النظام بالكامل
# ==========================================
if __name__ == "__main__":
    print(f"🚀 البوت يعمل الآن للأدمن ID: {config.ADMIN_ID}")
    
    # تشغيل مراقب الاستهلاك والسرعة بالخلفية (ليقوم بسحب الأرقام من المحرك)
    monitor_thread = threading.Thread(target=start_quota_monitor, daemon=True)
    monitor_thread.start()
    print("📊 نظام حساب الجيجابايت والسرعة يعمل الآن بالخلفية...")
    
    try:
        # البدء باستقبال أوامر التلجرام
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ حدث خطأ في البوت: {e}")
