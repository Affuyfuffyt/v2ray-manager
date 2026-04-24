import json
import os
import time

# مسار ملف الإعدادات ومحرك Xray
CONFIG_PATH = os.path.expanduser('~/xray_core/config.json')
XRAY_BIN = os.path.expanduser('~/xray_core/xray')

class PanelAPI:
    def __init__(self):
        pass

    def create_client(self, email, uuid):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            new_client = {
                "id": uuid,
                "email": email
            }
            
            clients = config['inbounds'][0]['settings']['clients']
            if not any(c.get('email') == email for c in clients):
                clients.append(new_client)
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            self.restart_xray()
            return True
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # 1. إيقاف قاسي ومباشر لضمان تفريغ البورت فوراً
        os.system("pkill -9 -f xray")
        time.sleep(2) # مهلة قصيرة لتأكيد الإغلاق
        
        # 2. تشغيل المحرك يدوياً من البوت مباشرة (تخطي انتظار Alwaysdata)
        os.system(f"nohup {XRAY_BIN} run -c {CONFIG_PATH} > /dev/null 2>&1 &")

    def get_client_traffic(self, email):
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            clients = config['inbounds'][0]['settings']['clients']
            
            if not enable:
                config['inbounds'][0]['settings']['clients'] = [c for c in clients if c.get('email') != email]
            else:
                if uuid and not any(c.get('email') == email for c in clients):
                    config['inbounds'][0]['settings']['clients'].append({"id": uuid, "email": email})
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
                
            self.restart_xray()
            return True
            
        except Exception as e:
            print(f"Error changing status: {e}")
            return False
