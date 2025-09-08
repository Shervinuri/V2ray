import os
import base64

OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# فرض کن new_configs یه دیکشنری هست با keys: 'all', 'vmess', 'vless', 'ss', 'hysterya'
# و values لیست کانفیگ‌ها

new_configs = {
    'all': [...],       # همه کانفیگ‌ها
    'vmess': [...],
    'vless': [...],
    'ss': [...],
    'hysterya': [...],
}

for key, configs in new_configs.items():
    file_path = os.path.join(OUTPUT_DIR, f"{key if key!='all' else 'last'}.md")
    with open(file_path, "w", encoding="utf-8") as f:
        # اضافه کردن header Hiddify Next
        f.write("# Hiddify Next - Auto Update Every 1h\n")
        f.write("# Source: Your subscription links\n\n")
        # نوشتن کانفیگ‌ها (base64 شده)
        for cfg in configs:
            if not cfg.strip().startswith("vmess://") and not cfg.strip().startswith("vless://") and not cfg.strip().startswith("ss://") and not cfg.strip().startswith("trojan://"):
                try:
                    cfg = base64.b64encode(cfg.encode()).decode()
                except:
                    pass
            f.write(cfg + "\n")
