import os
import base64
import requests

OUTPUT_DIR = "output"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# تابع شبیه process_subscription که کانفیگ‌ها رو جمع می‌کنه
def process_subscription(sub_link, new_remark="☬SHΞN™ Ai Collector"):
    try:
        response = requests.get(sub_link, timeout=10)
        response.raise_for_status()
        sub_data = response.text.strip()
        try:
            decoded_data = base64.b64decode(sub_data).decode("utf-8")
        except:
            decoded_data = sub_data

        config_lines = decoded_data.splitlines()
        supported_protocols = ("vmess://", "vless://", "ss://", "trojan://", "hysteria://")
        new_configs = {'all':[], 'vmess':[], 'vless':[], 'ss':[], 'trojan':[], 'hysterya':[]}

        for line in config_lines:
            line = line.strip()
            if not line or not any(line.startswith(proto) for proto in supported_protocols):
                continue

            # اضافه کردن ریمارک
            if "#" in line:
                cfg_part, _ = line.rsplit("#", 1)
                line = f"{cfg_part}#{new_remark}"
            else:
                line = f"{line}#{new_remark}"

            # اضافه کردن پرچم کشور بر اساس IP (شبیه‌سازی)
            # برای واقعی باید GeoIP استفاده کنی
            ip_flag = "🇮🇷"  # مثال ایران
            line = f"{line} {ip_flag}"

            new_configs['all'].append(line)
            if line.startswith("vmess://"):
                new_configs['vmess'].append(line)
            elif line.startswith("vless://"):
                new_configs['vless'].append(line)
            elif line.startswith("ss://"):
                new_configs['ss'].append(line)
            elif line.startswith("trojan://"):
                new_configs['trojan'].append(line)
            elif line.startswith("hysteria://"):
                new_configs['hysterya'].append(line)

        return new_configs

    except requests.exceptions.RequestException as e:
        print(f"خطا در دریافت لینک: {e}")
        return None

# نمونه لینک
subscription_link = "https://v2.alicivil.workers.dev"

# جمع‌آوری کانفیگ‌ها
configs = process_subscription(subscription_link)

if configs:
    # نوشتن فایل‌ها
    def write_output_file(filename, cfg_list):
        path = os.path.join(OUTPUT_DIR, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("# Hiddify Next - Auto Update Every 1h\n")
            f.write("# Source: Your subscription links\n\n")
            for c in cfg_list:
                try:
                    if not c.strip().startswith(("vmess://","vless://","ss://","trojan://","hysteria://")):
                        c = base64.b64encode(c.encode()).decode()
                except:
                    pass
                f.write(c + "\n")

    write_output_file("main.md", configs['all'])
    write_output_file("Vmes.md", configs['vmess'])
    write_output_file("Vless.md", configs['vless'])
    write_output_file("Ss.md", configs['ss'])
    write_output_file("Trojan.md", configs['trojan'])
    write_output_file("Hysterya.md", configs['hysterya'])

    print(f"[+] Output files created in {OUTPUT_DIR}/")
