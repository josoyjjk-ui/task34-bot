import re

with open("/Users/fireant/.openclaw/workspace/ops/publish_work.py", "r") as f:
    content = f.read()

new_text = '''POST_TEXT = """📌 불개미 일일시황 | 2026.04.07 (화)

1️⃣ BTC ETH 유출입
• BTC: +$471.32M (순유입)
• ETH: +$120.24M (순유입)
• ETF 데이터는 마지막 거래일 기준

2️⃣ 미결제약정 추이 (24시간 기준)
• BTC 24시간: -2.74%
• ETH 24시간: -3.32%

3️⃣ DAT 추이
• WEEKLY NET INFLOW: +$735.45M

4️⃣ 코인베이스 프리미엄
• 현재 지수: +0.011%

5️⃣ 요약
BTC·ETH 현물 ETF 모두 강한 순유입을 기록하며 기관 매수세가 이어지고 있습니다.
미결제약정은 BTC -2.74%, ETH -3.32%로 단기 레버리지 축소가 진행 중이며, 코인베이스 프리미엄은 소폭 플러스권을 유지 중입니다."""'''

content = re.sub(r'POST_TEXT = """.*?"""', new_text, content, flags=re.DOTALL)

with open("/Users/fireant/.openclaw/workspace/ops/publish_work.py", "w") as f:
    f.write(content)
