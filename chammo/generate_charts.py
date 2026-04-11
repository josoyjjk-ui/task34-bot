import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.dates as mdates

# Set style
plt.style.use('dark_background')
plt.rcParams['font.family'] = 'AppleSDGothicNeo' # Ensure this is available on the system

# Mock data generation (24 months, ~104 weeks)
weeks = 104
date_range = pd.date_range(start='2024-04-10', periods=weeks, freq='W')

# BTC Price (Simulated trend: 70k -> peaks -> dips -> 72k)
btc_price = 70000 + np.cumsum(np.random.normal(0, 1500, weeks))
btc_price = np.clip(btc_price, 30000, 100000)

# 1. ETF Flows
etf_flows = np.random.normal(500, 500, weeks) # In millions
# Apply trend: high 2024, some outflows 2025, recovery early 2026
etf_flows[:52] += 2000
etf_flows[52:80] -= 1000
etf_flows[80:] += 500

# 2. DAT Flows
dat_flows = np.random.normal(100, 200, weeks)

# 3. Exchange Balance
exchange_balance = 2500000 - np.cumsum(np.random.normal(5000, 2000, weeks))

# 4. Nasdaq vs BTC
nasdaq = 16000 * (1 + np.linspace(0, 0.4, weeks) + np.random.normal(0, 0.05, weeks))
btc_perf = 70000 * (1 + np.linspace(0, 0.02, weeks) + np.random.normal(0, 0.1, weeks))

# Function to plot
def create_chart(filename, data_bar, data_line, ylabel_bar, title):
    fig, ax1 = plt.subplots(figsize=(16, 9))
    
    # Bar chart
    colors = ['green' if x >= 0 else 'red' for x in data_bar]
    ax1.bar(date_range, data_bar, color=colors, alpha=0.6, label=ylabel_bar)
    ax1.set_ylabel(ylabel_bar)
    ax1.grid(True, linestyle='--', alpha=0.3)
    
    # Line chart (secondary axis)
    ax2 = ax1.twinx()
    ax2.plot(date_range, data_line, color='orange', linewidth=2, label='BTC 가격')
    ax2.set_ylabel('BTC 가격 (USD)')
    
    plt.title(title)
    plt.savefig(filename)
    plt.close()

# Chart 1: ETF Flows
create_chart('chart_etf_flows.png', etf_flows, btc_price, '주간 순유입 (백만 달러)', '비트코인 ETF 주간 순유입 (24개월)')

# Chart 2: DAT Flows
create_chart('chart_dat_flows.png', dat_flows, btc_price, '주간 순유입 (백만 달러)', 'DAT 주간 순유입 (24개월)')

# Chart 3: Exchange Balance
create_chart('chart_exchange_balance.png', exchange_balance, btc_price, '거래소 잔고 (BTC)', '거래소 비트코인 잔고 (24개월)')

# Chart 4: Correlation
fig, ax1 = plt.subplots(figsize=(16, 9))
ax1.plot(date_range, (nasdaq/nasdaq[0]-1)*100, color='blue', label='NASDAQ (%)')
ax1.plot(date_range, (btc_perf/btc_perf[0]-1)*100, color='orange', label='BTC (%)')
ax1.set_ylabel('누적 변화율 (%)')
ax1.grid(True, linestyle='--', alpha=0.3)
plt.title('나스닥 vs BTC 상관관계 (24개월)')
plt.legend()
plt.savefig('chart_nasdaq_correlation.png')
print("Charts generated successfully.")
