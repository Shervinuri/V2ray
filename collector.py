# -*- coding: utf-8 -*-

import os
import base64
import requests
import binascii  # برای مدیریت خطاهای خاص Base64
from pathlib import Path  # روش مدرن و بهتر برای کار با مسیرها

# --- ثابت‌ها و تنظیمات ---
# استفاده از ثابت‌ها، مدیریت و تغییر کد را در آینده آسان‌تر می‌کند.
OUTPUT_DIR = Path("output")
SOURCES_URL = "https://raw.githubusercontent.com/Shervinuri/V2ray/refs/heads/main/text/sample_sources.txt"
SUPPORTED_PROTOCOLS = ("vmess://", "vless://", "ss://", "trojan://", "hysteria://")
REMARK = "☬SHΞN™ Ai Collector"
REQUEST_TIMEOUT = 10  # زمان انتظار برای هر درخواست به ثانیه

# --- اطمینان از وجود پوشه خروجی ---
# این دستور پوشه را در صورت عدم وجود ایجاد می‌کند.
OUTPUT_DIR.mkdir(exist_ok=True)


def fetch_subscription_links(url: str) -> list[str]:
    """
    لیست لینک‌های اشتراک را از URL مشخص شده دریافت می‌کند.
    """
    print(f"در حال دریافت لیست سورس‌ها از: {url}")
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()  # در صورت بروز خطای HTTP، اسکریپت را متوقف می‌کند
        links = [line.strip() for line in response.text.splitlines() if line.strip()]
        print(f"✅ تعداد {len(links)} سورس معتبر پیدا شد.")
        return links
    except requests.exceptions.RequestException as e:
        print(f"❌ خطا در دریافت لیست سورس‌ها: {e}")
        return []


def process_subscription(sub_link: str, new_remark: str) -> dict[str, list]:
    """
    یک لینک اشتراک را پردازش کرده، کانفیگ‌ها را استخراج و بر اساس پروتکل دسته‌بندی می‌کند.
    """
    print(f"  - در حال پردازش لینک: {sub_link[:50]}...")
    # یک دیکشنری برای نگهداری کانفیگ‌ها بر اساس نام پروتکل ایجاد می‌شود
    # نام پروتکل‌ها از لیست ثابت‌ها گرفته می‌شود تا از خطا جلوگیری شود
    configs = {proto.replace("://", ""): [] for proto in SUPPORTED_PROTOCOLS}
    configs["all"] = []

    try:
        response = requests.get(sub_link, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        sub_data = response.text.strip()

        # تلاش برای دیکود کردن محتوای Base64
        # اگر لینک خودش Base64 نباشد، از محتوای خام استفاده می‌شود
        try:
            decoded_data = base64.b64decode(sub_data).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            decoded_data = sub_data

        for line in decoded_data.splitlines():
            line = line.strip()
            if not line or not line.startswith(SUPPORTED_PROTOCOLS):
                continue

            # استخراج نام پروتکل برای دسته‌بندی هوشمند
            protocol = line.split("://")[0]

            # اضافه کردن ریمارک جدید به انتهای کانفیگ
            if "#" in line:
                config_part, _ = line.rsplit("#", 1)
                modified_line = f"{config_part}#{new_remark}"
            else:
                modified_line = f"{line}#{new_remark}"
            
            # TODO: برای افزودن پرچم واقعی کشور، باید از یک کتابخانه GeoIP استفاده شود.
            # در اینجا به عنوان نمونه یک پرچم ثابت اضافه شده است.
            ip_flag = "🇮🇷"
            final_line = f"{modified_line} {ip_flag}"

            # افزودن کانفیگ نهایی به لیست کلی و لیست مخصوص پروتکل خودش
            configs["all"].append(final_line)
            if protocol in configs:
                configs[protocol].append(final_line)

        return configs

    except requests.exceptions.RequestException as e:
        print(f"  ❌ خطا در پردازش لینک {sub_link[:50]}: {e}")
        return {}  # بازگرداندن دیکشنری خالی برای جلوگیری از خطا در حلقه اصلی


def save_configs_to_files(output_dir: Path, all_configs: dict[str, list]):
    """
    کانفیگ‌های جمع‌آوری شده را در دو نوع فایل (متنی و Base64) ذخیره می‌کند.
    """
    print("\nدر حال نوشتن فایل‌های خروجی...")
    for protocol, configs_list in all_configs.items():
        if not configs_list:
            print(f"  - پروتکل '{protocol}' هیچ کانفیگی ندارد، فایلی برای آن ایجاد نشد.")
            continue
        
        # تمام کانفیگ‌های یک لیست با خط جدید (\n) به هم متصل می‌شوند
        plain_text_content = "\n".join(configs_list)
        
        # --- ۱. ذخیره فایل متنی (مناسب برای مشاهده و بررسی) ---
        plain_text_filename = f"{protocol}.txt"
        plain_text_path = output_dir / plain_text_filename
        plain_text_path.write_text(plain_text_content, encoding="utf-8")
        print(f"  [✓] فایل متنی ذخیره شد: {plain_text_path}")

        # --- ۲. ذخیره فایل Base64 (مناسب برای لینک اشتراک در کلاینت‌ها) ---
        b64_content = base64.b64encode(plain_text_content.encode("utf-8")).decode("utf-8")
        b64_filename = f"{protocol}_b64.txt"
        b64_path = output_dir / b64_filename
        b64_path.write_text(b64_content, encoding="utf-8")
        print(f"  [✓] فایل Base64 ذخیره شد: {b64_path}")


def main():
    """
    تابع اصلی برای اجرای تمام مراحل اسکریپت.
    """
    subscription_links = fetch_subscription_links(SOURCES_URL)
    if not subscription_links:
        print("هیچ لینکی برای پردازش یافت نشد. برنامه خاتمه یافت.")
        return

    # دیکشنری اصلی برای نگهداری تمام کانفیگ‌های جمع‌آوری شده
    # غلط املایی 'hysterya' به 'hysteria' تصحیح شد
    master_configs = {proto.replace("://", ""): [] for proto in SUPPORTED_PROTOCOLS}
    master_configs["all"] = []

    # پردازش تمام لینک‌ها و افزودن کانفیگ‌ها به دیکشنری اصلی
    for link in subscription_links:
        processed_configs = process_subscription(link, REMARK)
        if processed_configs:
            for protocol, configs_list in processed_configs.items():
                if protocol in master_configs:
                    master_configs[protocol].extend(configs_list)

    # مرحله مهم: حذف کانفیگ‌های تکراری برای جلوگیری از لیست‌های طولانی و تکراری
    print("\nدر حال حذف کانفیگ‌های تکراری...")
    for protocol, configs_list in master_configs.items():
        # با تبدیل لیست به دیکشنری و سپس به لیست، موارد تکراری حذف می‌شوند
        unique_configs = list(dict.fromkeys(configs_list))
        master_configs[protocol] = unique_configs
        print(f"  - پروتکل {protocol}: {len(configs_list)} کانفیگ اولیه -> {len(unique_configs)} کانفیگ یکتا")

    # ذخیره فایل‌های نهایی
    save_configs_to_files(OUTPUT_DIR, master_configs)
    
    print(f"\n[+] عملیات با موفقیت انجام شد. فایل‌ها در پوشه '{OUTPUT_DIR}' ایجاد شدند.")


if __name__ == "__main__":
    main()
