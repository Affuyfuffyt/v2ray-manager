import time
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from database import load_db, update_db
from xray_core.panel_api import PanelAPI

# قاموس لحفظ بيانات التمديد المؤقتة
renew_data = {}

def register_manage_handlers(bot):
    api = PanelAPI()

    # 1. زر إظهار قائمة المشتركين
    @bot.callback_query_handler(func=lambda call: call.data == "manage_users")
    def show_users_list(call):
        chat_id = call.message.chat.id
        db = load_db()
        
        if not db:
            bot.answer_callback_query(call.id, "📭 لا يوجد مشتركون حالياً.")
            return

        markup = InlineKeyboardMarkup(row_width=1)
        for email, data in db.items():
            # إظهار حالة المشترك (أخضر شغال، أحمر مطرود)
            status = "🟢" if data.get('is_active', True) else "🔴"
            markup.add(InlineKeyboardButton(f"{status} {email}", callback_data=f"user_{email}"))
        
        bot.edit_message_text("👥 **قائمة المشتركين:**\nاختر مشتركاً لعرض تفاصيله:", 
                              chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # 2. زر تفاصيل المشترك (الاستهلاك الفعلي والتاريخ)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("user_"))
    def show_user_details(call):
        chat_id = call.message.chat.id
        email = call.data.split('user_')[1]
        
        db = load_db()
        if email not in db:
            bot.answer_callback_query(call.id, "❌ المشترك غير موجود.")
            return
            
        user = db[email]
        
        # === تحويل البايتات إلى جيجابايت وميجابايت ===
        used_bytes = user.get('used_bytes', 0)
        used_mb = used_bytes / (1024 * 1024)
        used_gb = used_bytes / (1024**3)
        
        limit_bytes = user.get('limit_bytes', 0)
        limit_gb = limit_bytes / (1024**3)
        
        used_str = f"{used_gb:.2f} GB" if used_gb >= 1 else f"{used_mb:.2f} MB"
        limit_str = f"{limit_gb:.2f} GB" if limit_bytes > 0 else "بلا حدود ♾️"
        
        # حساب وتنسيق وقت الانتهاء
        expiry_ts = user.get('expiry_time', 0)
        if expiry_ts > 0:
            expiry_date = datetime.fromtimestamp(expiry_ts).strftime('%Y-%m-%d %H:%M:%S')
        else:
            expiry_date = "غير محدد"
            
        status = "فعال 🟢" if user.get('is_active', True) else "متوقف 🔴 (منتهي)"
        
        details = f"""
📊 **تفاصيل المشترك:** `{email}`
🔑 **المعرف:** `{user.get('uuid')}`
---
📉 **الاستهلاك الفعلي:** `{used_str}` من أصل `{limit_str}`
⏳ **موعد الانتهاء:** `{expiry_date}`
وضع الحساب: **{status}**
        """
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("♻️ تمديد وتصفير", callback_data=f"renew_{email}"),
            InlineKeyboardButton("🗑️ حذف نهائي", callback_data=f"del_{email}")
        )
        markup.add(InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="manage_users"))
        
        bot.edit_message_text(details, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    # 3. الحذف النهائي من السيرفر والداتا بيس
    @bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
    def delete_client(call):
        email = call.data.split("del_")[1]
        
        # الطرد من السيرفر الفعلي
        api.change_client_status(email, enable=False)
        
        # المسح من ملف البيانات
        db_data = load_db()
        if email in db_data:
            del db_data[email]
            update_db(db_data)
            
        bot.edit_message_text(f"✅ تم حذف المشترك `{email}` نهائياً.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    # ==================================================
    # 4. نظام التمديد (إعادة التشغيل وتصفير العداد)
    # ==================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("renew_"))
    def start_renew(call):
        email = call.data.split("renew_")[1]
        chat_id = call.message.chat.id
        renew_data[chat_id] = {'email': email}
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("1 دقيقة ⏱️", callback_data="rdur_1m"),
            InlineKeyboardButton("1 ساعة ⏳", callback_data="rdur_1h"),
            InlineKeyboardButton("يوم", callback_data="rdur_1d"),
            InlineKeyboardButton("شهر", callback_data="rdur_30d"),
            InlineKeyboardButton("مدة يدوية ✍️", callback_data="rdur_manual")
        )
        bot.edit_message_text(f"♻️ تمديد للمشترك `{email}`\n\n⏳ اختر المدة الجديدة:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("rdur_"))
    def ask_renew_quota(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        
        if choice == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل المدة (مثال: 5m, 2h, 10d):")
            bot.register_next_step_handler(msg, lambda m: save_rdur_manual(m, bot))
        else:
            renew_data[chat_id]['duration_str'] = choice
            show_renew_quota(chat_id, bot, call.message.message_id)

    def save_rdur_manual(message, bot):
        chat_id = message.chat.id
        text = message.text.lower().strip()
        if not (text.endswith('m') or text.endswith('h') or text.endswith('d') or text.endswith('y') or text.isdigit()):
            msg = bot.send_message(chat_id, "❌ خطأ! أرسل صيغة صحيحة:")
            bot.register_next_step_handler(msg, lambda m: save_rdur_manual(m, bot))
            return
        renew_data[chat_id]['duration_str'] = text
        show_renew_quota(chat_id, bot)

    def show_renew_quota(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("100 MB", callback_data="rquota_100m"),
            InlineKeyboardButton("10 GB", callback_data="rquota_10g"),
            InlineKeyboardButton("100 GB", callback_data="rquota_100g"),
            InlineKeyboardButton("بلا حدود ♾️", callback_data="rquota_unlimited"),
            InlineKeyboardButton("سعة يدوية ✍️", callback_data="rquota_manual")
        )
        text = "📊 حدد السعة الجديدة للتمديد:"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("rquota_"))
    def finalize_renew(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        
        if choice == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل السعة بالجيجابايت (مثال: 50):")
            bot.register_next_step_handler(msg, lambda m: execute_renew(m, bot, True))
        else:
            quota_map = { "100m": 100*1024*1024, "10g": 10*1024**3, "100g": 100*1024**3, "unlimited": 0 }
            renew_data[chat_id]['new_quota'] = quota_map[choice]
            execute_renew(call.message, bot, False)

    def execute_renew(message, bot, is_manual):
        chat_id = message.chat.id
        data = renew_data.get(chat_id)
        if not data: return
        
        if is_manual:
            try:
                data['new_quota'] = int(float(message.text) * 1024**3)
            except:
                msg = bot.send_message(chat_id, "❌ خطأ! أرسل رقماً فقط:")
                bot.register_next_step_handler(msg, lambda m: execute_renew(m, bot, True))
                return

        email = data['email']
        new_quota = data['new_quota']
        dur_str = data['duration_str']
        
        # حساب الوقت الجديد
        if dur_str.endswith('m'): sec = int(dur_str[:-1]) * 60
        elif dur_str.endswith('h'): sec = int(dur_str[:-1]) * 3600
        elif dur_str.endswith('d'): sec = int(dur_str[:-1]) * 86400
        elif dur_str.endswith('y'): sec = int(dur_str[:-1]) * 86400 * 365
        else: sec = int(dur_str) * 86400
        
        new_expiry = time.time() + sec
        
        db_data = load_db()
        if email in db_data:
            # تصفير العداد وتجديد البيانات
            db_data[email]['limit_bytes'] = new_quota
            db_data[email]['expiry_time'] = new_expiry
            db_data[email]['used_bytes'] = 0 
            db_data[email]['is_active'] = True
            update_db(db_data)
            
            # إعادة تفعيل المشترك في السيرفر (نفترض بروتوكول vless بشكل افتراضي للتجديد)
            api.create_client(email, db_data[email]['uuid'], "vless")
            
            bot.send_message(chat_id, f"✅ **تم التمديد بنجاح!**\n\n👤 المشترك: `{email}`\nتم تصفير العداد وتفعيل الكود للعمل فوراً. 🚀", parse_mode="Markdown")
        
        renew_data.pop(chat_id, None)
