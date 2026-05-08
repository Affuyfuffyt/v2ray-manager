#!/bin/bash
clear
echo "=================================================="
echo "  🚀 تثبيت عقدة (Node) V2Ray للسيرفر الفرعي "
echo "=================================================="

pkill -9 xray
pkill -9 -f run.py

# طلب بيانات السيرفر الفرعي (تم إزالة متطلبات البوت هنا)
read -p "🛠️ أدخل Alwaysdata API Key الخاص بالسيرفر الجديد: " AD_API_KEY
read -p "🆔 أدخل Site ID الخاص بالسيرفر الجديد: " AD_SITE_ID
read -p "🌐 أدخل الدومين الخاص بالسيرفر (مثال: google.com): " AD_DOMAIN
read -p "👤 أدخل FTP User (اسم الحساب الجديد): " FTP_USER

WORK_DIR="$HOME/v2ray_manager"
XRAY_DIR="$HOME/xray_core"
mkdir -p $XRAY_DIR
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# تحميل المحرك
if [ ! -f "$XRAY_DIR/xray" ]; then
    echo "[+] جاري تحميل محرك Xray..."
    cd $XRAY_DIR
    wget -q https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-64.zip
    unzip -q Xray-linux-64.zip
    rm Xray-linux-64.zip
    chmod +x xray
fi

echo "[+] جاري سحب ملفات الإعداد..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR
cp xray_core/config.json $XRAY_DIR/config.json

echo "[+] جاري تصحيح المسارات..."
sed -i 's|"access":.*|"access": "/home/'"$FTP_USER"'/xray_core/access.log",|g' $XRAY_DIR/config.json
sed -i 's|"error":.*|"error": "/home/'"$FTP_USER"'/xray_core/error.log",|g' $XRAY_DIR/config.json

# تخزين الإعدادات الخاصة بالسيرفر
echo "AD_API_KEY=$AD_API_KEY" > .env
echo "AD_SITE_ID=$AD_SITE_ID" >> .env
echo "AD_DOMAIN=$AD_DOMAIN" >> .env
echo "FTP_USER=$FTP_USER" >> .env

echo "$AD_SITE_ID" > $HOME/alwaysdata_keys.txt
echo "$AD_API_KEY" >> $HOME/alwaysdata_keys.txt
echo "$AD_DOMAIN" >> $HOME/alwaysdata_keys.txt

echo "[+] جاري إنشاء ملف التشغيل الأبدي..."
cat << 'EOF' > $HOME/keep_alive.sh
#!/bin/bash
if ! pgrep -f "xray" > /dev/null
then
    echo "إعادة تشغيل Xray..."
    cd $HOME/xray_core
    nohup ./xray run -c config.json > system.log 2>&1 &
fi
EOF
chmod +x $HOME/keep_alive.sh

echo "[+] جاري تشغيل المحرك..."
nohup $HOME/xray_core/xray run -c $HOME/xray_core/config.json > $HOME/xray_core/system.log 2>&1 &

echo "=================================================="
echo "✅ تم تثبيت السيرفر الفرعي بنجاح كعقدة (Node)!"
echo "⚠️ قم بإضافة $HOME/keep_alive.sh إلى Scheduled Tasks في لوحة التحكم الخاصة به."
echo "=================================================="
