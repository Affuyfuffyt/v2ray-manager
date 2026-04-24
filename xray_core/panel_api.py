import requests
import json
import config

class PanelAPI:
    def __init__(self):
        self.url = config.PANEL_URL
        self.session = requests.Session()
        self.login()

    def login(self):
        try:
            payload = {"username": config.PANEL_USER, "password": config.PANEL_PASS}
            self.session.post(f"{self.url}/login", data=payload, timeout=10)
        except Exception as e:
            print(f"Error logging in to panel: {e}")

    def get_client_traffic(self, email):
        # سحب الاستهلاك الفعلي للمشترك من السيرفر
        try:
            res = self.session.get(f"{self.url}/panel/api/inbounds/getClientTraffics/{email}").json()
            if res.get('success'):
                up = res['obj']['up']
                down = res['obj']['down']
                return up + down # الاستهلاك الكلي بالبايت
        except:
            pass
        return 0

    def change_client_status(self, email, inbound_id, uuid, enable=True):
        # تفعيل أو إيقاف (حظر) المشترك
        # يتم تحديث إعدادات العميل داخل الـ inbound
        # (هذه الدالة تحتاج تفاصيل Inbound الخاص بك، هذا هيكل تقريبي للـ 3x-ui)
        pass
