"""测试东方财富全持仓API"""
import requests
import json

code = '002910'
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://fundf10.eastmoney.com/'}

# Test 1: http with topline=500
url1 = f'http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year=2024&month=12'
r1 = requests.get(url1, headers=headers, timeout=15)
text1 = r1.text
has1 = '{' in text1 and 'content' in text1
print(f'Test1 (http, topline=500): has_json={has1}, len={len(text1)}')
if has1:
    start = text1.index('{')
    end = text1.rindex('}') + 1
    d = json.loads(text1[start:end])
    content = d.get('content', {})
    if content:
        for key, arr in content.items():
            print(f'  {key}: {len(arr)} stocks')
            if arr and len(arr) > 0:
                print(f'  First stock: {arr[0][:8]}')
    else:
        print('  content is empty')

# Test 2: month=06
url2 = f'http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code}&topline=500&year=2024&month=06'
r2 = requests.get(url2, headers=headers, timeout=15)
text2 = r2.text
has2 = '{' in text2 and 'content' in text2
print(f'Test2 (month=06): has_json={has2}, len={len(text2)}')
if has2:
    start = text2.index('{')
    end = text2.rindex('}') + 1
    d2 = json.loads(text2[start:end])
    content2 = d2.get('content', {})
    if content2:
        total = sum(len(arr) for arr in content2.values())
        print(f'  Total stocks: {total}')

# Test 3: Try a fund that previously returned 0
code2 = '021179'
url3 = f'http://fundf10.eastmoney.com/FundArchivesDatas.aspx?type=jjcc&code={code2}&topline=500&year=2024&month=12'
r3 = requests.get(url3, headers=headers, timeout=15)
text3 = r3.text
has3 = '{' in text3 and 'content' in text3
print(f'Test3 ({code2}, month=12): has_json={has3}, len={len(text3)}')
if has3:
    start = text3.index('{')
    end = text3.rindex('}') + 1
    d3 = json.loads(text3[start:end])
    content3 = d3.get('content', {})
    if content3:
        total3 = sum(len(arr) for arr in content3.values())
        print(f'  Total stocks: {total3}')
    else:
        print('  content is empty')
else:
    print(f'  Response[:200]: {text3[:200]}')
