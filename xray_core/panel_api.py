import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()

class XrayPanelAPI:
    def __init__(self):
        self.url = os.getenv('PANEL_URL')
        self.session = requests.Session()
        self.login()

    def login(self):
        # تسجيل الدخول للوحة السيرفر للحصول على صلاحية
        payload = {"username": os.getenv('PANEL_USER'), "password": os.getenv('PANEL_PASS')}
        self.session.post(f"{self.url}/login", data=payload)

    def create_client(self, name, protocol, port, path, uuid, max_ips, duration_days, quota_bytes):
        # 🔥 هذا الكود الفعلي اللي يولد الاشتراك داخل السيرفر
        # يتم بناء الـ JSON حسب بروتوكول VLESS أو VMESS
        
        settings = {
            "clients": [
                {
                    "id": uuid,
                    "flow": "",
                    "email": name,
                    "limitIp": max_ips,
                    "totalGB": quota_bytes,
                    "expiryTime": duration_days * 86400000 # تحويل الأيام إلى ميلي ثانية
                }
            ]
        }
        
        # إرسال أمر الإنشاء الفعلي للـ Core
        response = self.session.post(
            f"{self.url}/panel/api/inbounds/addClient", 
            json={"id": port, "settings": json.dumps(settings)}
        )
        return response.json()

    def get_client_traffic(self, email):
        # 📊 سحب الاستهلاك الفعلي بالكيكا والميكا من السيرفر
        response = self.session.get(f"{self.url}/panel/api/inbounds/getClientTraffics/{email}")
        data = response.json()
        if data['success']:
            up = data['obj']['up']
            down = data['obj']['down']
            total_used = up + down
            return total_used # يرجعلك الاستهلاك بالبايت حتى تحوله بالبوت للكيكا
        return 0
