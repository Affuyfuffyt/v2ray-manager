import sys
import os
import time
import datetime
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# 🔥 إجبار الملف على قراءة المسار الرئيسي لحل مشكلة عدم العثور على db 🔥
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# الاستدعاء المباشر للدوال من ملف db.py الرئيسي
from db import link_user_subscription, get_user_subscriptions, get_subscription_details

def register_user_handlers(bot):
    @bot.callback_query_handler(func=lambda call: call.data == "add_user_sub")
    def add_sub_callback(call):
        msg = bot.send_message(call.message.chat.id, "📝 **الرجاء إرسال اسم الاشتراك الخاص بك:**\n(أرسل الاسم كما استلمته من المبيعات بالضبط)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_sub, bot)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("view_sub_"))
    def view_sub_callback(call):
        email = call.data.split("view_sub_")[1]
        show_sub_details(bot, call.message.chat.id, email, call.message.message_id)

    @bot.callback_query_handler(func=lambda call: call.data == "user_main_menu")
    def back_to_main(call):
        show_user_main_menu(bot, call.message.chat.id, call.message.message_id)

def process_add_sub(message, bot):
    email = message.text.strip()
    chat_id = message.chat.id
    try:
        # استخدام الدالة المستدعاة مباشرة
        success = link_user_subscription(chat_id, email)
        
        if success:
            bot.send_message(chat_id, f"✅ **تم إضافة الحساب بنجاح!**\nتم ربط الاشتراك `{email}` بحسابك.", parse_mode="Markdown")
        else:
            bot.send_message(chat_id, "❌ **عذراً!** إما أن الاسم غير صحيح، أو أنه مربوط بحسابك مسبقاً.", parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ حدث خطأ أثناء ربط الحساب: {e}")
    
    show_user_main_menu(bot, chat_id)

def show_user_main_menu(bot, chat_id, message_id=None):
    try:
        subs = get_user_subscriptions(chat_id)
        markup = InlineKeyboardMarkup(row_width=1)
        
        markup.add(InlineKeyboardButton("➕ إضافة حساب اشتراك", callback_data="add_user_sub"))
        
        # إضافة أزرار للاشتراكات المربوطة
        for sub in subs:
            markup.add(InlineKeyboardButton(f"👤 {sub}", callback_data=f"view_sub_{sub}"))
            
        text = "👋 **مرحباً بك في بوابة المشتركين!**\n\nمن خلال هذا البوت يمكنك:\n🔹 متابعة استهلاكك للبيانات\n🔹 معرفة متى ينتهي اشتراكك\n🔹 استلام تنبيهات التجديد\n\n👇 اضغط على **إضافة حساب اشتراك** وأرسل اسمك لربط حسابك."
        
        if message_id:
            try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
            except: bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ حدث خطأ في القائمة: {e}")

def show_sub_details(bot, chat_id, email, message_id):
    try:
        details = get_subscription_details(email)
        if not details:
            bot.send_message(chat_id, "❌ حدث خطأ في جلب بيانات الاشتراك.")
            return
        
        expiry_date, quota_bytes, status, last_seen, total_sec = details
        
        # 1. جلب الاستهلاك الفعلي بدقة (من ملف JSON)
        used_bytes = 0
        try:
            home_dir = os.path.expanduser("~")
            for json_name in ["users_db.json", "database.json", "data.json"]:
                db_path = os.path.join(home_dir, "v2ray_manager", json_name)
                if os.path.exists(db_path):
                    with open(db_path, 'r', encoding='utf-8') as f:
                        db_data = json.load(f)
                        if email in db_data:
                            used_bytes = db_data[email].get('used_bytes', 0)
                            break
        except:
            pass
            
        used_gb = used_bytes / (1024**3)
        used_mb = used_bytes / (1024**2)
        used_str = f"{used_gb:.2f} GB" if used_gb >= 1 else f"{used_mb:.2f} MB"
        quota_str = "بلا حدود ♾️" if quota_bytes == 0 else f"{quota_bytes / (1024**3):.2f} GB"

        # 2. حساب الوقت المتبقي
        now = time.time()
        expiry_time = float(expiry_date)
        time_left = expiry_time - now
        
        if time_left <= 0:
            time_str = "منتهي ❌"
            status_icon = "🔴 غير نشط"
        else:
            days = int(time_left // 86400)
            hours = int((time_left % 86400) // 3600)
            time_str = f"{days} يوم و {hours} ساعة"
            status_icon = "🟢 نشط" if status == 'active' else "🔴 متوقف"
        
        # 3. فورمات الوقت الكلي
        total_hours = int(total_sec // 3600)
        total_mins = int((total_sec % 3600) // 60)
        
        last_seen_str = last_seen if last_seen else "لم يتصل بعد"

        text = f"📊 **تفاصيل الاشتراك:** `{email}`\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"🚦 **الحالة:** {status_icon}\n"
        text += f"⏳ **الوقت المتبقي:** {time_str}\n"
        text += f"📅 **موعد الانتهاء:** {datetime.datetime.fromtimestamp(expiry_time).strftime('%Y-%m-%d %H:%M')}\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"📉 **الاستهلاك:** `{used_str}` من أصل `{quota_str}`\n"
        text += f"━━━━━━━━━━━━━━━━━━\n"
        text += f"📡 **آخر ظهور:** {last_seen_str}\n"
        text += f"⏱️ **إجمالي وقت التشغيل:** {total_hours} ساعة و {total_mins} دقيقة\n"
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🛒 تجديد الاشتراك", url="https://t.me/l_t22"))
        markup.add(InlineKeyboardButton("📢 قناة التحديثات", url="https://t.me/r338888"))
        markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="user_main_menu"))
        
        bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ حدث خطأ في جلب التفاصيل: {e}")
