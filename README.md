# Telegram FX Signals Bot (RSI-based)

بوت بسيط لإشارات الفوركس على التليغرام يعتمد RSI ويجلب بيانات من Alpha Vantage.

## المتطلبات
- Python 3.10+
- حساب مجاني في [Alpha Vantage](https://www.alphavantage.co/support/#api-key) للحصول على API Key
- Bot Token من @BotFather على تليغرام

## الإعداد
1) فك الضغط، ثم انسخ `.env.example` إلى `.env` وعبي القيم:
```
TELEGRAM_BOT_TOKEN=...
ALPHAVANTAGE_API_KEY=...
ADMIN_CHAT_IDS=        # اختياري: حط IDs للمصرح لهم بالتعديل، مفصولة بفواصل
INTERVAL_MINUTES=5
RSI_LOW=30
RSI_HIGH=70
```

2) ثبت المكتبات:
```
pip install -r requirements.txt
```

3) شغل البوت:
```
python bot.py
```

## الأوامر داخل التليغرام
- `/start` — تعليمات
- `/subscribe` — الاشتراك في الإشعارات
- `/unsubscribe` — إلغاء الاشتراك
- `/pairs EURUSD USDJPY` — تحديث الأزواج
- `/status` — يعرض الحالة
- `/test` — يرسل إشارة اختبار

> ملاحظة: Alpha Vantage على الخطة المجانية قد يحدّ من عدد الطلبات بالدقيقة. في حال حدوث تأخير أو Rate Limit، السكربت يحاول تلقائيًا كم مرة.

## نشر سريع
- تقدر تنشره على Render أو Railway أو أي VPS.
- تأكد من إضافة متغيرات البيئة نفسها من `.env` في لوحة التحكم.
- افتح منفذ الإنترنت وخلّه يعمل بالـ polling (ما يحتاج Webhook).

## تحذير مهم
هذا البوت للتعليم والاختبار فقط. التداول ينطوي على مخاطر عالية.
لا يعتبر نصيحة استثمارية. استخدمه على مسؤوليتك.
