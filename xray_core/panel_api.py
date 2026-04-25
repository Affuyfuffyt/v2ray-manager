import json
import os
import time

CONFIG_PATH = '/home/wathfor/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        # تم الاستغناء عن API المنصة نهائياً لاعتمادنا على الحارس (Watchdog) المستقل
        pass

    def create_client(self, email, uuid, protocol="vless"):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # تحديد الغرفة حسب البروتوكول المختار
            if protocol == "vless":
                target_inbound = 1
            elif protocol == "vmess":
                target_inbound = 2
            elif protocol == "trojan":
                target_inbound = 3
            else:
                target_inbound = 1
                
            new_client = {"id": uuid, "email": email, "level": 0}
            if protocol == "trojan":
                new_client = {"password": uuid, "email": email, "level": 0}
                
            clients = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients):
                clients.append(new_client)
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
        except Exception as e:
            print(f"Error creating client: {e}")
            return False

    def restart_xray(self):
        # 🔥 ذبح المحرك فقط، وسيقوم الـ Watchdog باكتشاف ذلك وإعادة تشغيله فوراً 🔥
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
                        # حذف المشترك لقطع الإنترنت عنه
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
