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
import ftplib
import sqlite3
from io import BytesIO

# 👇 استدعاء دوال الحفظ وقاعدة البيانات
from database import save_user, extend_json_expiry
from db import (
    add_user, get_active_users, set_user_expired, get_user_by_ref_code, 
    extend_user_expiry, assign_ref_code, add_pending_reward, 
    get_all_pending_rewards, remove_pending_reward, get_user_connection_seconds,
    get_all_servers, get_server_details
)

# 👇 استدعاء نظام الإشعارات
try:
    from user_notifier import notify_extension
except ImportError:
    def notify_extension(bot, email, seconds_added): pass

creation_data = {}
add_server_data = {} # 📌 قاموس لحفظ بيانات السيرفر الجديد
watchdog_started = False

# ==========================================
# 🛠️ دالة الإضافة الذكية (تدعم السيرفر المحلي والبعيد)
# ==========================================
def add_client_to_config(user_name, uuid_val, protocol, server_id=1, bot=None, chat_id=None):
    try:
        modified = False
        config_data = {}

        if server_id == 1:
            # 📌 إضافة للسيرفر المحلي (نفس السيرفر)
            home_dir = os.path.expanduser("~")
            config_path = f"{home_dir}/xray_core/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
        else:
            # 🌐 إضافة لسيرفر بعيد عبر FTP المشفر
            server = get_server_details(server_id)
            if not server: return False
            s_id, s_name, s_site_id, s_api, s_host, s_user, s_pass = server
            
            ftp = ftplib.FTP_TLS(s_host)
            ftp.login(s_user, s_pass)
            ftp.prot_p() 
            
            r = BytesIO()
            ftp.retrbinary("RETR xray_core/config.json", r.write)
            config_data = json.loads(r.getvalue().decode('utf-8'))

        # التعديل على ملف الـ JSON المجلوب
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
            if server_id == 1:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4)
            else:
                w = BytesIO(json.dumps(config_data, indent=4).encode('utf-8'))
                ftp.storbinary("STOR xray_core/config.json", w)
                ftp.quit()
        return True
    except Exception as e:
        print(f"Error adding to config: {e}")
        if bot and chat_id: bot.send_message(chat_id, f"⚠️ خطأ في تعديل ملف السيرفر: {e}")
        return False

# ==========================================
# 🗑️ دالة حذف المشترك المنتهي
# ==========================================
def remove_client_from_config(uuid_val, server_id=1):
    try:
        modified = False
        config_data = {}

        if server_id == 1:
            home_dir = os.path.expanduser("~")
            config_path = f"{home_dir}/xray_core/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
        else:
            server = get_server_details(server_id)
            if not server: return
            s_id, s_name, s_site_id, s_api, s_host, s_user, s_pass = server
            
            ftp = ftplib.FTP_TLS(s_host)
            ftp.login(s_user, s_pass)
            ftp.prot_p()
            r = BytesIO()
            ftp.retrbinary("RETR xray_core/config.json", r.write)
            config_data = json.loads(r.getvalue().decode('utf-8'))

        if "inbounds" in config_data:
            for inbound in config_data["inbounds"]:
                if "settings" in inbound and "clients" in inbound["settings"]:
                    original = inbound["settings"]["clients"]
                    new_clients = [c for c in original if c.get("id") != uuid_val and c.get("password") != uuid_val]
                    if len(original) != len(new_clients):
                        inbound["settings"]["clients"] = new_clients
                        modified = True
                        
        if modified:
            if server_id == 1:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, indent=4)
            else:
                w = BytesIO(json.dumps(config_data, indent=4).encode('utf-8'))
                ftp.storbinary("STOR xray_core/config.json", w)
                ftp.quit()
    except Exception as e:
        print(f"Error removing from config: {e}")

# ==========================================
# 🔄 دالة عمل ريستارت للسيرفر (مركزي)
# ==========================================
def restart_alwaysdata(bot=None, chat_id=None, success_msg=None, fail_msg=None, server_id=1):
    try:
        if server_id == 1:
            home_dir = os.path.expanduser("~")
            key_file = f"{home_dir}/alwaysdata_keys.txt"
            if os.path.exists(key_file):
                with open(key_file, 'r') as f:
                    lines = f.read().strip().split('\n')
                    if len(lines) >= 2:
                        SITE_ID = lines[0].strip()
                        API_KEY = lines[1].strip()
        else:
            server = get_server_details(server_id)
            if not server: return False
            SITE_ID = server[2]
            API_KEY = server[3]
            
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
def auto_restart_on_expiry(bot, chat_id, expiry_time, user_name, uuid_val, protocol, server_id=1):
    wait_seconds = expiry_time - time.time()
    if wait_seconds > 0:
        time.sleep(wait_seconds) 
        
    if protocol != "trojan" and server_id == 1:
        try:
            from xray_core.panel_api import PanelAPI
            local_api = PanelAPI()
            try: local_api.delete_client(user_name)
            except: pass
            try: local_api.remove_client(uuid_val)
            except: pass
        except: pass
    
    remove_client_from_config(uuid_val, server_id)
    success_msg = f"🛑 **تنبيه انتهاء صلاحية!** 🛑\n\n👤 المشترك: `{user_name}`\n⏳ انتهى وقته للتو.\n🔄 **تم سحب صلاحيته من السيرفر نهائياً!**"
    fail_msg = f"⚠️ انتهى وقت `{user_name}` ولكن فشل الريستارت التلقائي للسيرفر!"
    restart_alwaysdata(bot, chat_id, success_msg, fail_msg, server_id)

# ==========================================
# 👁️ مراقب قاعدة البيانات
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
            active_users = get_active_users() 
            current_time = time.time()
            expired_by_server = {}
            
            for email, uuid_val, expiry_date, s_id in active_users:
                if expiry_date and current_time >= float(expiry_date):
                    remove_client_from_config(uuid_val, s_id)
                    set_user_expired(email)
                    if s_id not in expired_by_server: expired_by_server[s_id] = []
                    expired_by_server[s_id].append(email)
                    
            if admin_id:
                for s_id, names in expired_by_server.items():
                    success = restart_alwaysdata(server_id=s_id)
                    names_str = "\n".join([f"• `{n}`" for n in names])
                    if success:
                        msg = f"🛑 **تنبيه الطرد التلقائي!** 🛑\n\nالمنتهين في سيرفر ({s_id}):\n{names_str}\n\n🔄 **تم سحب الصلاحيات وعمل ريستارت للسيرفر لطردهم!**"
                    else:
                        msg = f"⚠️ تم مسح المشتركين ({names_str}) من السيرفر ({s_id}) ولكن فشل الريستارت!"
                    bot.send_message(admin_id, msg, parse_mode="Markdown")

            pending_rewards = get_all_pending_rewards()
            for ref_email, inv_email, reward_sec, c_id in pending_rewards:
                if get_user_connection_seconds(inv_email) >= 60:
                    extend_user_expiry(ref_email, reward_sec)
                    try: extend_json_expiry(ref_email, reward_sec)
                    except: pass
                    remove_pending_reward(inv_email)
                    
                    bot.send_message(c_id, f"🎉 **تم تفعيل المكافأة المعلقة!**\n\nتم تمديد وقت المشترك الداعي `{ref_email}` بنجاح لأن المشترك الجديد اتصل بالإنترنت! 🚀", parse_mode="Markdown")
                    notify_extension(bot, ref_email, reward_sec)
        except Exception as e:
            pass
        time.sleep(60)

# ==========================================
# 🆕 بناء وتوزيع الكود + 🌐 إضافة السيرفرات الذكية والعميقة
# ==========================================
def register_create_handlers(bot):
    global watchdog_started
    if not watchdog_started:
        threading.Thread(target=database_expiry_watchdog, args=(bot,), daemon=True).start()
        watchdog_started = True

    # -----------------------------------------------------------------
    # 🔥 ميزة إضافة سيرفر جديد مخصص بالكامل (بالتسلسل المطلوب 1 إلى 12) 🔥
    # -----------------------------------------------------------------
    @bot.message_handler(commands=['add_server'])
    def start_add_server(message):
        msg = bot.send_message(message.chat.id, "1️⃣ أرسل **كود SSH** للاتصال بالسيرفر\n(مثال: `ssh linkapp@ssh-linkapp.alwaysdata.net`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_ssh)

    def process_add_ssh(message):
        add_server_data[message.chat.id] = {'ssh': message.text.strip()}
        msg = bot.send_message(message.chat.id, "2️⃣ أرسل **يوزر السيرفر** (FTP User):")
        bot.register_next_step_handler(msg, process_add_user)

    def process_add_user(message):
        add_server_data[message.chat.id]['user'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "3️⃣ أرسل **باسورد السيرفر** (FTP Password):")
        bot.register_next_step_handler(msg, process_add_pass)

    def process_add_pass(message):
        add_server_data[message.chat.id]['pass'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "4️⃣ أرسل **كود تثبيت الأداة** في السيرفر الجديد\n(مثال: `curl -sO https://raw.githubusercontent.com/.../install.sh && bash install.sh`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_curl)

    def process_add_curl(message):
        add_server_data[message.chat.id]['curl_cmd'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "5️⃣ أرسل **توكن البوت** (Bot Token):")
        bot.register_next_step_handler(msg, process_add_bot_token)

    def process_add_bot_token(message):
        add_server_data[message.chat.id]['bot_token'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "6️⃣ أرسل **آيدي الأدمن** (Admin ID):")
        bot.register_next_step_handler(msg, process_add_admin_id)

    def process_add_admin_id(message):
        add_server_data[message.chat.id]['admin_id'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "7️⃣ أرسل **الأمر المخصص** الذي سيشغل واجهة هذا السيرفر بالبوت\n(مثال: `/linkapp`):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_custom_cmd)

    def process_add_custom_cmd(message):
        cmd_text = message.text.strip()
        if not cmd_text.startswith('/'):
            cmd_text = '/' + cmd_text
        add_server_data[message.chat.id]['custom_cmd'] = cmd_text
        msg = bot.send_message(message.chat.id, "8️⃣ أرسل **اسم السيرفر** (الاسم الذي سيظهر في لوحة التحكم):")
        bot.register_next_step_handler(msg, process_add_name)

    def process_add_name(message):
        add_server_data[message.chat.id]['name'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "9️⃣ أرسل **API Key** الخاص بالسيرفر:")
        bot.register_next_step_handler(msg, process_add_api)

    def process_add_api(message):
        add_server_data[message.chat.id]['api'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "🔟 أرسل **ID السيرفر** (Site ID):")
        bot.register_next_step_handler(msg, process_add_id)

    def process_add_id(message):
        add_server_data[message.chat.id]['id'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "1️⃣1️⃣ أرسل **هوست السيرفر** (Domain)\n(مثال: `linkapp.alwaysdata.net`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_host)

    def process_add_host(message):
        add_server_data[message.chat.id]['host'] = message.text.strip()
        msg = bot.send_message(message.chat.id, "1️⃣2️⃣ أرسل **كود التشغيل** (Command Xray)\n(مثال: `/home/linkapp/xray_core/xray run -c /home/linkapp/xray_core/config.json /home/linkapp/xray_core/ userprogram`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_add_cmd)

    def process_add_cmd(message):
        add_server_data[message.chat.id]['run_cmd'] = message.text.strip()
        finalize_add_server(message)

    def finalize_add_server(message):
        chat_id = message.chat.id
        data = add_server_data[chat_id]
        bot.send_message(chat_id, "⏳ جاري إرسال الإعدادات وتثبيت ملفات الكونفيك والبانيل المخصصة بالسيرفر الجديد...")
        
        ftp_user = data['user']
        ftp_pass = data['pass']
        ftp_host = data['host']
        
        if not ftp_host.startswith("ftp-"):
            ftp_host = f"ftp-{ftp_host}"

        # 1. الدخول للسيرفر عبر SSH وتنفيذ أداة التثبيت مع تمرير الإجابات تلقائياً
        try:
            import paramiko
            ssh_target = data['ssh'].replace('ssh ', '')
            ssh_user = ssh_target.split('@')[0]
            ssh_host_ip = ssh_target.split('@')[1]
            
            bot.send_message(chat_id, "⚙️ جاري الدخول للسيرفر عبر SSH وتنفيذ أداة التثبيت تلقائياً...")
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(ssh_host_ip, username=ssh_user, password=ftp_pass, timeout=15)
            
            # تمرير الإجابات بالتسلسل للسكربت حتى يتثبت بدون أن يتوقف
            stdin, stdout, stderr = ssh_client.exec_command(data['curl_cmd'])
            input_data = f"{data['bot_token']}\n{data['admin_id']}\n{data['api']}\n{data['id']}\n{data['host']}\n{ftp_user}\n"
            stdin.write(input_data)
            stdin.flush()
            
            stdout.channel.recv_exit_status() # انتظار انتهاء التثبيت
            ssh_client.close()
        except ImportError:
            bot.send_message(chat_id, "⚠️ ملاحظة: لم يتم تثبيت مكتبة paramiko في هذا السيرفر، سيتم تجاهل خطوة SSH والاعتماد على FTP.")
        except Exception as e:
            bot.send_message(chat_id, f"⚠️ خطأ في اتصال SSH: {e}\nسيتم الاعتماد على FTP لرفع الملفات.")

        # 2. بناء ملف Config.json الخاص بالسيرفر الجديد
        node_config = {
          "log": {
            "access": f"/home/{ftp_user}/xray_core/access.log",
            "error": f"/home/{ftp_user}/xray_core/error.log",
            "loglevel": "warning"
          },
          "stats": {},
          "api": {
            "tag": "api",
            "services": ["StatsService", "HandlerService", "LoggerService", "ReflectionService"]
          },
          "policy": {
            "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}},
            "system": {"statsInboundUplink": True, "statsInboundDownlink": True, "statsOutboundUplink": True, "statsOutboundDownlink": True}
          },
          "inbounds": [
            {
              "tag": "vless_tcp_fallback", "port": 8100, "listen": "0.0.0.0", "protocol": "vless",
              "settings": {
                "clients": [], "decryption": "none",
                "fallbacks": [
                  {"path": "/Telegram-@338888-vless", "dest": 8101},
                  {"path": "/Telegram-@338888-vmess", "dest": 8102},
                  {"path": "/Telegram-@338888-trojan", "dest": 8103}
                ]
              },
              "streamSettings": {"network": "tcp"}
            },
            {
              "tag": "vless", "port": 8101, "listen": "127.0.0.1", "protocol": "vless",
              "settings": {"clients": [], "decryption": "none"},
              "streamSettings": {"network": "ws", "wsSettings": {"path": "/Telegram-@338888-vless"}}
            },
            {
              "tag": "vmess", "port": 8102, "listen": "127.0.0.1", "protocol": "vmess",
              "settings": {"clients": []},
              "streamSettings": {"network": "ws", "wsSettings": {"path": "/Telegram-@338888-vmess"}}
            },
            {
              "tag": "trojan", "port": 8103, "listen": "127.0.0.1", "protocol": "trojan",
              "settings": {"clients": []},
              "streamSettings": {"network": "ws", "wsSettings": {"path": "/Telegram-@338888-trojan"}}
            },
            {
              "port": 10086, "listen": "127.0.0.1", "protocol": "dokodemo-door",
              "settings": {"address": "127.0.0.1"}, "tag": "api"
            }
          ],
          "outbounds": [
            {"protocol": "freedom", "tag": "freedom"},
            {"protocol": "blackhole", "tag": "api"}
          ],
          "routing": {
            "rules": [{"inboundTag": ["api"], "outboundTag": "api", "type": "field"}]
          }
        }
        
        # 3. بناء ملف panel_api.py خاص
        panel_script = f"""import json
import os
import time

CONFIG_PATH = '/home/{ftp_user}/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        pass

    def create_client(self, email, uuid, protocol="vless"):
        try:
            if not os.path.exists(CONFIG_PATH):
                return False
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            main_inbound = 0
            if protocol == "vless" or protocol == "vmess":
                new_client = {{"id": uuid, "email": email, "level": 0}}
            elif protocol == "trojan":
                new_client = {{"password": uuid, "email": email, "level": 0}} 
            else:
                new_client = {{"id": uuid, "email": email, "level": 0}}

            clients_main = config['inbounds'][main_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_main):
                clients_main.append(new_client)

            target_map = {{"vless": 1, "vmess": 2, "trojan": 3}}
            target_inbound = target_map.get(protocol.lower(), 1)
            
            clients_ws = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_ws):
                clients_ws.append(new_client)
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
        except Exception as e:
            return False

    def restart_xray(self):
        os.system("pkill -9 xray")
        time.sleep(0.5)
        return True

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            changed = False
            for i in range(4): 
                try:
                    clients = config['inbounds'][i]['settings']['clients']
                    if not enable:
                        original_len = len(clients)
                        config['inbounds'][i]['settings']['clients'] = [c for c in clients if c.get('email') != email]
                        if len(config['inbounds'][i]['settings']['clients']) != original_len:
                            changed = True
                except Exception:
                    continue
            
            if changed:
                with open(CONFIG_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
                return self.restart_xray()
            return True
        except Exception as e:
            return False
"""

        # 4. رفع الملفات عبر FTP المشفر لضمان أن كل شيء في مكانه
        try:
            ftp = ftplib.FTP_TLS(ftp_host)
            ftp.login(ftp_user, ftp_pass)
            ftp.prot_p()
            
            try: ftp.mkd('xray_core')
            except: pass
            
            config_bytes = BytesIO(json.dumps(node_config, indent=4).encode('utf-8'))
            ftp.storbinary("STOR xray_core/config.json", config_bytes)
            
            panel_bytes = BytesIO(panel_script.encode('utf-8'))
            ftp.storbinary("STOR xray_core/panel_api.py", panel_bytes)
            ftp.quit()
            
            # 5. تشغيل السيرفر لفحص نجاح العملية
            url = f"https://api.alwaysdata.com/v1/site/{data['id']}/restart/"
            resp = requests.post(url, auth=(data['api'], ''))
            
            if resp.status_code in [200, 201, 202, 204]:
                # 6. حفظ السيرفر بقاعدة البيانات وحفظ أمر الواجهة
                try:
                    conn = sqlite3.connect('bot_database.db')
                    c = conn.cursor()
                    c.execute('''INSERT INTO servers (name, site_id, api_key, host, user, password, status)
                                 VALUES (?, ?, ?, ?, ?, ?, 'active')''',
                              (data['name'], data['id'], data['api'], ftp_host, data['user'], data['pass']))
                    conn.commit()
                    conn.close()
                    
                    # حفظ الأمر المخصص لتشغيل واجهة السيرفر (مثلاً /linkapp) بملف json مستقل للوصول السريع
                    mapping_file = "server_commands.json"
                    mapping = {}
                    if os.path.exists(mapping_file):
                        with open(mapping_file, 'r') as mf:
                            mapping = json.load(mf)
                    
                    mapping[data['custom_cmd']] = data['name']
                    with open(mapping_file, 'w') as mf:
                        json.dump(mapping, mf, indent=4, ensure_ascii=False)
                        
                except Exception as db_e:
                    print("DB Error: ", db_e)
                    
                bot.send_message(chat_id, f"✅ **تم إنشاء وإضافة السيرفر بنجاح!**\n\n🖥️ **اسم السيرفر:** `{data['name']}`\n🌐 **الهوست:** `{ftp_host}`\n✅ **الملفات:** تم الرفع بنجاح.\n🔑 **أمر التشغيل الخاص بهذا السيرفر:** `{data['custom_cmd']}`\n🔄 **حالة التشغيل:** السيرفر يعمل بشكل ممتاز.\n\nالآن يمكنك استخدام الأمر المخصص لفتح واجهة إدارة هذا السيرفر.", parse_mode="Markdown")
            else:
                bot.send_message(chat_id, f"❌ تم رفع الملفات، ولكن فشل تشغيل السيرفر! تأكد من الـ Site ID والـ API. كود الخطأ: {resp.status_code}")
                
        except Exception as e:
            bot.send_message(chat_id, f"❌ حدث خطأ أثناء الاتصال بالـ FTP ورفع الملفات:\n`{str(e)}`\nتأكد أن السيرفر يعمل أو أن بيانات FTP صحيحة.", parse_mode="Markdown")

    # ----------------------------------------------------
    # دوال صناعة الأكواد للمشتركين
    # ----------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data == "create_code")
    def start_creation(call):
        chat_id = call.message.chat.id
        servers = get_all_servers()
        
        if not servers:
            bot.send_message(chat_id, "❌ لا توجد سيرفرات متاحة. يرجى تهيئة قاعدة البيانات أو إضافة سيرفر.")
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        for s in servers:
            s_id, s_name, s_site_id, s_status = s
            if s_status == 'active':
                markup.add(InlineKeyboardButton(f"🖥️ {s_name}", callback_data=f"sel_srv_{s_id}"))
                
        bot.edit_message_text("🌐 **في أي سيرفر تريد إنشاء المشترك؟**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sel_srv_"))
    def process_server_selection(call):
        chat_id = call.message.chat.id
        server_id = int(call.data.split("_")[2])
        creation_data[chat_id] = {'server_id': server_id}
        
        msg = bot.send_message(chat_id, "📝 أرسل اسم المشترك (باللغة الإنجليزية وبدون مسافات):")
        bot.register_next_step_handler(msg, process_name, bot)

    def process_name(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id]['name'] = message.text.strip()
        
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
            try: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            except: bot.send_message(chat_id, text, reply_markup=markup)
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
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

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
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

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
        markup.add(InlineKeyboardButton("متصل واحد 📱", callback_data="ip_1"), InlineKeyboardButton("العدد يدوي ✍️", callback_data="ip_manual"))
        text = "👥 حدد عدد الأجهزة المسموحة:"
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

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
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

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
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

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
        server_id = data.get('server_id', 1)
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

        bot.send_message(chat_id, "⏳ جاري زراعة الكود في السيرفر المطلوب، يرجى الانتظار...")
        success = add_client_to_config(data['name'], data['uuid'], protocol, server_id, bot, chat_id)
        
        if not success:
            bot.send_message(chat_id, "❌ فشلت عملية الإضافة للسيرفر البعيد! تأكد من بيانات FTP.")
            creation_data.pop(chat_id, None)
            return

        try: save_user(data['name'], data['uuid'], data['quota_bytes'], expiry_time)
        except: pass

        try:
            selected_port = data.get('port', 443)
            add_user(data['name'], data['uuid'], selected_port, data['quota_bytes'], expiry_time, server_id)
        except Exception as e: print(f"Error saving to SQLite DB: {e}")

        new_ref_code = "REF-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        try: assign_ref_code(data['name'], new_ref_code)
        except: pass

        reward_sec = data.get('reward_seconds')
        referrer_email = data.get('referrer')
        if reward_sec and referrer_email:
            try: add_pending_reward(referrer_email, data['name'], reward_sec, chat_id)
            except: pass

        threading.Thread(
            target=auto_restart_on_expiry, 
            args=(bot, chat_id, expiry_time, data['name'], data['uuid'], protocol, server_id), 
            daemon=True
        ).start()

        selected_port = data.get('port', 443)
        host_domain = "wathfor.alwaysdata.net" 
        
        if server_id == 1:
            try:
                home_dir = os.path.expanduser("~")
                key_file = f"{home_dir}/alwaysdata_keys.txt"
                if os.path.exists(key_file):
                    with open(key_file, 'r') as f:
                        lines = f.read().strip().split('\n')
                        if len(lines) >= 3 and lines[2].strip() != "":
                            host_domain = lines[2].strip()
            except: pass
        else:
            srv = get_server_details(server_id)
            if srv:
                raw_host = srv[5]
                if raw_host.startswith("ftp-"):
                    raw_host = raw_host[4:]
                host_domain = raw_host
        
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
        
        srv_name = "السيرفر المحلي" if server_id == 1 else srv[1]
        summary = f"""
✅ **تم إنشاء الكود وتفعيله بنجاح!**

🖥️ **السيرفر المستخدم:** `{srv_name}`
👤 **الاسم:** `{data['name']}`
🌐 **البروتوكول:** `{protocol.upper()}`
🚪 **البورت:** `{selected_port}`
⏳ **المدة:** `{data['duration_str']}`
📊 **السعة:** `{quota_display}`
🎁 **كود الدعوة الخاص به:** `{new_ref_code}`

🔗 **انسخ الكود أدناه والصقه في تطبيق (متجر اشور أو v2rayNG):**
`{final_link}`
        """
        bot.send_message(chat_id, summary, parse_mode="Markdown")
        creation_data.pop(chat_id, None)

        time.sleep(1) 
        success_msg = f"🔄 تم الريستارت التلقائي للسيرفر ({srv_name}) بنجاح! 🚀 الكود هسه شغال."
        fail_msg = f"⚠️ الكود انحفظ، بس فشل الريستارت التلقائي للسيرفر ({srv_name})."
        restart_alwaysdata(bot, chat_id, success_msg, fail_msg, server_id)
