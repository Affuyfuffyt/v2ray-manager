import json
import os
import requests
from dotenv import load_dotenv

# مسارات الملفات
CONFIG_PATH = os.path.expanduser('~/xray_core/config.json')

class PanelAPI:
    def __init__(self):
        # تحميل المفاتيح من ملف .env المخفي
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')

    def create_client(self, email, uuid, protocol="vless"):
        try:
            # 1. قراءة الملف
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # 2. تحديد الغرفة (Inbound) وصيغة الكود وإضافة (level: 0) لتفعيل العداد الداخلي
            if protocol == "vless":
                target_inbound = 1
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "vmess":
                target_inbound = 2
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "trojan":
                target_inbound = 3
                new_client = {"password": uuid, "email": email, "level": 0} # Trojan يستخدم كلمة password بدل id
            else:
                target_inbound = 1
                new_client = {"id": uuid, "email": email, "level": 0}
            
            # 3. إضافته للقائمة الصحيحة داخل ملف الإعدادات
            clients = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients):
                clients.append(new_client)
            
            # 4. حفظ التعديلات
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            # 5. ريستارت رسمي للسيرفر
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # تنفيذ ريستارت رسمي للموقع عبر API منصة Alwaysdata
        if self.api_key and self.site_id:
            try:
                url = f"https://api.alwaysdata.com/v1/site/{self.site_id}/restart/"
                # استخدام مفتاح الـ API كـ Username والـ Password يترك فارغاً
                response = requests.post(url, auth=(self.api_key, ''))
                
                if response.status_code == 204:
                    print("✅ Successfully restarted site via API")
                    return True
                else:
                    print(f"⚠️ API Restart failed with status: {response.status_code}")
            except Exception as e:
                print(f"API Restart Error: {e}")
        
        # حل بديل (Fallback) في حال فشل الـ API
        print("🔄 Falling back to manual process kill")
        os.system("pkill -9 xray")
        return True

    def get_client_traffic(self, email):
        # الاستهلاك يعود كـ 0 حالياً (لأن العداد الذكي الخارجي هو من يقوم بالحساب الآن)
        return 0

    def change_client_status(self, email, inbound_id=None, uuid=None, enable=True):
        try:
            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # البحث والحذف في كل الغرف (1, 2, 3) 
            for i in range(1, 4):
                try:
                    clients = config['inbounds'][i]['settings']['clients']
                    if not enable:
                        # حذف المشترك (حظر وقطع النت نهائياً)
                        config['inbounds'][i]['settings']['clients'] = [c for c in clients if c.get('email') != email]
                except Exception:
                    continue
            
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
                
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error changing status: {e}")
            return False
