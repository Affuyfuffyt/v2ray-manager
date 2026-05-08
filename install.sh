#!/bin/bash
clear
echo "=================================================="
echo "  ًںڑ€ ط£ط¯ط§ط© ط¥ط¯ط§ط±ط© V2Ray (ط§ظ„ظ†ط³ط®ط© ط§ظ„ط§ط­طھط±ط§ظپظٹط© ط¨ظ€ API) "
echo "=================================================="

# 1. طھظ†ط¸ظٹظپ ظˆط¥ظٹظ‚ط§ظپ ط§ظ„ط¹ظ…ظ„ظٹط§طھ
pkill -9 xray
pkill -9 -f run.py

# 2. ط£ط®ط° ط§ظ„ط¨ظٹط§ظ†ط§طھ ط§ظ„ظ…ط·ظ„ظˆط¨ط©
read -p "ًں”‘ ط£ط¯ط®ظ„ طھظˆظƒظ† ط§ظ„ط¨ظˆطھ: " BOT_TOKEN
read -p "ًں‘‘ ط£ط¯ط®ظ„ ط§ظ„ط¢ظٹط¯ظٹ ط§ظ„ط®ط§طµ ط¨ظƒ: " ADMIN_ID
read -p "ًں› ï¸ڈ ط£ط¯ط®ظ„ Alwaysdata API Key: " AD_API_KEY
read -p "ًں†” ط£ط¯ط®ظ„ Site ID ط§ظ„ط®ط§طµ ط¨ظƒ: " AD_SITE_ID
read -p "ًںŒگ ط£ط¯ط®ظ„ ط§ظ„ط¯ظˆظ…ظٹظ† ط§ظ„ط®ط§طµ ط¨ظƒ (ظ…ط«ط§ظ„: google.com): " AD_DOMAIN
read -p "ًں‘¤ ط£ط¯ط®ظ„ FTP User (ط§ط³ظ… ط­ط³ط§ط¨ظƒ ظپظٹ Alwaysdata): " FTP_USER

# 3. طھط¬ظ‡ظٹط² ط§ظ„ظ…ط¬ظ„ط¯ط§طھ
WORK_DIR="$HOME/v2ray_manager"
XRAY_DIR="$HOME/xray_core"
mkdir -p $XRAY_DIR
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# 4. طھط­ظ…ظٹظ„ ط§ظ„ظ…ط­ط±ظƒ Xray (ط¥ط°ط§ ظ„ظ… ظٹظƒظ† ظ…ظˆط¬ظˆط¯ط§ظ‹)
if [ ! -f "$XRAY_DIR/xray" ]; then
    echo "[+] ط¬ط§ط±ظٹ طھط­ظ…ظٹظ„ ظ…ط­ط±ظƒ Xray..."
    cd $XRAY_DIR
    wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
    unzip -q Xray-linux-64.zip
    rm Xray-linux-64.zip
    chmod +x xray
fi

# 5. ط³ط­ط¨ ظ…ظ„ظپط§طھ ط§ظ„ط¨ظˆطھ ظ…ظ† ظƒظٹطھ ظ‡ط¨
echo "[+] ط¬ط§ط±ظٹ ط³ط­ط¨ ظ…ظ„ظپط§طھ ط§ظ„ط¨ظˆطھ..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR

# 6. ظ†ظ‚ظ„ ظ…ظ„ظپ config.json ظ„ظ„ظ…ظƒط§ظ† ط§ظ„طµط­ظٹط­ ظˆطھطµط­ظٹط­ ط§ظ„ظ…ط³ط§ط±ط§طھ ًں”¥
cp xray_core/config.json $XRAY_DIR/config.json

echo "[+] ط¬ط§ط±ظٹ طھطµط­ظٹط­ ظ…ط³ط§ط±ط§طھ ط§ظ„ط³ظٹط±ظپط± ط§ظ„ظ…ط­ظ„ظٹ ظ„طھط¹ظ…ظ„ ظ…ط¹ ط­ط³ط§ط¨: $FTP_USER"
# ًں”¥ ط§ظ„طھط­ط¯ظٹط« ط§ظ„ط¬ط°ط±ظٹ: ظ…ط³ط­ ط£ظٹ ظ…ط³ط§ط± ظ‚ط¯ظٹظ… ظˆظƒطھط§ط¨ط© ط§ظ„ظ…ط³ط§ط± ط§ظ„ظ…ط·ظ„ظ‚ ط§ظ„طµط­ظٹط­ ط¨ظ‚ظˆط© ًں”¥
sed -i 's|"access":.*|"access": "/home/'"$FTP_USER"'/xray_core/access.log",|g' $XRAY_DIR/config.json
sed -i 's|"error":.*|"error": "/home/'"$FTP_USER"'/xray_core/error.log",|g' $XRAY_DIR/config.json

# 7. طھط®ط²ظٹظ† ظƒظ„ ط§ظ„ظ…ظپط§طھظٹط­ ظپظٹ ظ…ظ„ظپ ط§ظ„ط¨ظٹط¦ط© ط§ظ„ظ…ط®ظپظٹ
echo "BOT_TOKEN=$BOT_TOKEN" > .env
echo "ADMIN_ID=$ADMIN_ID" >> .env
echo "AD_API_KEY=$AD_API_KEY" >> .env
echo "AD_SITE_ID=$AD_SITE_ID" >> .env
echo "AD_DOMAIN=$AD_DOMAIN" >> .env
echo "FTP_USER=$FTP_USER" >> .env

# ًں”¥ ط§ظ„ط¥ط¶ط§ظپط© ط§ظ„ط°ظƒظٹط©: طھط¬ظ‡ظٹط² ظ…ظ„ظپ ط§ظ„ط±ظٹط³طھط§ط±طھ ط§ظ„طھظ„ظ‚ط§ط¦ظٹ ظˆط§ظ„ط¯ظˆظ…ظٹظ† ط§ظ„ط¹ط§ظ„ظ…ظٹ
echo "$AD_SITE_ID" > $HOME/alwaysdata_keys.txt
echo "$AD_API_KEY" >> $HOME/alwaysdata_keys.txt
echo "$AD_DOMAIN" >> $HOME/alwaysdata_keys.txt

# 8. طھط«ط¨ظٹطھ ط§ظ„ظ…ظƒط§طھط¨
echo "[+] ط¬ط§ط±ظٹ طھط«ط¨ظٹطھ ط§ظ„ظ…طھط·ظ„ط¨ط§طھ..."
pip install -r requirements.txt

# ًں”¥ 9. ط¥ظ†ط´ط§ط، ظ…ظ„ظپ ط§ظ„ظ…ط±ط§ظ‚ط¨ ط§ظ„ط£ط¨ط¯ظٹ (Keep Alive) ًں”¥
cat << 'EOF' > $HOME/keep_alive.sh
#!/bin/bash
if ! pgrep -f "run.py" > /dev/null
then
    echo "ط§ظ„ط¨ظˆطھ ظƒط§ظ† ظ…طھظˆظ‚ظپ... ط¬ط§ط±ظٹ ط¥ط¹ط§ط¯ط© طھط´ط؛ظٹظ„ظ‡."
    cd $HOME/v2ray_manager
    nohup python3 run.py > system.log 2>&1 &
fi
EOF
chmod +x $HOME/keep_alive.sh

# طھط´ط؛ظٹظ„ ط§ظ„ط¨ظˆطھ ظ„ط£ظˆظ„ ظ…ط±ط©
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "âœ… طھظ… ط§ظ„طھط«ط¨ظٹطھ ظˆط§ظ„ط±ط¨ط· ط¨ظ€ API ط§ظ„ظ…ظ†طµط© ظˆطھطµط­ظٹط­ ط§ظ„ظ…ط³ط§ط±ط§طھ ط¨ظ†ط¬ط§ط­!"
echo "âڑ ï¸ڈ ط®ط·ظˆط© ط£ط®ظٹط±ط© ظ…ظ‡ظ…ط©: ظ‚ظ… ط¨ط¥ط¶ط§ظپط© $HOME/keep_alive.sh ط¥ظ„ظ‰ Scheduled Tasks ظپظٹ ظ„ظˆط­ط© Alwaysdata ظ„ظٹط¹ظ…ظ„ ظƒظ„ 5 ط¯ظ‚ط§ط¦ظ‚."
echo "=================================================="
