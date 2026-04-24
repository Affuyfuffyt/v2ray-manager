#!/bin/bash
clear
echo "=================================================="
echo "  🚀 أداة إدارة V2Ray (نسخة السيرفر المحلي) "
echo "=================================================="

# 1. إيقاف البوت القديم لفك قفل الملفات (حل مشكلة .nfs)
echo "[+] جاري تنظيف السيرفر من العمليات المعلقة..."
pkill -9 -f "python3 run.py" 2>/dev/null
pkill -9 -f "xray" 2>/dev/null
sleep 2

# 2. أخذ التوكن والآيدي فقط (تم حذف أسئلة اللوحة الخارجية)
read -p "🔑 أدخل توكن البوت (Bot Token): " BOT_TOKEN
read -p "👑 أدخل الآيدي الخاص بك (Admin ID): " ADMIN_ID

# 3. إنشاء وتنظيف بيئة العمل بشكل آمن
WORK_DIR="$HOME/v2ray_manager"
cd $HOME
rm -rf $WORK_DIR
mkdir -p $WORK_DIR

# 4. سحب الملفات من مستودعك
echo "[+] جاري سحب ملفات النظام..."
git clone https://github.com/Affuyfuffyt/v2ray-manager.git $WORK_DIR
cd $WORK_DIR

# 5. حفظ البيانات في ملف مخفي
cat <<EOF > .env
BOT_TOKEN=$BOT_TOKEN
ADMIN_ID=$ADMIN_ID
EOF

# 6. تثبيت المكاتب
echo "[+] جاري تثبيت المتطلبات..."
pip install -r requirements.txt

# 7. تشغيل البوت بالخلفية
echo "[+] جاري تشغيل البوت..."
nohup python3 run.py > system.log 2>&1 &

echo "=================================================="
echo "✅ تم التثبيت بنجاح! البوت الآن جاهز لبرمجة التوليد المحلي."
echo "=================================================="
