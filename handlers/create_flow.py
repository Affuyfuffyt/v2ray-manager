from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import uuid
import random
import string
import json
import base64
import time
import requests
import threading
import os
import urllib.parse

# 👇 استدعاء دوال الحفظ + دوال النظام الذكي للمكافآت المعلقة
from database import save_user, extend_json_expiry
from db import (
    add_user, get_active_users, set_user_expired, get_user_by_ref_code, 
    extend_user_expiry, assign_ref_code, add_pending_reward, 
    get_all_pending_rewards, remove_pending_reward, get_user_connection_seconds
)

# 👇 استدعاء نظام الإشعارات لإبلاغ العميل
try:
    from user_notifier import notify_extension
except ImportError:
    def notify_extension(bot, email, seconds_added): pass

creation_data = {}
watchdog_started = False

# ==========================================
# 🛠️ دالة الإضافة الذكية
# ==========================================
def add_client_to_config(user_name, uuid_val, protocol):
    try:
        home_dir = os.path.expanduser("~")
        config_path = f"{home_dir}/xray_core/config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            modified = False
            if "inbounds" in config_data:
                for inbound in config_data["inbounds"]:
                    
                    if inbound.get("protocol") == "trojan" and "settings" in inbound:
                        clients = inbound["settings"].setdefault("clients", [])
                        for c in clients:
                            if "id" in c: 
                                c["password"] = c.pop("id")
                                modified = True

                    if inbound.get("tag") == protocol and "settings" in inbound:
                        clients = inbound["settings"].setdefault("clients", [])
                        exists = any(c.get("id") == uuid_val or c.get("password") == uuid_val for c in clients)
                        if not exists:
                            if protocol == "vless":
                                clients.append({"id": uuid_val, "email": user_name, "flow": ""})
                            elif protocol == "vmess":
                                clients.append({"id": uuid_val, "email": user_name, "alterId": 0})
                            elif protocol == "trojan":
                                clients.append({"password": uuid_val, "email": user_name})
                            modified = True
                        break 
                        
            if modified:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error adding to config: {e}")

# ==========================================
# 🗑️ دالة حذف المشترك المنتهي
# ==========================================
def remove_client_from_config(uuid_val):
    try:
        home_dir = os.path.expanduser("~")
        config_path = f"{home_dir}/xray_core/config.json"
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            modified = False
            if "inbounds" in config_data:
                for inbound in config_data["inbounds"]:
                    if "settings" in inbound and "clients" in inbound["settings"]:
                        original = inbound["settings"]["clients"]
                        new_clients = [c for c in original if c.get("id") != uuid_val and c.get("password") != uuid_val]
                        if len(original) != len(new_clients):
                            inbound["settings"]["clients"] = new_clients
                            modified = True
                            
            if modified:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"Error removing from config: {e}")

# ==========================================
# 🔄 دالة عمل ريستارت للسيرفر
# ==========================================
def restart_alwaysdata(bot=None, chat_id=None, success_msg=None, fail_msg=None):
    try:
        home_dir = os.path.expanduser("~")
        key_file = f"{home_dir}/alwaysdata_keys.txt"
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                lines = f.read().strip().split('\n')
                if len(lines) >= 2:
                    SITE_ID = lines[0].strip()
                    API_KEY = lines[1].strip()
                    url = f"https://api.alwaysdata.com/v1/site/{SITE_ID}/restart/"
                    response = requests.post(url, auth=(API_KEY, ''))
                    
                    if bot and chat_id:
                        if response.status_code in [200, 201, 202, 204]:
                            bot.send_message(chat_id, success_msg, parse_mode="Markdown")
                        else:
                            bot.send_message(chat_id, f"{fail_msg}\nكود الخطأ: {response.status_code}")
                    return response.status_code in [200, 201, 202, 204]
    except Exception as e:
        if bot and chat_id: bot.send_message(chat_id, "⚠️ حدث خطأ في الاتصال بمنصة Alwaysdata.")
        print(f"Restart Error: {e}")
    return False

# ==========================================
# ⏱️ العداد التنازلي لطرد المشترك
# ==========================================
def auto_restart_on_expiry(bot, chat_id, expiry_time, user_name, uuid_val, protocol):
    wait_seconds = expiry_time - time.time()
    if wait_seconds > 0:
        time.sleep(wait_seconds) 
        
    if protocol != "trojan":
        try:
            from xray_core.panel_api import PanelAPI
            local_api = PanelAPI()
            try: local_api.delete_client(user_name)
            except: pass
            try: local_api.remove_client(uuid_val)
            except: pass
        except: pass
    
    remove_client_from_config(uuid_val)
    success_msg = f"🛑 **تنبيه انتهاء صلاحية!** 🛑\n\n👤 المشترك: `{user_name}`\n⏳ انتهى وقته للتو.\n🔄 **تم سحب صلاحيته وعمل ريستارت للسيرفر لطرده نهائياً!**"
    fail_msg = f"⚠️ انتهى وقت `{user_name}` ولكن فشل الريستارت التلقائي!"
    restart_alwaysdata(bot, chat_id, success_msg, fail_msg)


# ==========================================
# 👁️ مراقب قاعدة البيانات والمكافآت الذكي
# ==========================================
def database_expiry_watchdog(bot):
    admin_id = None
    home_dir = os.path.expanduser("~")
    env_path = f"{home_dir}/v2ray_manager/.env"
    
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.startswith("ADMIN_ID="):
                    try: admin_id = int(line.strip().split("=")[1])
                    except: pass

    while True:
        try:
            # 1. مراقبة انتهاء المشتركين
            active_users = get_active_users() 
            current_time = time.time()
            expired_names = []
            
            for email, uuid_val, expiry_date in active_users:
                if expiry_date and current_time >= float(expiry_date):
                    remove_client_from_config(uuid_val)
                    set_user_expired(email)
                    expired_names.append(email)
                    
            if expired_names and admin_id:
                success = restart_alwaysdata()
                names_str = "\n".join([f"• `{name}`" for name in expired_names])
                if success:
                    msg = f"🛑 **تنبيه مراقب قاعدة البيانات!** 🛑\n\nالمنتهين:\n{names_str}\n\n🔄 **تم سحب الصلاحيات وعمل ريستارت للسيرفر لطردهم!**"
                else:
                    msg = f"⚠️ تم مسح المشتركين ({names_str}) من الملف ولكن فشل الريستارت التلقائي!"
                bot.send_message(admin_id, msg, parse_mode="Markdown")

            # 2. 🔥 مراقبة المكافآت المعلقة (النظام الذكي) 🔥
            pending_rewards = get_all_pending_rewards()
            for ref_email, inv_email, reward_sec, c_id in pending_rewards:
                # إذا المشترك المدعو استهلك 60 ثانية بالرادار (يعني كنك دقيقة)
                if get_user_connection_seconds(inv_email) >= 60:
                    
                    # تمديد الرادار واللوحة
                    extend_user_expiry(ref_email, reward_sec)
                    try: extend_json_expiry(ref_email, reward_sec)
                    except: pass

                    # إعادة زراعة كود الداعي بالسيرفر
                    ref_uuid = None
                    try:
                        for json_name in ["users_db.json", "database.json", "data.json"]:
                            db_path = os.path.join(home_dir, "v2ray_manager", json_name)
                            if os.path.exists(db_path):
                                with open(db_path, 'r', encoding='utf-8') as f:
                                    db_data = json.load(f)
                                    if ref_email in db_data:
                                        ref_uuid = db_data[ref_email].get('uuid')
                                        break
                    except: pass

                    if ref_uuid:
                        try:
                            from xray_core.panel_api import PanelAPI
                            local_api = PanelAPI()
                            local_api.create_client(ref_email, ref_uuid, "vless")
                        except: pass
                        add_client_to_config(ref_email, ref_uuid, "vless")

                    # حذف المكافأة لأنها اتنفذت
                    remove_pending_reward(inv_email)
                    
                    # إرسال تأكيد للأدمن وريستارت للسيرفر
                    bot.send_message(c_id, f"🎉 **تم تفعيل المكافأة المعلقة!**\n\nقام المشترك الجديد `{inv_email}` باستخدام الكود لمدة دقيقة.\nتم الآن تمديد وإعادة تشغيل كود الداعي `{ref_email}` بنجاح! 🚀", parse_mode="Markdown")
                    restart_alwaysdata()

                    # 🔥 إرسال إشعار للمشترك الداعي بالتمديد (إذا كان رابط حسابه بالبوت) 🔥
                    notify_extension(bot, ref_email, reward_sec)

        except Exception as e:
            pass
        time.sleep(60)

def register_create_handlers(bot):
    global watchdog_started
    if not watchdog_started:
        threading.Thread(target=database_expiry_watchdog, args=(bot,), daemon=True).start()
        watchdog_started = True

    @bot.callback_query_handler(func=lambda call: call.data == "create_code")
    def start_creation(call):
        chat_id = call.message.chat.id
        msg = bot.send_message(chat_id, "📝 أرسل اسم المشترك (باللغة الإنجليزية وبدون مسافات):")
        bot.register_next_step_handler(msg, process_name, bot)

    def process_name(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id] = {'name': message.text.strip()}
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("⏭️ تخطي كود الدعوة", callback_data="skip_referral"))
        msg = bot.send_message(chat_id, "🎁 **نظام المكافآت والدعوات:**\nإذا كان المشترك قادماً عن طريق شخص آخر، أرسل (كود دعوة) الشخص الداعي الآن ليتم مكافأته.\n\n👇 أو اضغط تخطي للاستمرار:", reply_markup=markup, parse_mode="Markdown")
        bot.register_next_step_handler(msg, check_referral_text, bot)

    @bot.callback_query_handler(func=lambda call: call.data == "skip_referral")
    def skip_ref(call):
        chat_id = call.message.chat.id
        bot.clear_step_handler_by_chat_id(chat_id) 
        ask_protocol(chat_id, bot, call.message.message_id)

    def check_referral_text(message, bot):
        chat_id = message.chat.id
        ref_code = message.text.strip()
        referrer = get_user_by_ref_code(ref_code)

        if referrer:
            referrer_email = referrer[0]
            creation_data[chat_id]['referrer'] = referrer_email

            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("تمديد 5 أيام 🎁", callback_data="rew_5"),
                InlineKeyboardButton("تمديد 10 أيام 🎁", callback_data="rew_10"),
                InlineKeyboardButton("تمديد 30 يوم 🎁", callback_data="rew_30"),
                InlineKeyboardButton("إدخال يدوي ✍️", callback_data="rew_manual"),
                InlineKeyboardButton("إلغاء التمديد والتخطي ⏭️", callback_data="skip_referral")
            )
            bot.send_message(chat_id, f"✅ **كود صحيح!**\nهذا الكود يعود للمشترك: `{referrer_email}`\n\nاختر كم تريد أن تمدد صلاحيته كمكافأة للدعوة:", reply_markup=markup, parse_mode="Markdown")
        else:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("⏭️ الاستمرار بدون مكافأة (تخطي)", callback_data="skip_referral"))
            msg = bot.send_message(chat_id, "❌ كود الدعوة غير صحيح أو غير موجود!\nتأكد من الكود وأرسله مجدداً، أو اضغط تخطي:", reply_markup=markup)
            bot.register_next_step_handler(msg, check_referral_text, bot)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("rew_"))
    def process_reward(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]

        if choice == "manual":
            bot.clear_step_handler_by_chat_id(chat_id)
            msg = bot.send_message(chat_id, "✍️ أرسل مدة التمديد:\n(مثال: `5m` لدقائق، `2h` لساعات، `10d` لأيام، `1mo` لشهر)", parse_mode="Markdown")
            bot.register_next_step_handler(msg, manual_reward_input, bot)
        else:
            days = int(choice)
            apply_reward(chat_id, bot, days * 86400)

    def manual_reward_input(message, bot):
        chat_id = message.chat.id
        text = message.text.lower().strip()
        
        if text.endswith('mo'): sec = int(text[:-2]) * 86400 * 30
        elif text.endswith('m'): sec = int(text[:-1]) * 60
        elif text.endswith('h'): sec = int(text[:-1]) * 3600
        elif text.endswith('d'): sec = int(text[:-1]) * 86400
        else:
            msg = bot.send_message(chat_id, "❌ صيغة خاطئة! حاول مجدداً (مثال: `5m`, `2h`, `10d`, `1mo`):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, manual_reward_input, bot)
            return
            
        apply_reward(chat_id, bot, sec)

    # 🔥 تعليق المكافأة وعدم تفعيلها فوراً 🔥
    def apply_reward(chat_id, bot, seconds):
        referrer_email = creation_data[chat_id].get('referrer')
        if referrer_email:
            creation_data[chat_id]['reward_seconds'] = seconds
            bot.send_message(chat_id, f"⏳ **تم تعليق المكافأة!**\nسيتم تفعيل المكافأة للداعي `{referrer_email}` **تلقائياً** بعد أن يتصل المشترك الجديد بالإنترنت لمدة دقيقة واحدة.", parse_mode="Markdown")
        ask_protocol(chat_id, bot)

    def ask_protocol(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("VLESS", callback_data="proto_vless"),
            InlineKeyboardButton("VMESS", callback_data="proto_vmess"),
            InlineKeyboardButton("Trojan", callback_data="proto_trojan")
        )
        text = "🌐 اختر البروتوكول:"
        if message_id:
            try:
                bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            except:
                bot.send_message(chat_id, text, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("proto_"))
    def process_protocol(call):
        chat_id = call.message.chat.id
        protocol = call.data.split('_')[1]
        creation_data[chat_id]['protocol'] = protocol
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("بورت 443 (TLS) 🔒", callback_data="port_443"),
            InlineKeyboardButton("بورت 80 🌐", callback_data="port_80"),
            InlineKeyboardButton("إدخال البورت يدوياً ✍️", callback_data="port_manual")
        )
        bot.edit_message_text("🚪 اختر البورت:", chat_id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("port_"))
    def process_port(call):
        chat_id = call.message.chat.id
        port_val = call.data.split('_')[1]
        if port_val == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل رقم البورت:")
            bot.register_next_step_handler(msg, lambda m: save_port_and_ask_ws(m, bot))
        else:
            creation_data[chat_id]['port'] = int(port_val)
            ask_ws(chat_id, bot, call.message.message_id)

    def save_port_and_ask_ws(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id]['port'] = int(message.text)
        ask_ws(chat_id, bot)

    def ask_ws(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("WebSocket (WS) 🌐", callback_data="net_ws"))
        text = "📡 اختر نوع الشبكة:"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "net_ws")
    def process_ws(call):
        chat_id = call.message.chat.id
        creation_data[chat_id]['network'] = 'ws'
        creation_data[chat_id]['path'] = '/Telegram-@338888'
        ask_uuid(chat_id, bot, call.message.message_id)

    def ask_uuid(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("ID عشوائي 🎲", callback_data="id_random"),
            InlineKeyboardButton("ID يدوي ✍️", callback_data="id_manual")
        )
        text = "🔑 اختر المعرف (UUID):"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("id_"))
    def process_uuid(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "random":
            creation_data[chat_id]['uuid'] = str(uuid.uuid4())
            ask_ips(chat_id, bot, call.message.message_id)
        else:
            msg = bot.send_message(chat_id, "✍️ أرسل المعرف (UUID):")
            bot.register_next_step_handler(msg, lambda m: save_uuid_and_ask_ips(m, bot))

    def save_uuid_and_ask_ips(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id]['uuid'] = message.text
        ask_ips(chat_id, bot)

    def ask_ips(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("متصل واحد 📱", callback_data="ip_1"),
            InlineKeyboardButton("العدد يدوي ✍️", callback_data="ip_manual")
        )
        text = "👥 حدد عدد الأجهزة المسموحة:"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ip_"))
    def process_ips(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل عدد الأجهزة (أرقام فقط):")
            bot.register_next_step_handler(msg, lambda m: save_ips_and_ask_duration(m, bot))
        else:
            creation_data[chat_id]['ips'] = int(choice)
            ask_duration(chat_id, bot, call.message.message_id)

    def save_ips_and_ask_duration(message, bot):
        chat_id = message.chat.id
        try:
            creation_data[chat_id]['ips'] = int(message.text)
            ask_duration(chat_id, bot)
        except ValueError:
            msg = bot.send_message(chat_id, "❌ خطأ! أرسل رقماً صحيحاً للأجهزة:")
            bot.register_next_step_handler(msg, lambda m: save_ips_and_ask_duration(m, bot))

    def ask_duration(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("1 دقيقة ⏱️", callback_data="dur_1m"),
            InlineKeyboardButton("1 ساعة ⏳", callback_data="dur_1h"),
            InlineKeyboardButton("يوم", callback_data="dur_1d"),
            InlineKeyboardButton("شهر", callback_data="dur_30d"),
            InlineKeyboardButton("سنة", callback_data="dur_365d"),
            InlineKeyboardButton("مدة يدوية ✍️", callback_data="dur_manual")
        )
        text = "⏳ حدد مدة الكود:"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("dur_"))
    def process_duration(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل المدة (مثال: 5m لدقائق، 2h لساعات، 10d لأيام، 1y لسنة):")
            bot.register_next_step_handler(msg, lambda m: save_duration_and_ask_quota(m, bot))
        else:
            creation_data[chat_id]['duration_str'] = choice
            ask_quota(chat_id, bot, call.message.message_id)

    def save_duration_and_ask_quota(message, bot):
        chat_id = message.chat.id
        text = message.text.lower().strip()
        if not (text.endswith('m') or text.endswith('h') or text.endswith('d') or text.endswith('y') or text.isdigit()):
            msg = bot.send_message(chat_id, "❌ خطأ! أرسل صيغة صحيحة (مثال 10m, 2h, 5d):")
            bot.register_next_step_handler(msg, lambda m: save_duration_and_ask_quota(m, bot))
            return
        creation_data[chat_id]['duration_str'] = text
        ask_quota(chat_id, bot)

    def ask_quota(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("10 MB", callback_data="quota_10m"),
            InlineKeyboardButton("100 MB", callback_data="quota_100m"),
            InlineKeyboardButton("100 GB", callback_data="quota_100g"),
            InlineKeyboardButton("1000 GB", callback_data="quota_1000g"),
            InlineKeyboardButton("بلا حدود ♾️", callback_data="quota_unlimited"),
            InlineKeyboardButton("سعة يدوية ✍️", callback_data="quota_manual")
        )
        text = "📊 حدد سعة الاستهلاك (Quota):"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("quota_"))
    def process_quota(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل السعة بالجيجابايت (مثال: 50):")
            bot.register_next_step_handler(msg, lambda m: finalize_creation(m, bot, is_manual=True))
        else:
            quota_map = {
                "10m": 10 * 1024 * 1024,
                "100m": 100 * 1024 * 1024,
                "100g": 100 * 1024 * 1024 * 1024,
                "1000g": 1000 * 1024 * 1024 * 1024,
                "unlimited": 0
            }
            creation_data[chat_id]['quota_bytes'] = quota_map[choice]
            finalize_creation(call.message, bot, is_manual=False)

    def finalize_creation(message, bot, is_manual):
        chat_id = message.chat.id
        if is_manual:
            try:
                gb_val = float(message.text)
                creation_data[chat_id]['quota_bytes'] = int(gb_val * 1024 * 1024 * 1024)
            except ValueError:
                msg = bot.send_message(chat_id, "❌ خطأ! أرسل رقماً فقط:")
                bot.register_next_step_handler(msg, lambda m: finalize_creation(m, bot, is_manual=True))
                return

        data = creation_data[chat_id]
        protocol = data.get('protocol', 'vless').lower()
        fixed_path = f"/Telegram-@338888-{protocol}"
        data['path'] = fixed_path

        dur_str = data['duration_str']
        if dur_str.endswith('m'): sec = int(dur_str[:-1]) * 60
        elif dur_str.endswith('h'): sec = int(dur_str[:-1]) * 3600
        elif dur_str.endswith('d'): sec = int(dur_str[:-1]) * 86400
        elif dur_str.endswith('y'): sec = int(dur_str[:-1]) * 86400 * 365
        else: sec = int(dur_str) * 86400 
        
        expiry_time = time.time() + sec

        if protocol != "trojan":
            try:
                from xray_core.panel_api import PanelAPI
                local_api = PanelAPI()
                local_api.create_client(data['name'], data['uuid'], protocol)
            except Exception as e:
                pass

        add_client_to_config(data['name'], data['uuid'], protocol)

        try: save_user(data['name'], data['uuid'], data['quota_bytes'], expiry_time)
        except Exception as e: print(f"Error saving to JSON DB: {e}")

        try:
            selected_port = data.get('port', 443)
            add_user(data['name'], data['uuid'], selected_port, data['quota_bytes'], expiry_time)
        except Exception as e: print(f"Error saving to SQLite DB: {e}")

        # 🔥 توليد وحفظ كود دعوة خاص للمشترك الجديد 🔥
        new_ref_code = "REF-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        try: assign_ref_code(data['name'], new_ref_code)
        except Exception as e: pass

        # 🔥 حفظ المكافأة المعلقة بالجدول (إذا الداعي موجود) 🔥
        reward_sec = data.get('reward_seconds')
        referrer_email = data.get('referrer')
        if reward_sec and referrer_email:
            try: add_pending_reward(referrer_email, data['name'], reward_sec, chat_id)
            except Exception as e: print(f"Pending reward error: {e}")

        threading.Thread(
            target=auto_restart_on_expiry, 
            args=(bot, chat_id, expiry_time, data['name'], data['uuid'], protocol), 
            daemon=True
        ).start()

        selected_port = data.get('port', 443)
        host_domain = "wathfor.alwaysdata.net" 
        try:
            home_dir = os.path.expanduser("~")
            key_file = f"{home_dir}/alwaysdata_keys.txt"
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    lines = f.read().strip().split('\n')
                    if len(lines) >= 3 and lines[2].strip() != "":
                        host_domain = lines[2].strip()
        except:
            pass
        
        if selected_port == 443:
            security_type = "tls"
            sni_param = host_domain
            sni_str = f"&sni={sni_param}"
        else:
            security_type = "none"
            sni_param = ""
            sni_str = ""

        encoded_path = urllib.parse.quote(fixed_path, safe='')

        if protocol == "vless":
            final_link = f"vless://{data['uuid']}@{host_domain}:{selected_port}?type=ws&security={security_type}&path={encoded_path}&host={host_domain}{sni_str}#{data['name']}"
        elif protocol == "trojan":
            final_link = f"trojan://{data['uuid']}@{host_domain}:{selected_port}?type=ws&security={security_type}&path={encoded_path}&host={host_domain}{sni_str}#{data['name']}"
        elif protocol == "vmess":
            vmess_dict = {
                "v": "2", "ps": data['name'], "add": host_domain, "port": str(selected_port),
                "id": data['uuid'], "aid": "0", "scy": "auto", "net": "ws", "type": "none",
                "host": host_domain, "path": fixed_path, "tls": security_type, "sni": sni_param, "alpn": ""
            }
            vmess_json = json.dumps(vmess_dict)
            vmess_b64 = base64.b64encode(vmess_json.encode('utf-8')).decode('utf-8')
            final_link = f"vmess://{vmess_b64}"
        else:
            final_link = f"vless://{data['uuid']}@{host_domain}:{selected_port}?type=ws&security={security_type}&path={encoded_path}&host={host_domain}{sni_str}#{data['name']}"
        
        quota_display = "بلا حدود ♾️" if data['quota_bytes'] == 0 else f"{data['quota_bytes'] / (1024**3):.2f} GB"
        summary = f"""
✅ **تم إنشاء الكود وتفعيله بالسيرفر بنجاح!**

👤 **الاسم:** `{data['name']}`
🌐 **البروتوكول:** `{protocol.upper()}`
🚪 **البورت:** `{selected_port}`
⏳ **المدة:** `{data['duration_str']}`
📊 **السعة:** `{quota_display}`
🎁 **كود الدعوة الخاص به:** `{new_ref_code}` (يستخدمه لدعوة أصدقائه)

🔗 **انسخ الكود أدناه والصقه في تطبيق (DarkTunnel أو v2rayNG):**
`{final_link}`
        """
        bot.send_message(chat_id, summary, parse_mode="Markdown")
        creation_data.pop(chat_id, None)

        time.sleep(1) 
        success_msg = "🔄 تم الريستارت التلقائي للسيرفر بنجاح! 🚀 الكود هسه شغال للمشترك الجديد."
        fail_msg = "⚠️ الكود انحفظ، بس فشل الريستارت التلقائي."
        restart_alwaysdata(bot, chat_id, success_msg, fail_msg)
