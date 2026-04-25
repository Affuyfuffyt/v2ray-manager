import json
import os
import time

CONFIG_PATH = '/home/wathfor/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        # تم الاستغناء عن API المنصة لأننا نستخدم الحارس (Watchdog) في ملف run.py
        pass

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
        # 🔥 نقتل المحرك فقط، وحارس البوت (Watchdog) راح يكتشف إنه مات ويرجع يشغله بثانية! 🔥
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
            for i in range(1, 4):
                try:
                    clients = config['inbounds'][i]['settings']['clients']
                    if not enable:
                        original_len = len(clients)
                        # حذف المشترك لقطع النت
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
