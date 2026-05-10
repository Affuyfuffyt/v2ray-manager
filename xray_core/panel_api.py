import json
import os
import requests
from dotenv import load_dotenv
import time

# المسار الثابت اللي راح يستبدله سكربت التيرمكس باليوزر الجديد
CONFIG_PATH = '/home/alowapp/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        # تحميل المفاتيح للاتصال المستقبلي إذا لزم الأمر
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')

    def create_client(self, email, uuid, protocol="vless"):
        try:
            if not os.path.exists(CONFIG_PATH):
                print(f"❌ Error: Config file not found at {CONFIG_PATH}")
                return False

            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # تصحيح مسار اللوكات الثابت (التيرمكس راح يستبدل كلمة wathfor باليوزر الجديد)
            if "log" in config:
                expected_access = "/home/wathfor/xray_core/access.log"
                expected_error = "/home/wathfor/xray_core/error.log"
                if config["log"].get("access") != expected_access:
                    config["log"]["access"] = expected_access
                if config["log"].get("error") != expected_error:
                    config["log"]["error"] = expected_error

            # إضافة المشترك للمنفذ الرئيسي (Fallback) ليتم حساب استهلاكه
            main_inbound = 0
            
            if protocol == "vless" or protocol == "vmess":
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "trojan":
                new_client = {"password": uuid, "email": email, "level": 0} 
            else:
                new_client = {"id": uuid, "email": email, "level": 0}

            # الإضافة للبوابة الرئيسية
            clients_main = config['inbounds'][main_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_main):
                clients_main.append(new_client)

            # الإضافة للمسار الخاص بالبروتوكول (WS)
            target_map = {"vless": 1, "vmess": 2, "trojan": 3}
            target_inbound = target_map.get(protocol.lower(), 1)
            
            clients_ws = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_ws):
                clients_ws.append(new_client)
            
            # حفظ الملف بعد التعديل والتصحيح
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # إيقاف المحرك لقطع الاتصال عن المنتهين وإجبار السيرفر على إعادة التشغيل
        os.system("pkill -9 xray")
        time.sleep(0.5)
        return True

    def get_client_traffic(self, email):
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            changed = False
            # البحث وحذف المشترك من جميع البوابات (من 0 إلى 3)
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
            print(f"Error changing status: {e}")
            return False
