# -*- coding: utf-8 -*-
import sys, os, re, time, json
sys.path.insert(0, r"c:\Users\26955\.trae-cn\plugins\trae-remote-official\ifind\1.3.0\skills\ifind-finance-data")
from call import call

BATCH = r"D:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\插件补全\task1_batch2.txt"
RAWDIR = r"D:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\插件补全\task1_raw"
FAIL = r"D:\Desktop\基金经理行为分析研究\指标计算流水线\data\股价行情\插件补全\task1_failed_2.txt"

os.makedirs(RAWDIR, exist_ok=True)

def read_codes(path):
    with open(path, "r", encoding="utf-8-sig") as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines

def find_csv_url(text):
    # find "下载URL为：" immediately followed by a URL ending in .csv
    idx = text.find("下载URL为：")
    if idx == -1:
        idx = text.find("下载URL为:")
    if idx == -1:
        return None
    rest = text[idx:]
    m = re.search(r'https?://[^"\s\)\]]+\.csv', rest)
    if m:
        return m.group(0)
    return None

def download(url, dest):
    import urllib.request
    try:
        urllib.request.urlretrieve(url, dest)
        return True
    except Exception as e:
        print("   download err:", e)
        return False

def main():
    codes = read_codes(BATCH)
    print("Total codes:", len(codes))
    failed = []
    okay = 0
    for i, code in enumerate(codes, 1):
        query = f"股票{code}自2006年1月至2026年8月的月涨跌幅"
        print(f"[{i}/{len(codes)}] {code}")
        try:
            res = call("stock", "get_stock_performance", {"query": query})
        except Exception as e:
            print("   call exception:", e)
            failed.append(code)
            time.sleep(3)
            continue
        if not res.get("ok"):
            print("   call not ok:", res.get("error"))
            failed.append(code)
            time.sleep(3)
            continue
        text = json.dumps(res.get("data"), ensure_ascii=False)
        url = find_csv_url(text)
        if not url:
            print("   no download url")
            failed.append(code)
            time.sleep(3)
            continue
        dest = os.path.join(RAWDIR, f"{code}.csv")
        if download(url, dest):
            if os.path.getsize(dest) > 1024:
                print(f"   OK saved {os.path.getsize(dest)} bytes")
                okay += 1
            else:
                print("   file too small")
                try: os.remove(dest)
                except Exception: pass
                failed.append(code)
        else:
            failed.append(code)
        time.sleep(3)

    with open(FAIL, "w", encoding="utf-8") as f:
        for c in failed:
            f.write(c + "\n")
    print("DONE. success:", okay, "failed:", len(failed))
    print("Failed codes:", failed)

if __name__ == "__main__":
    main()