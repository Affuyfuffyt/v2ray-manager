from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import uuid
import random
import string
import json
import base64

# قاموس لحفظ بيانات الإنشاء المؤقتة قبل إرسالها للسيرفر
creation_data = {}

def register_create_handlers(bot):

    # 1. زر إنشاء كود (البداية)
    @bot.callback_query_handler(func=lambda call: call.data == "create_code")
    def start_creation(call):
        chat_id = call.message.chat.id
        msg = bot.send_message(chat_id, "📝 أرسل اسم المشترك (باللغة الإنجليزية وبدون مسافات):")
        bot.register_next_step_handler(msg, process_name, bot)

    def process_name(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id] = {'name': message.text}
        
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("VLESS", callback_data="proto_vless"),
            InlineKeyboardButton("VMESS", callback_data="proto_vmess"),
            InlineKeyboardButton("Trojan", callback_data="proto_trojan")
        )
        bot.send_message(chat_id, "🌐 اختر البروتوكول:", reply_markup=markup)

    # 2. اختيار البروتوكول
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

    # 3. اختيار البورت
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

    # 4. اختيار نوع النقل (WS) وتخطي المسار (Path)
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
        # تم تحديد المسار إجبارياً ليتطابق مع السيرفر
        creation_data[chat_id]['path'] = '/ashor'
        ask_uuid(chat_id, bot, call.message.message_id)

    # 5. اختيار المعرف (UUID)
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

    # 6. تحديد عدد الأجهزة (Concurrent IPs)
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

    # 7. تحديد المدة (Duration)
    def ask_duration(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("يوم", callback_data="dur_1"),
            InlineKeyboardButton("أسبوع", callback_data="dur_7"),
            InlineKeyboardButton("15 يوم", callback_data="dur_15"),
            InlineKeyboardButton("شهر", callback_data="dur_30"),
            InlineKeyboardButton("شهرين", callback_data="dur_60"),
            InlineKeyboardButton("3 أشهر", callback_data="dur_90"),
            InlineKeyboardButton("مدة يدوية ✍️", callback_data="dur_manual")
        )
        text = "⏳ حدد مدة الكود (بالأيام):"
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else:
            bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("dur_"))
    def process_duration(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        
        if choice == "manual":
            msg = bot.send_message(chat_id, "✍️ أرسل المدة بالأيام (أو اكتب صيغة مثل 45):")
            bot.register_next_step_handler(msg, lambda m: save_duration_and_ask_quota(m, bot))
        else:
            creation_data[chat_id]['duration'] = int(choice)
            ask_quota(chat_id, bot, call.message.message_id)

    def save_duration_and_ask_quota(message, bot):
        chat_id = message.chat.id
        try:
            creation_data[chat_id]['duration'] = int(message.text)
            ask_quota(chat_id, bot)
        except ValueError:
            msg = bot.send_message(chat_id, "❌ خطأ! أرسل المدة بالأيام كرقم صحيح:")
            bot.register_next_step_handler(msg, lambda m: save_duration_and_ask_quota(m, bot))

    # 8. تحديد السعة (Quota)
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

    # 9. إعطاء الملخص النهائي والاتصال الفعلي بالسيرفر المحلي
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

        # إضافة المشترك للسيرفر الفعلي
        try:
            from xray_core.panel_api import PanelAPI
            local_api = PanelAPI()
            local_api.create_client(data['name'], data['uuid'])
        except Exception as e:
            print(f"Error connecting to local API: {e}")

        # === التحديث الجديد: إصلاح المسار ديناميكياً ===
        protocol = data.get('protocol', 'vless').lower()
        selected_port = data.get('port', 443)
        host_domain = "wathfor.alwaysdata.net"
        fixed_path = "/ashor" # المسار الثابت للسيرفر
        
        # إعدادات الأمان حسب البورت
        if selected_port == 443:
            security_type = "tls"
            sni_param = host_domain
            sni_str = f"&sni={sni_param}"
        else:
            security_type = "none"
            sni_param = ""
            sni_str = ""

        # توليد الرابط حسب البروتوكول المختار مع إجبار المسار الصحيح
        if protocol == "vless":
            final_link = f"vless://{data['uuid']}@{host_domain}:{selected_port}?type=ws&security={security_type}&path={fixed_path}{sni_str}#{data['name']}"
            
        elif protocol == "trojan":
            final_link = f"trojan://{data['uuid']}@{host_domain}:{selected_port}?type=ws&security={security_type}&path={fixed_path}{sni_str}#{data['name']}"
            
        elif protocol == "vmess":
            vmess_dict = {
                "v": "2",
                "ps": data['name'],
                "add": host_domain,
                "port": str(selected_port),
                "id": data['uuid'],
                "aid": "0",
                "scy": "auto",
                "net": "ws",
                "type": "none",
                "host": host_domain,
                "path": fixed_path,
                "tls": security_type,
                "sni": sni_param,
                "alpn": ""
            }
            vmess_json = json.dumps(vmess_dict)
            vmess_b64 = base64.b64encode(vmess_json.encode('utf-8')).decode('utf-8')
            final_link = f"vmess://{vmess_b64}"
        else:
            final_link = f"vless://{data['uuid']}@{host_domain}:{selected_port}?type=ws&security={security_type}&path={fixed_path}{sni_str}#{data['name']}"
        
        quota_display = "بلا حدود ♾️" if data['quota_bytes'] == 0 else f"{data['quota_bytes'] / (1024**3):.2f} GB"
        
        summary = f"""
✅ **تم إنشاء الكود وتفعيله بالسيرفر بنجاح!**

👤 **الاسم:** `{data['name']}`
🌐 **البروتوكول:** `{protocol.upper()}`
🚪 **البورت:** `{selected_port}`
🛤️ **المسار:** `{fixed_path}`
🔑 **المعرف:** `{data['uuid']}`
👥 **الأجهزة المتصلة:** `{data['ips']}`
⏳ **المدة:** `{data['duration']} أيام`
📊 **السعة:** `{quota_display}`

🔗 **انسخ الكود أدناه والصقه في تطبيق (DarkTunnel أو v2rayNG):**
`{final_link}`
        """
        
        bot.send_message(chat_id, summary, parse_mode="Markdown")
        
        # تنظيف الذاكرة بعد الاكتمال
        creation_data.pop(chat_id, None)
