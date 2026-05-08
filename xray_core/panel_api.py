import json
import os
import requests
from dotenv import load_dotenv
import time

# ًں”¥ ط§ظƒطھط´ط§ظپ ط§ظ„ظ…ط³ط§ط± ط§ظ„ط£ط³ط§ط³ظٹ طھظ„ظ‚ط§ط¦ظٹط§ظ‹ ًں”¥
HOME_DIR = os.path.expanduser("~")
CONFIG_PATH = f'{HOME_DIR}/xray_core/config.json'

class PanelAPI:
    def __init__(self):
        # طھط­ظ…ظٹظ„ ط§ظ„ظ…ظپط§طھظٹط­ ظ„ظ„ط§طھطµط§ظ„ ط§ظ„ظ…ط³طھظ‚ط¨ظ„ظٹ ط¥ط°ط§ ظ„ط²ظ… ط§ظ„ط£ظ…ط±
        load_dotenv()
        self.api_key = os.getenv('AD_API_KEY')
        self.site_id = os.getenv('AD_SITE_ID')

    def create_client(self, email, uuid, protocol="vless"):
        try:
            if not os.path.exists(CONFIG_PATH):
                print(f"â‌Œ Error: Config file not found at {CONFIG_PATH}")
                return False

            with open(CONFIG_PATH, 'r') as f:
                config = json.load(f)
            
            # ًں”¥ طھطµط­ظٹط­ ظ…ط³ط§ط± ط§ظ„ظ„ظˆظƒط§طھ ط§ظ„طھظ„ظ‚ط§ط¦ظٹ (ط¨ط§ظ„ط§ط¹طھظ…ط§ط¯ ط¹ظ„ظ‰ ط§ظ„ظ…ط³ط§ط± ط§ظ„ظ…ط·ظ„ظ‚) ًں”¥
            # ظٹط³طھط®ط±ط¬ ط§ط³ظ… ط§ظ„ظٹظˆط²ط± ط§ظ„ط­ط§ظ„ظٹ ظˆظٹطµط­ط­ ط§ظ„ظ…ط³ط§ط± ظپظˆط±ط§ظ‹ ظ„ط¶ظ…ط§ظ† ط¹ظ…ظ„ Xray ط¨ط§ظ„ط®ظ„ظپظٹط©
            local_user = os.path.basename(HOME_DIR)
            if "log" in config:
                expected_access = f"/home/{local_user}/xray_core/access.log"
                expected_error = f"/home/{local_user}/xray_core/error.log"
                if config["log"].get("access") != expected_access:
                    config["log"]["access"] = expected_access
                if config["log"].get("error") != expected_error:
                    config["log"]["error"] = expected_error

            # ًں”¥ ط¥ط¶ط§ظپط© ط§ظ„ظ…ط´طھط±ظƒ ظ„ظ„ظ…ظ†ظپط° ط§ظ„ط±ط¦ظٹط³ظٹ (Fallback) ظ„ظٹطھظ… ط­ط³ط§ط¨ ط§ط³طھظ‡ظ„ط§ظƒظ‡ ًں”¥
            main_inbound = 0
            
            if protocol == "vless" or protocol == "vmess":
                new_client = {"id": uuid, "email": email, "level": 0}
            elif protocol == "trojan":
                new_client = {"password": uuid, "email": email, "level": 0} 
            else:
                new_client = {"id": uuid, "email": email, "level": 0}

            # ط§ظ„ط¥ط¶ط§ظپط© ظ„ظ„ط¨ظˆط§ط¨ط© ط§ظ„ط±ط¦ظٹط³ظٹط©
            clients_main = config['inbounds'][main_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_main):
                clients_main.append(new_client)

            # ط§ظ„ط¥ط¶ط§ظپط© ظ„ظ„ظ…ط³ط§ط± ط§ظ„ط®ط§طµ ط¨ط§ظ„ط¨ط±ظˆطھظˆظƒظˆظ„ (WS)
            target_map = {"vless": 1, "vmess": 2, "trojan": 3}
            target_inbound = target_map.get(protocol.lower(), 1)
            
            clients_ws = config['inbounds'][target_inbound]['settings']['clients']
            if not any(c.get('email') == email for c in clients_ws):
                clients_ws.append(new_client)
            
            # ط­ظپط¸ ط§ظ„ظ…ظ„ظپ ط¨ط¹ط¯ ط§ظ„طھط¹ط¯ظٹظ„ ظˆط§ظ„طھطµط­ظٹط­
            with open(CONFIG_PATH, 'w') as f:
                json.dump(config, f, indent=2)
            
            return self.restart_xray()
            
        except Exception as e:
            print(f"Error creating client locally: {e}")
            return False

    def restart_xray(self):
        # 1. ط¥ظٹظ‚ط§ظپ ط§ظ„ظ…ط­ط±ظƒ ظ„ظ‚ط·ط¹ ط§ظ„ط§طھطµط§ظ„ ط¹ظ† ط§ظ„ظ…ظ†طھظ‡ظٹظ† ظˆط¥ط¬ط¨ط§ط± ط§ظ„ط³ظٹط±ظپط± ط¹ظ„ظ‰ ط¥ط¹ط§ط¯ط© ط§ظ„طھط´ط؛ظٹظ„
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
            # ط§ظ„ط¨ط­ط« ظˆط­ط°ظپ ط§ظ„ظ…ط´طھط±ظƒ ظ…ظ† ط¬ظ…ظٹط¹ ط§ظ„ط¨ظˆط§ط¨ط§طھ (ظ…ظ† 0 ط¥ظ„ظ‰ 3)
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
