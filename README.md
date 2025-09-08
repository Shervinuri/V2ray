# V2Ray Collector — ☬SHΞN™ Ai Collector
Automatically fetches subscription links from `text` folder, finds VLESS/VMESS/SS/Hysterya configs, deduplicates, remarks them, geo-tags with country flag and outputs Markdown files (base64-encoded) into structured folders. Designed for GitHub Actions (runs every 30 minutes).

**Features**
- Reads source links from `text/*.txt` (each file may contain one or more subscription URLs).
- Fetches each URL, parses returned subscription data (handles raw lists, base64-encoded lists, and common `vmess://`, `vless://`, `ss://`, `trojan://`, `hysteria://` lines).
- Deduplicates entries across sources.
- Adds remark `☬SHΞN™ Ai Collector` and appends country flag based on resolved IP/domain for each node (best-effort).
- Produces one master folder `output/all/` and protocol-specific folders (`output/vmess/`, `output/vless/`, `output/ss/`, `output/hysterya/`), each containing `.md` files where every line is a base64-encoded config string.
- Adds a small header suitable for Hiddify/Hiddify Next (update interval suggestion) at top of each `.md` file.
- Includes a GitHub Actions workflow that runs on push and on schedule every 30 minutes.

> **Important**: This project does *network I/O* when the script runs (fetching subscription links and querying geoip services). The runtime environment (GitHub Actions runners or your host) must allow outgoing HTTPS requests. Use responsibly and only for links you own or have permission to query.

