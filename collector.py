#!/usr/bin/env python3
"""
V2Ray Collector — main script
Writes outputs into ./output/<category>/latest.md and ./output/all/latest.md
"""

import os
import re
import sys
import time
import json
import base64
import hashlib
import pathlib
from urllib.parse import urlparse, unquote
import requests

# Config
SOURCES_DIR = "text"
OUTPUT_DIR = "output"
REMARK = "☬SHΞN™ Ai Collector"
GEOIP_API = "http://ip-api.com/json/"  # simple geoip service (rate limits may apply)
USER_AGENT = "v2ray-collector/1.0 (+https://github.com/)"
HEADERS = {"User-Agent": USER_AGENT}
# Supported schemes and their categories
SCHEMES = {
    "vmess": "vmess",
    "vless": "vless",
    "ss": "ss",
    "trojan": "trojan",
    "hysteria": "hysterya",
    "hysterya": "hysterya"
}

# Helpers
def ensure_dirs():
    pathlib.Path(OUTPUT_DIR).mkdir(exist_ok=True)
    for cat in set(SCHEMES.values()):
        pathlib.Path(os.path.join(OUTPUT_DIR, cat)).mkdir(parents=True, exist_ok=True)
    pathlib.Path(os.path.join(OUTPUT_DIR, "all")).mkdir(parents=True, exist_ok=True)

def read_sources():
    """Read all .txt files from SOURCES_DIR and return list of URLs (one per line)"""
    urls = []
    if not os.path.isdir(SOURCES_DIR):
        print(f"[WARN] Sources directory '{SOURCES_DIR}' not found.")
        return urls
    for p in pathlib.Path(SOURCES_DIR).glob("*.txt"):
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line=line.strip()
                if not line or line.startswith("#"): continue
                urls.append(line)
    return urls

def fetch_url(url, timeout=15):
    try:
        r = requests.get(url, timeout=timeout, headers=HEADERS, allow_redirects=True)
        r.raise_for_status()
        return r.text, None
    except Exception as e:
        return None, str(e)

base64_rx = re.compile(r'^[A-Za-z0-9+/=\s]+$')

def try_base64_decode(s):
    s_strip = s.strip()
    # heuristic: if no newlines and long and base64-like, try decode
    try:
        # remove whitespace and newlines
        compact = "".join(s_strip.split())
        if len(compact) % 4 == 0 and base64_rx.match(compact):
            dec = base64.b64decode(compact + "===")
            return dec.decode("utf-8", errors="ignore")
    except Exception:
        return None
    return None

scheme_line_rx = re.compile(r'^(?P<scheme>[a-zA-Z0-9]+)://(?P<body>.+)$')

def extract_configs_from_text(text):
    """Return list of raw config lines found in text (vmess://..., vless://..., ss://..., hysteria://..., trojan://...) or plain lines"""
    results = []
    # try decode full text if it's base64
    decoded = try_base64_decode(text)
    if decoded and ("vmess://" in decoded or "vless://" in decoded or "ss://" in decoded or "hysteria" in decoded or "trojan://" in decoded):
        text = decoded

    # Split into lines and also try to catch inline schemes
    lines = []
    for part in re.split(r'[\r\n]+', text):
        part = part.strip()
        if not part: continue
        # some subscriptions may contain commas or spaces, split further
        parts = re.split(r'[\s,]+', part)
        for p in parts:
            p = p.strip()
            if not p: continue
            lines.append(p)

    for line in lines:
        # If line looks like a base64 payload that decodes to a list of schemes, decode it
        m = scheme_line_rx.match(line)
        if m:
            results.append(line)
            continue
        # maybe it's a base64-encoded vmess entry without scheme (just raw base64 JSON)
        decoded_line = try_base64_decode(line)
        if decoded_line and ("vmess://" in decoded_line or "vless://" in decoded_line or "ss://" in decoded_line or "trojan://" in decoded_line or "hysteria" in decoded_line):
            # recursively extract from decoded_line
            results.extend(extract_configs_from_text(decoded_line))
            continue
        # fallback: treat as plain line (could be a URL)
        results.append(line)
    return results

def dedupe_keep_order(items):
    seen=set()
    out=[]
    for it in items:
        h=hashlib.sha1(it.encode("utf-8")).hexdigest()
        if h in seen: continue
        seen.add(h); out.append(it)
    return out

# Parsing helpers for extracting host/ip
def extract_host_from_config(line):
    """Best-effort: return host or ip for geoip lookup"""
    try:
        m = scheme_line_rx.match(line)
        if m:
            scheme = m.group("scheme").lower()
            body = m.group("body")
            if scheme == "vmess":
                # body is base64 JSON
                try:
                    dec = base64.b64decode(body + "===")
                    j = json.loads(dec.decode("utf-8", errors="ignore"))
                    return j.get("add") or j.get("ps") or None
                except Exception:
                    return None
            elif scheme in ("vless", "trojan", "hysteria", "hysterya"):
                # format: scheme://<id>@host:port?opt#name  OR scheme://host:port#name
                # try to parse host
                host = body
                # remove possible userinfo
                if "@" in host:
                    host = host.split("@",1)[1]
                # remove query and fragment
                host = host.split("?",1)[0].split("#",1)[0]
                # remove port
                host = host.split(":",1)[0]
                return host
            elif scheme == "ss":
                # ss://<base64> or ss://method:pass@host:port
                if body.startswith("a2") and ":" not in body and "/" not in body:
                    # looks like base64 payload, decode
                    try:
                        dec = base64.b64decode(body + "===")
                        s = dec.decode("utf-8", errors="ignore")
                        # format method:password@host:port
                        if "@" in s:
                            hostpart = s.split("@",1)[1]
                            host = hostpart.split(":",1)[0]
                            return host
                    except Exception:
                        return None
                else:
                    # may be method:pass@host:port or host:port
                    if "@" in body:
                        hostpart = body.split("@",1)[1]
                        host = hostpart.split(":",1)[0]
                        return host
                    else:
                        # maybe host:port
                        host = body.split(":",1)[0]
                        return host
    except Exception:
        return None
    return None

def geoip_country_code(host):
    """Query GEOIP API to get countryCode for host (resolve domain first)"""
    try:
        # If host is domain, resolve to IP via requests to the host? We'll use requests to ip-api with 'host' which accepts domains.
        resp = requests.get(GEOIP_API + host, timeout=10, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                return data.get("countryCode")
    except Exception:
        pass
    return None

def country_code_to_emoji(cc):
    if not cc or len(cc)!=2: return ""
    offset = ord('🇦') - ord('A')  # not directly used, build via regional indicators
    return chr(0x1F1E6 + ord(cc[0].upper()) - ord('A')) + chr(0x1F1E6 + ord(cc[1].upper()) - ord('A'))

def remark_config_line(line, country_emoji):
    """Add remark to a single config line. Best-effort for vmess (JSON), and fallback by appending #remark for other schemes"""
    try:
        m = scheme_line_rx.match(line)
        if not m:
            # if this is a URL or plain entry, just return base64 later; no remark added
            return line
        scheme = m.group("scheme").lower()
        body = m.group("body")
        if scheme == "vmess":
            # vmess://BASE64(JSON)
            try:
                dec = base64.b64decode(body + "===")
                j = json.loads(dec.decode("utf-8", errors="ignore"))
                # set ps (remark)
                old = j.get("ps","")
                j["ps"] = f"{old} {REMARK} {country_emoji}".strip()
                newb = base64.b64encode(json.dumps(j, separators=(',',':')).encode("utf-8")).decode("utf-8")
                return f"vmess://{newb}"
            except Exception:
                return f"{line}#{REMARK} {country_emoji}"
        else:
            # for schemes that accept fragment remark, append #remark (avoid doubling)
            if "#" in line:
                base, frag = line.rsplit("#",1)
                return f"{base}#{frag} | {REMARK} {country_emoji}"
            else:
                return f"{line}#{REMARK} {country_emoji}"
    except Exception:
        return line

def to_base64_line(line):
    """Return base64 encoded line (utf-8)"""
    return base64.b64encode(line.encode("utf-8")).decode("utf-8")

def classify_scheme(line):
    m = scheme_line_rx.match(line)
    if m:
        scheme = m.group("scheme").lower()
        return SCHEMES.get(scheme, "other")
    # heuristics: if starts with '{' maybe vmess JSON
    if line.strip().startswith("{") and '"add"' in line:
        return "vmess"
    return "other"

def header_for_hiddify(source_url_list):
    header = [
        "<!--",
        "Hiddify Next auto-update settings:",
        "update_interval: 3600  # seconds (1 hour)",
        "display_source_links: true",
        "sources:",
    ]
    for s in source_url_list:
        header.append(f"  - {s}")
    header.append("-->")
    return "\n".join(header) + "\n\n"

def write_outputs(all_configs, per_category, source_urls):
    ensure_dirs()
    timestamp = int(time.time())
    # master all
    master_path = os.path.join(OUTPUT_DIR, "all", "latest.md")
    with open(master_path, "w", encoding="utf-8") as f:
        f.write(header_for_hiddify(source_urls))
        for cfg in all_configs:
            f.write(cfg + "\n")
    # per category
    for cat, items in per_category.items():
        path = os.path.join(OUTPUT_DIR, cat, "latest.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(header_for_hiddify(source_urls))
            for cfg in items:
                f.write(cfg + "\n")

def process():
    source_urls = read_sources()
    if not source_urls:
        print("[INFO] No source links found in 'text' folder. Put subscription URLs (one per line) into text/*.txt")
        return 1
    print(f"[INFO] Found {len(source_urls)} source lines.")
    raw_configs = []
    for url in source_urls:
        print(f"[INFO] Fetching {url} ...")
        text, err = fetch_url(url)
        if err:
            print(f"[WARN] Failed to fetch {url}: {err}")
            continue
        # extract configs
        extracted = extract_configs_from_text(text)
        print(f"[INFO] Extracted {len(extracted)} potential config lines from {url}")
        raw_configs.extend(extracted)
    # dedupe
    raw_configs = dedupe_keep_order(raw_configs)
    print(f"[INFO] After dedupe: {len(raw_configs)} configs")
    per_category = {v:[] for v in set(SCHEMES.values())}
    all_out = []
    for line in raw_configs:
        host = extract_host_from_config(line)
        cc = None
        emoji = ""
        if host:
            cc = geoip_country_code(host)
            emoji = country_code_to_emoji(cc) if cc else ""
        remarked = remark_config_line(line, emoji)
        b64line = to_base64_line(remarked)
        all_out.append(b64line)
        cat = classify_scheme(line)
        if cat in per_category:
            per_category[cat].append(b64line)
    # write outputs
    write_outputs(all_out, per_category, source_urls)
    print("[INFO] Outputs written into 'output/'")
    return 0

if __name__ == "__main__":
    sys.exit(process())
