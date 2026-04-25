import json
import os
import requests
from dotenv import load_dotenv
import time

CONFIG_PATH = '/home/wathfor/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        # تحميل المفاتيح من ملف .env المخفي للاتصال الرسمي بالمنصة
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')

    def create_client(self, email, uuid, protocol="vless"):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # تحديد الغرفة وإضافة (level: 0) لتفعيل العداد الداخلي
            if protocol == "vless":
                target_inbound = 1
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "vmess":
                target_inbound = 2
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "trojan":
                target_inbound = 3
                new_client = {"password": uuid, "email": email, "level": 0} 
            else:
                target_inbound = 1
                new_client = {"id": uuid, "email": email, "level": 0}
            
            clients = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients):
                clients.append(new_client)
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # 1. الضربة القاضية: نقتل العملية فوراً لقطع النت عن المنتهية صلاحيتهم
        os.system("pkill -9 xray")
        time.sleep(0.5)
        
        # 2. التشغيل القانوني: نطلب من منصة Alwaysdata تشغيل الموقع رسمياً
        if self.api_key and self.site_id:
            try:
                url = f"https://api.alwaysdata.com/v1/site/{self.site_id}/restart/"
                response = requests.post(url, auth=(self.api_key, ''))
                
                if response.status_code == 204:
                    print("✅ Successfully restarted site via API")
                    return True
                else:
                    print(f"⚠️ API Restart failed with status: {response.status_code}")
            except Exception as e:
                print(f"API Restart Error: {e}")
        
        return True

    def get_client_traffic(self, email):
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            changed = False
            for i in range(1, 4):
                try:
                    clients = config['inbounds'][i]['settings']['clients']
                    if not enable:
                        original_len = len(clients)
                        # حذف المشترك
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
