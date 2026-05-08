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
from io import BytesIO

# ًں‘‡ ط§ط³طھط¯ط¹ط§ط، ط¯ظˆط§ظ„ ط§ظ„ط­ظپط¸ ظˆظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ
from database import save_user, extend_json_expiry
from db import (
    add_user, get_active_users, set_user_expired, get_user_by_ref_code, 
    extend_user_expiry, assign_ref_code, add_pending_reward, 
    get_all_pending_rewards, remove_pending_reward, get_user_connection_seconds,
    get_all_servers, get_server_details
)

# ًں‘‡ ط§ط³طھط¯ط¹ط§ط، ظ†ط¸ط§ظ… ط§ظ„ط¥ط´ط¹ط§ط±ط§طھ
try:
    from user_notifier import notify_extension
except ImportError:
    def notify_extension(bot, email, seconds_added): pass

creation_data = {}
watchdog_started = False

# ==========================================
# ًں› ï¸ڈ ط¯ط§ظ„ط© ط§ظ„ط¥ط¶ط§ظپط© ط§ظ„ط°ظƒظٹط© (طھط¯ط¹ظ… ط§ظ„ط³ظٹط±ظپط± ط§ظ„ظ…ط­ظ„ظٹ ظˆط§ظ„ط¨ط¹ظٹط¯)
# ==========================================
def add_client_to_config(user_name, uuid_val, protocol, server_id=1, bot=None, chat_id=None):
    try:
        modified = False
        config_data = {}

        if server_id == 1:
            # ًں“Œ ط¥ط¶ط§ظپط© ظ„ظ„ط³ظٹط±ظپط± ط§ظ„ظ…ط­ظ„ظٹ (ظ†ظپط³ ط§ظ„ط³ظٹط±ظپط±)
            home_dir = os.path.expanduser("~")
            config_path = f"{home_dir}/xray_core/config.json"
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
        else:
            # ًںŒگ ط¥ط¶ط§ظپط© ظ„ط³ظٹط±ظپط± ط¨ط¹ظٹط¯ ط¹ط¨ط± FTP
            server = get_server_details(server_id)
            if not server: return False
            s_id, s_name, s_site_id, s_api, s_host, s_user, s_pass = server
            
            ftp = ftplib.FTP(s_host)
            ftp.login(s_user, s_pass)
            
            r = BytesIO()
            ftp.retrbinary("RETR xray_core/config.json", r.write)
            config_data = json.loads(r.getvalue().decode('utf-8'))

        # ط§ظ„طھط¹ط¯ظٹظ„ ط¹ظ„ظ‰ ظ…ظ„ظپ ط§ظ„ظ€ JSON ط§ظ„ظ…ط¬ظ„ظˆط¨
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
        if bot and chat_id: bot.send_message(chat_id, f"âڑ ï¸ڈ ط®ط·ط£ ظپظٹ طھط¹ط¯ظٹظ„ ظ…ظ„ظپ ط§ظ„ط³ظٹط±ظپط±: {e}")
        return False

# ==========================================
# ًں—‘ï¸ڈ ط¯ط§ظ„ط© ط­ط°ظپ ط§ظ„ظ…ط´طھط±ظƒ ط§ظ„ظ…ظ†طھظ‡ظٹ
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
            ftp = ftplib.FTP(s_host)
            ftp.login(s_user, s_pass)
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
# ًں”„ ط¯ط§ظ„ط© ط¹ظ…ظ„ ط±ظٹط³طھط§ط±طھ ظ„ظ„ط³ظٹط±ظپط± (ظ…ط±ظƒط²ظٹ)
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
                bot.send_message(chat_id, f"{fail_msg}\nظƒظˆط¯ ط§ظ„ط®ط·ط£: {response.status_code}")
        return response.status_code in [200, 201, 202, 204]
    except Exception as e:
        if bot and chat_id: bot.send_message(chat_id, "âڑ ï¸ڈ ط­ط¯ط« ط®ط·ط£ ظپظٹ ط§ظ„ط§طھطµط§ظ„ ط¨ظ…ظ†طµط© Alwaysdata.")
        print(f"Restart Error: {e}")
    return False

# ==========================================
# âڈ±ï¸ڈ ط§ظ„ط¹ط¯ط§ط¯ ط§ظ„طھظ†ط§ط²ظ„ظٹ ظ„ط·ط±ط¯ ط§ظ„ظ…ط´طھط±ظƒ
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
    success_msg = f"ًں›‘ **طھظ†ط¨ظٹظ‡ ط§ظ†طھظ‡ط§ط، طµظ„ط§ط­ظٹط©!** ًں›‘\n\nًں‘¤ ط§ظ„ظ…ط´طھط±ظƒ: `{user_name}`\nâڈ³ ط§ظ†طھظ‡ظ‰ ظˆظ‚طھظ‡ ظ„ظ„طھظˆ.\nًں”„ **طھظ… ط³ط­ط¨ طµظ„ط§ط­ظٹطھظ‡ ظ…ظ† ط§ظ„ط³ظٹط±ظپط± ظ†ظ‡ط§ط¦ظٹط§ظ‹!**"
    fail_msg = f"âڑ ï¸ڈ ط§ظ†طھظ‡ظ‰ ظˆظ‚طھ `{user_name}` ظˆظ„ظƒظ† ظپط´ظ„ ط§ظ„ط±ظٹط³طھط§ط±طھ ط§ظ„طھظ„ظ‚ط§ط¦ظٹ ظ„ظ„ط³ظٹط±ظپط±!"
    restart_alwaysdata(bot, chat_id, success_msg, fail_msg, server_id)


# ==========================================
# ًں‘پï¸ڈ ظ…ط±ط§ظ‚ط¨ ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ
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
            # 1. ظ…ط±ط§ظ‚ط¨ط© ط§ظ†طھظ‡ط§ط، ط§ظ„ظ…ط´طھط±ظƒظٹظ†
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
                    names_str = "\n".join([f"â€¢ `{n}`" for n in names])
                    if success:
                        msg = f"ًں›‘ **طھظ†ط¨ظٹظ‡ ط§ظ„ط·ط±ط¯ ط§ظ„طھظ„ظ‚ط§ط¦ظٹ!** ًں›‘\n\nط§ظ„ظ…ظ†طھظ‡ظٹظ† ظپظٹ ط³ظٹط±ظپط± ({s_id}):\n{names_str}\n\nًں”„ **طھظ… ط³ط­ط¨ ط§ظ„طµظ„ط§ط­ظٹط§طھ ظˆط¹ظ…ظ„ ط±ظٹط³طھط§ط±طھ ظ„ظ„ط³ظٹط±ظپط± ظ„ط·ط±ط¯ظ‡ظ…!**"
                    else:
                        msg = f"âڑ ï¸ڈ طھظ… ظ…ط³ط­ ط§ظ„ظ…ط´طھط±ظƒظٹظ† ({names_str}) ظ…ظ† ط§ظ„ط³ظٹط±ظپط± ({s_id}) ظˆظ„ظƒظ† ظپط´ظ„ ط§ظ„ط±ظٹط³طھط§ط±طھ!"
                    bot.send_message(admin_id, msg, parse_mode="Markdown")

            # 2. ظ…ط±ط§ظ‚ط¨ط© ط§ظ„ظ…ظƒط§ظپط¢طھ ط§ظ„ظ…ط¹ظ„ظ‚ط©
            pending_rewards = get_all_pending_rewards()
            for ref_email, inv_email, reward_sec, c_id in pending_rewards:
                if get_user_connection_seconds(inv_email) >= 60:
                    extend_user_expiry(ref_email, reward_sec)
                    try: extend_json_expiry(ref_email, reward_sec)
                    except: pass
                    remove_pending_reward(inv_email)
                    
                    bot.send_message(c_id, f"ًںژ‰ **طھظ… طھظپط¹ظٹظ„ ط§ظ„ظ…ظƒط§ظپط£ط© ط§ظ„ظ…ط¹ظ„ظ‚ط©!**\n\nطھظ… طھظ…ط¯ظٹط¯ ظˆظ‚طھ ط§ظ„ظ…ط´طھط±ظƒ ط§ظ„ط¯ط§ط¹ظٹ `{ref_email}` ط¨ظ†ط¬ط§ط­ ظ„ط£ظ† ط§ظ„ظ…ط´طھط±ظƒ ط§ظ„ط¬ط¯ظٹط¯ ط§طھطµظ„ ط¨ط§ظ„ط¥ظ†طھط±ظ†طھ! ًںڑ€", parse_mode="Markdown")
                    notify_extension(bot, ref_email, reward_sec)
        except Exception as e:
            pass
        time.sleep(60)

# ==========================================
# ًں†• ط¨ظ†ط§ط، ظˆطھظˆط²ظٹط¹ ط§ظ„ظƒظˆط¯
# ==========================================
def register_create_handlers(bot):
    global watchdog_started
    if not watchdog_started:
        threading.Thread(target=database_expiry_watchdog, args=(bot,), daemon=True).start()
        watchdog_started = True

    # ًں”¥ ط§ظ„طھط­ط¯ظٹط«: ط§ط®طھظٹط§ط± ط§ظ„ط³ظٹط±ظپط± ط£ظˆظ„ط§ظ‹ ًں”¥
    @bot.callback_query_handler(func=lambda call: call.data == "create_code")
    def start_creation(call):
        chat_id = call.message.chat.id
        servers = get_all_servers()
        
        if not servers:
            bot.send_message(chat_id, "â‌Œ ظ„ط§ طھظˆط¬ط¯ ط³ظٹط±ظپط±ط§طھ ظ…طھط§ط­ط©. ظٹط±ط¬ظ‰ طھظ‡ظٹط¦ط© ظ‚ط§ط¹ط¯ط© ط§ظ„ط¨ظٹط§ظ†ط§طھ ط£ظˆ ط¥ط¶ط§ظپط© ط³ظٹط±ظپط±.")
            return
            
        markup = InlineKeyboardMarkup(row_width=1)
        for s in servers:
            s_id, s_name, s_site_id, s_status = s
            if s_status == 'active':
                markup.add(InlineKeyboardButton(f"ًں–¥ï¸ڈ {s_name}", callback_data=f"sel_srv_{s_id}"))
                
        bot.edit_message_text("ًںŒگ **ظپظٹ ط£ظٹ ط³ظٹط±ظپط± طھط±ظٹط¯ ط¥ظ†ط´ط§ط، ط§ظ„ظ…ط´طھط±ظƒطں**", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("sel_srv_"))
    def process_server_selection(call):
        chat_id = call.message.chat.id
        server_id = int(call.data.split("_")[2])
        creation_data[chat_id] = {'server_id': server_id}
        
        msg = bot.send_message(chat_id, "ًں“‌ ط£ط±ط³ظ„ ط§ط³ظ… ط§ظ„ظ…ط´طھط±ظƒ (ط¨ط§ظ„ظ„ط؛ط© ط§ظ„ط¥ظ†ط¬ظ„ظٹط²ظٹط© ظˆط¨ط¯ظˆظ† ظ…ط³ط§ظپط§طھ):")
        bot.register_next_step_handler(msg, process_name, bot)

    def process_name(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id]['name'] = message.text.strip()
        
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("âڈ­ï¸ڈ طھط®ط·ظٹ ظƒظˆط¯ ط§ظ„ط¯ط¹ظˆط©", callback_data="skip_referral"))
        msg = bot.send_message(chat_id, "ًںژپ **ظ†ط¸ط§ظ… ط§ظ„ظ…ظƒط§ظپط¢طھ ظˆط§ظ„ط¯ط¹ظˆط§طھ:**\nط¥ط°ط§ ظƒط§ظ† ط§ظ„ظ…ط´طھط±ظƒ ظ‚ط§ط¯ظ…ط§ظ‹ ط¹ظ† ط·ط±ظٹظ‚ ط´ط®طµ ط¢ط®ط±طŒ ط£ط±ط³ظ„ (ظƒظˆط¯ ط¯ط¹ظˆط©) ط§ظ„ط´ط®طµ ط§ظ„ط¯ط§ط¹ظٹ ط§ظ„ط¢ظ† ظ„ظٹطھظ… ظ…ظƒط§ظپط£طھظ‡.\n\nًں‘‡ ط£ظˆ ط§ط¶ط؛ط· طھط®ط·ظٹ ظ„ظ„ط§ط³طھظ…ط±ط§ط±:", reply_markup=markup, parse_mode="Markdown")
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
                InlineKeyboardButton("طھظ…ط¯ظٹط¯ 5 ط£ظٹط§ظ… ًںژپ", callback_data="rew_5"),
                InlineKeyboardButton("طھظ…ط¯ظٹط¯ 10 ط£ظٹط§ظ… ًںژپ", callback_data="rew_10"),
                InlineKeyboardButton("طھظ…ط¯ظٹط¯ 30 ظٹظˆظ… ًںژپ", callback_data="rew_30"),
                InlineKeyboardButton("ط¥ط¯ط®ط§ظ„ ظٹط¯ظˆظٹ âœچï¸ڈ", callback_data="rew_manual"),
                InlineKeyboardButton("ط¥ظ„ط؛ط§ط، ط§ظ„طھظ…ط¯ظٹط¯ ظˆط§ظ„طھط®ط·ظٹ âڈ­ï¸ڈ", callback_data="skip_referral")
            )
            bot.send_message(chat_id, f"âœ… **ظƒظˆط¯ طµط­ظٹط­!**\nظ‡ط°ط§ ط§ظ„ظƒظˆط¯ ظٹط¹ظˆط¯ ظ„ظ„ظ…ط´طھط±ظƒ: `{referrer_email}`\n\nط§ط®طھط± ظƒظ… طھط±ظٹط¯ ط£ظ† طھظ…ط¯ط¯ طµظ„ط§ط­ظٹطھظ‡ ظƒظ…ظƒط§ظپط£ط© ظ„ظ„ط¯ط¹ظˆط©:", reply_markup=markup, parse_mode="Markdown")
        else:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("âڈ­ï¸ڈ ط§ظ„ط§ط³طھظ…ط±ط§ط± ط¨ط¯ظˆظ† ظ…ظƒط§ظپط£ط© (طھط®ط·ظٹ)", callback_data="skip_referral"))
            msg = bot.send_message(chat_id, "â‌Œ ظƒظˆط¯ ط§ظ„ط¯ط¹ظˆط© ط؛ظٹط± طµط­ظٹط­ ط£ظˆ ط؛ظٹط± ظ…ظˆط¬ظˆط¯!\nطھط£ظƒط¯ ظ…ظ† ط§ظ„ظƒظˆط¯ ظˆط£ط±ط³ظ„ظ‡ ظ…ط¬ط¯ط¯ط§ظ‹طŒ ط£ظˆ ط§ط¶ط؛ط· طھط®ط·ظٹ:", reply_markup=markup)
            bot.register_next_step_handler(msg, check_referral_text, bot)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("rew_"))
    def process_reward(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]

        if choice == "manual":
            bot.clear_step_handler_by_chat_id(chat_id)
            msg = bot.send_message(chat_id, "âœچï¸ڈ ط£ط±ط³ظ„ ظ…ط¯ط© ط§ظ„طھظ…ط¯ظٹط¯:\n(ظ…ط«ط§ظ„: `5m` ظ„ط¯ظ‚ط§ط¦ظ‚طŒ `2h` ظ„ط³ط§ط¹ط§طھطŒ `10d` ظ„ط£ظٹط§ظ…طŒ `1mo` ظ„ط´ظ‡ط±)", parse_mode="Markdown")
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
            msg = bot.send_message(chat_id, "â‌Œ طµظٹط؛ط© ط®ط§ط·ط¦ط©! ط­ط§ظˆظ„ ظ…ط¬ط¯ط¯ط§ظ‹ (ظ…ط«ط§ظ„: `5m`, `2h`, `10d`, `1mo`):", parse_mode="Markdown")
            bot.register_next_step_handler(msg, manual_reward_input, bot)
            return
            
        apply_reward(chat_id, bot, sec)

    def apply_reward(chat_id, bot, seconds):
        referrer_email = creation_data[chat_id].get('referrer')
        if referrer_email:
            creation_data[chat_id]['reward_seconds'] = seconds
            bot.send_message(chat_id, f"âڈ³ **طھظ… طھط¹ظ„ظٹظ‚ ط§ظ„ظ…ظƒط§ظپط£ط©!**\nط³ظٹطھظ… طھظپط¹ظٹظ„ ط§ظ„ظ…ظƒط§ظپط£ط© ظ„ظ„ط¯ط§ط¹ظٹ `{referrer_email}` **طھظ„ظ‚ط§ط¦ظٹط§ظ‹** ط¨ط¹ط¯ ط£ظ† ظٹطھطµظ„ ط§ظ„ظ…ط´طھط±ظƒ ط§ظ„ط¬ط¯ظٹط¯ ط¨ط§ظ„ط¥ظ†طھط±ظ†طھ ظ„ظ…ط¯ط© ط¯ظ‚ظٹظ‚ط© ظˆط§ط­ط¯ط©.", parse_mode="Markdown")
        ask_protocol(chat_id, bot)

    def ask_protocol(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("VLESS", callback_data="proto_vless"),
            InlineKeyboardButton("VMESS", callback_data="proto_vmess"),
            InlineKeyboardButton("Trojan", callback_data="proto_trojan")
        )
        text = "ًںŒگ ط§ط®طھط± ط§ظ„ط¨ط±ظˆطھظˆظƒظˆظ„:"
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
            InlineKeyboardButton("ط¨ظˆط±طھ 443 (TLS) ًں”’", callback_data="port_443"),
            InlineKeyboardButton("ط¨ظˆط±طھ 80 ًںŒگ", callback_data="port_80"),
            InlineKeyboardButton("ط¥ط¯ط®ط§ظ„ ط§ظ„ط¨ظˆط±طھ ظٹط¯ظˆظٹط§ظ‹ âœچï¸ڈ", callback_data="port_manual")
        )
        bot.edit_message_text("ًںڑھ ط§ط®طھط± ط§ظ„ط¨ظˆط±طھ:", chat_id, call.message.message_id, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("port_"))
    def process_port(call):
        chat_id = call.message.chat.id
        port_val = call.data.split('_')[1]
        if port_val == "manual":
            msg = bot.send_message(chat_id, "âœچï¸ڈ ط£ط±ط³ظ„ ط±ظ‚ظ… ط§ظ„ط¨ظˆط±طھ:")
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
        markup.add(InlineKeyboardButton("WebSocket (WS) ًںŒگ", callback_data="net_ws"))
        text = "ًں“، ط§ط®طھط± ظ†ظˆط¹ ط§ظ„ط´ط¨ظƒط©:"
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
            InlineKeyboardButton("ID ط¹ط´ظˆط§ط¦ظٹ ًںژ²", callback_data="id_random"),
            InlineKeyboardButton("ID ظٹط¯ظˆظٹ âœچï¸ڈ", callback_data="id_manual")
        )
        text = "ًں”‘ ط§ط®طھط± ط§ظ„ظ…ط¹ط±ظپ (UUID):"
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
            msg = bot.send_message(chat_id, "âœچï¸ڈ ط£ط±ط³ظ„ ط§ظ„ظ…ط¹ط±ظپ (UUID):")
            bot.register_next_step_handler(msg, lambda m: save_uuid_and_ask_ips(m, bot))

    def save_uuid_and_ask_ips(message, bot):
        chat_id = message.chat.id
        creation_data[chat_id]['uuid'] = message.text
        ask_ips(chat_id, bot)

    def ask_ips(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(InlineKeyboardButton("ظ…طھطµظ„ ظˆط§ط­ط¯ ًں“±", callback_data="ip_1"), InlineKeyboardButton("ط§ظ„ط¹ط¯ط¯ ظٹط¯ظˆظٹ âœچï¸ڈ", callback_data="ip_manual"))
        text = "ًں‘¥ ط­ط¯ط¯ ط¹ط¯ط¯ ط§ظ„ط£ط¬ظ‡ط²ط© ط§ظ„ظ…ط³ظ…ظˆط­ط©:"
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("ip_"))
    def process_ips(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "manual":
            msg = bot.send_message(chat_id, "âœچï¸ڈ ط£ط±ط³ظ„ ط¹ط¯ط¯ ط§ظ„ط£ط¬ظ‡ط²ط© (ط£ط±ظ‚ط§ظ… ظپظ‚ط·):")
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
            msg = bot.send_message(chat_id, "â‌Œ ط®ط·ط£! ط£ط±ط³ظ„ ط±ظ‚ظ…ط§ظ‹ طµط­ظٹط­ط§ظ‹ ظ„ظ„ط£ط¬ظ‡ط²ط©:")
            bot.register_next_step_handler(msg, lambda m: save_ips_and_ask_duration(m, bot))

    def ask_duration(chat_id, bot, message_id=None):
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton("1 ط¯ظ‚ظٹظ‚ط© âڈ±ï¸ڈ", callback_data="dur_1m"),
            InlineKeyboardButton("1 ط³ط§ط¹ط© âڈ³", callback_data="dur_1h"),
            InlineKeyboardButton("ظٹظˆظ…", callback_data="dur_1d"),
            InlineKeyboardButton("ط´ظ‡ط±", callback_data="dur_30d"),
            InlineKeyboardButton("ط³ظ†ط©", callback_data="dur_365d"),
            InlineKeyboardButton("ظ…ط¯ط© ظٹط¯ظˆظٹط© âœچï¸ڈ", callback_data="dur_manual")
        )
        text = "âڈ³ ط­ط¯ط¯ ظ…ط¯ط© ط§ظ„ظƒظˆط¯:"
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("dur_"))
    def process_duration(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "manual":
            msg = bot.send_message(chat_id, "âœچï¸ڈ ط£ط±ط³ظ„ ط§ظ„ظ…ط¯ط© (ظ…ط«ط§ظ„: 5m ظ„ط¯ظ‚ط§ط¦ظ‚طŒ 2h ظ„ط³ط§ط¹ط§طھطŒ 10d ظ„ط£ظٹط§ظ…طŒ 1y ظ„ط³ظ†ط©):")
            bot.register_next_step_handler(msg, lambda m: save_duration_and_ask_quota(m, bot))
        else:
            creation_data[chat_id]['duration_str'] = choice
            ask_quota(chat_id, bot, call.message.message_id)

    def save_duration_and_ask_quota(message, bot):
        chat_id = message.chat.id
        text = message.text.lower().strip()
        if not (text.endswith('m') or text.endswith('h') or text.endswith('d') or text.endswith('y') or text.isdigit()):
            msg = bot.send_message(chat_id, "â‌Œ ط®ط·ط£! ط£ط±ط³ظ„ طµظٹط؛ط© طµط­ظٹط­ط© (ظ…ط«ط§ظ„ 10m, 2h, 5d):")
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
            InlineKeyboardButton("ط¨ظ„ط§ ط­ط¯ظˆط¯ â™¾ï¸ڈ", callback_data="quota_unlimited"),
            InlineKeyboardButton("ط³ط¹ط© ظٹط¯ظˆظٹط© âœچï¸ڈ", callback_data="quota_manual")
        )
        text = "ًں“ٹ ط­ط¯ط¯ ط³ط¹ط© ط§ظ„ط§ط³طھظ‡ظ„ط§ظƒ (Quota):"
        if message_id: bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
        else: bot.send_message(chat_id, text, reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("quota_"))
    def process_quota(call):
        chat_id = call.message.chat.id
        choice = call.data.split('_')[1]
        if choice == "manual":
            msg = bot.send_message(chat_id, "âœچï¸ڈ ط£ط±ط³ظ„ ط§ظ„ط³ط¹ط© ط¨ط§ظ„ط¬ظٹط¬ط§ط¨ط§ظٹطھ (ظ…ط«ط§ظ„: 50):")
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
                msg = bot.send_message(chat_id, "â‌Œ ط®ط·ط£! ط£ط±ط³ظ„ ط±ظ‚ظ…ط§ظ‹ ظپظ‚ط·:")
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

        # ط§ظ„ط¥ط¶ط§ظپط© ظ„ظ…ظ„ظپ config.json (ظ…ط­ظ„ظٹ ط£ظˆ ط¨ط¹ظٹط¯)
        bot.send_message(chat_id, "âڈ³ ط¬ط§ط±ظٹ ط²ط±ط§ط¹ط© ط§ظ„ظƒظˆط¯ ظپظٹ ط§ظ„ط³ظٹط±ظپط± ط§ظ„ظ…ط·ظ„ظˆط¨طŒ ظٹط±ط¬ظ‰ ط§ظ„ط§ظ†طھط¸ط§ط±...")
        success = add_client_to_config(data['name'], data['uuid'], protocol, server_id, bot, chat_id)
        
        if not success:
            bot.send_message(chat_id, "â‌Œ ظپط´ظ„طھ ط¹ظ…ظ„ظٹط© ط§ظ„ط¥ط¶ط§ظپط© ظ„ظ„ط³ظٹط±ظپط± ط§ظ„ط¨ط¹ظٹط¯! طھط£ظƒط¯ ظ…ظ† ط¨ظٹط§ظ†ط§طھ FTP.")
            creation_data.pop(chat_id, None)
            return

        try: save_user(data['name'], data['uuid'], data['quota_bytes'], expiry_time)
        except: pass

        try:
            selected_port = data.get('port', 443)
            # طھظ… ط¥ط¶ط§ظپط© server_id ظ„ظ„ظ€ DB
            add_user(data['name'], data['uuid'], selected_port, data['quota_bytes'], expiry_time, server_id)
        except Exception as e: print(f"Error saving to SQLite DB: {e}")

        # ط§ظ„ظ…ظƒط§ظپط¢طھ
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
        
        # ط§ط³طھط®ط±ط§ط¬ ط§ظ„ط¯ظˆظ…ظٹظ† ط¨ظ†ط§ط،ظ‹ ط¹ظ„ظ‰ ط§ظ„ط³ظٹط±ظپط±
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
            if srv: host_domain = f"{srv[5]}.alwaysdata.net"
        
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
        
        quota_display = "ط¨ظ„ط§ ط­ط¯ظˆط¯ â™¾ï¸ڈ" if data['quota_bytes'] == 0 else f"{data['quota_bytes'] / (1024**3):.2f} GB"
        
        srv_name = "ط§ظ„ط³ظٹط±ظپط± ط§ظ„ظ…ط­ظ„ظٹ" if server_id == 1 else srv[1]
        summary = f"""
âœ… **طھظ… ط¥ظ†ط´ط§ط، ط§ظ„ظƒظˆط¯ ظˆطھظپط¹ظٹظ„ظ‡ ط¨ظ†ط¬ط§ط­!**

ًں–¥ï¸ڈ **ط§ظ„ط³ظٹط±ظپط± ط§ظ„ظ…ط³طھط®ط¯ظ…:** `{srv_name}`
ًں‘¤ **ط§ظ„ط§ط³ظ…:** `{data['name']}`
ًںŒگ **ط§ظ„ط¨ط±ظˆطھظˆظƒظˆظ„:** `{protocol.upper()}`
ًںڑھ **ط§ظ„ط¨ظˆط±طھ:** `{selected_port}`
âڈ³ **ط§ظ„ظ…ط¯ط©:** `{data['duration_str']}`
ًں“ٹ **ط§ظ„ط³ط¹ط©:** `{quota_display}`
ًںژپ **ظƒظˆط¯ ط§ظ„ط¯ط¹ظˆط© ط§ظ„ط®ط§طµ ط¨ظ‡:** `{new_ref_code}`

ًں”— **ط§ظ†ط³ط® ط§ظ„ظƒظˆط¯ ط£ط¯ظ†ط§ظ‡ ظˆط§ظ„طµظ‚ظ‡ ظپظٹ طھط·ط¨ظٹظ‚ (DarkTunnel ط£ظˆ v2rayNG):**
`{final_link}`
        """
        bot.send_message(chat_id, summary, parse_mode="Markdown")
        creation_data.pop(chat_id, None)

        time.sleep(1) 
        success_msg = f"ًں”„ طھظ… ط§ظ„ط±ظٹط³طھط§ط±طھ ط§ظ„طھظ„ظ‚ط§ط¦ظٹ ظ„ظ„ط³ظٹط±ظپط± ({srv_name}) ط¨ظ†ط¬ط§ط­! ًںڑ€ ط§ظ„ظƒظˆط¯ ظ‡ط³ظ‡ ط´ط؛ط§ظ„."
        fail_msg = f"âڑ ï¸ڈ ط§ظ„ظƒظˆط¯ ط§ظ†ط­ظپط¸طŒ ط¨ط³ ظپط´ظ„ ط§ظ„ط±ظٹط³طھط§ط±طھ ط§ظ„طھظ„ظ‚ط§ط¦ظٹ ظ„ظ„ط³ظٹط±ظپط± ({srv_name})."
        restart_alwaysdata(bot, chat_id, success_msg, fail_msg, server_id)
