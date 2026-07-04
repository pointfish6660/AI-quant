#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch 比亚迪 (002594.SZ + 01211.HK) daily K-line data (前复权).

A股: 腾讯行情 API (sz002594, qfq 前复权)
港股: westock CLI (hk01211, 复权)
Spec: specs/byd.yaml
"""
import sys, io
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import urllib.request, json, csv, os, subprocess

TENCENT_CODE = "sz002594"
A_CODE = "002594.SZ"
HK_CODE = "01211.HK"
WESTOCK_CODE = "hk01211"
NAME = "比亚迪"
LIMIT_A, LIMIT_HK = 320, 300

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data")
os.makedirs(DATA_DIR, exist_ok=True)


def fetch_a_share():
    url = f"https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={TENCENT_CODE},day,,,{LIMIT_A},qfq"
    print(f"[A-Share] {url}")
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    resp = urllib.request.urlopen(req, timeout=15)
    api_data = json.loads(resp.read().decode("utf-8"))
    raw = api_data["data"][TENCENT_CODE].get("qfqday") or api_data["data"][TENCENT_CODE].get("day", [])
    print(f"[A-Share] {len(raw)} raw records")

    records = []
    for k in raw:
        o, c, h, l_ = float(k[1]), float(k[2]), float(k[3]), float(k[4])
        v = float(k[5])
        rec = {"trade_date": k[0].replace("-", ""), "open": o, "close": c,
               "high": h, "low": l_, "vol": v,
               "amount": round(v * (h + l_ + c) / 3, 0), "turnover": None}
        records.append(rec)
    records.sort(key=lambda x: x["trade_date"])
    for i, rec in enumerate(records):
        if i == 0:
            o, c = rec["open"], rec["close"]
            rec["pct_chg"] = round((c - o) / o * 100, 4) if o else 0.0
        else:
            prev = records[i - 1]["close"]
            rec["pct_chg"] = round((rec["close"] - prev) / prev * 100, 4)
    save_records(records, "byd_a")
    return records


def fetch_hk_share():
    print(f"\n[HK-Share] westock CLI: {WESTOCK_CODE}")
    cmd = f"npx -y westock-data-clawhub@1.0.4 kline {WESTOCK_CODE} --period day --limit {LIMIT_HK}"
    print(f"  [CMD] {cmd}")
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True,
                            timeout=180, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        print(f"[ERROR] {result.stderr}"); return []
    lines = [l.strip() for l in result.stdout.split("\n") if l.strip().startswith("|")]
    if len(lines) < 3: print("[ERROR] Bad format"); return []
    headers = [h.strip() for h in lines[0].split("|") if h.strip()]
    data_lines = [l for l in lines[1:] if not all(c in "-:|" for c in l.replace(" ", ""))]
    records = []
    for line in data_lines:
        cells = [c.strip() for c in line.split("|")]; cells = [c for c in cells if c != ""]
        if len(cells) != len(headers) or "npm notice" in line: continue
        row = dict(zip(headers, cells))
        rec = {"trade_date": row.get("date", ""),
               "open": to_f(row.get("open")), "close": to_f(row.get("last")),
               "high": to_f(row.get("high")), "low": to_f(row.get("low")),
               "vol": to_f(row.get("volume")), "amount": to_f(row.get("amount")),
               "turnover": to_f(row.get("exchange"))}
        records.append(rec)
    records.sort(key=lambda x: x["trade_date"])
    for i, rec in enumerate(records):
        if i == 0:
            o, c = rec["open"], rec["close"]
            rec["pct_chg"] = round((c - o) / o * 100, 4) if o and c else 0.0
        else:
            prev = records[i - 1]["close"]
            rec["pct_chg"] = round((rec["close"] - prev) / prev * 100, 4) if prev else 0.0
    print(f"[HK-Share] {len(records)} records")
    save_records(records, "byd_hk")
    return records


def to_f(val):
    if val is None or val == "": return None
    try: return float(str(val).replace(",", "").replace("%", "").strip())
    except: return None


def save_records(records, prefix):
    fn = ["trade_date", "open", "close", "high", "low", "vol", "amount", "pct_chg", "turnover"]
    cp = os.path.join(DATA_DIR, f"{prefix}_daily.csv")
    with open(cp, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader()
        for r in records: w.writerow({k: r.get(k, "") for k in fn})
    jp = os.path.join(DATA_DIR, f"{prefix}_daily.json")
    with open(jp, "w", encoding="utf-8") as f: json.dump(records, f, ensure_ascii=False, indent=2)
    print(f"  [SAVE] {cp} / {jp}")


def summary(records, label, code):
    if not records: return
    f, l_ = records[0], records[-1]
    sp, ep = f["close"], l_["close"]
    chg = ep - sp if sp and ep else 0
    pct = (ep / sp - 1) * 100 if sp else 0
    print(f"\n  {label} {code}: {f['trade_date']}~{l_['trade_date']} ({len(records)}d)")
    print(f"  Close: {sp:.2f} → {ep:.2f} ({'+'if chg>=0 else ''}{chg:.2f}, {'+'if pct>=0 else ''}{pct:.2f}%)")


def main():
    print(f"=== {NAME} A+H 取数 (前复权) ===\n")
    a = fetch_a_share(); summary(a, "A股", A_CODE)
    hk = fetch_hk_share(); summary(hk, "港股", HK_CODE)
    print(f"\n=== Done: A={len(a)}d, HK={len(hk)}d ===")

if __name__ == "__main__":
    main()
