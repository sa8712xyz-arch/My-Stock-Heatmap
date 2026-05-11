import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime

print("1. 正在從維基百科獲取 S&P 500 最新成分股...")
url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
tables = pd.read_html(url)
sp500 = tables[0][['Symbol', 'GICS Sector', 'GICS Sub-Industry']]
sp500['Symbol'] = sp500['Symbol'].str.replace('.', '-', regex=False)
tickers = sp500['Symbol'].tolist()

print("2. 正在從 Yahoo Finance 下載最近 5 天的歷史價格...")
data = yf.download(tickers, period="5d")['Close']

print("3. 計算今日漲跌幅與 5 日資金輪動...")
daily_return = ((data.iloc[-1] / data.iloc[-2]) - 1) * 100
weekly_return = ((data.iloc[-1] / data.iloc[0]) - 1) * 100

performance_df = pd.DataFrame({
    'Symbol': daily_return.index,
    'Daily_Change_%': daily_return.values,
    'Weekly_Change_%': weekly_return.values
})

final_df = sp500.merge(performance_df, on='Symbol')
final_df['Weight'] = 1 
final_df = final_df.dropna()

print("4. 繪製互動式熱力圖並產出網頁...")
fig = px.treemap(
    final_df,
    path=[px.Constant("S&P 500 (美股資金輪動)"), 'GICS Sector', 'GICS Sub-Industry', 'Symbol'],
    values='Weight',
    color='Daily_Change_%',
    hover_data=['Daily_Change_%', 'Weekly_Change_%'],
    color_continuous_scale='RdYlGn',
    color_continuous_midpoint=0,
    range_color=[-3, 3],
    title=f"美股產業熱力圖 (更新時間: {datetime.now().strftime('%Y-%m-%d')})"
)
fig.update_layout(margin=dict(t=50, l=10, r=10, b=10))

rotation = final_df.groupby('GICS Sector')['Weekly_Change_%'].mean().sort_values(ascending=False).reset_index()
rotation.columns = ['產業 (Sector)', '近5日資金動能 (%)']
rotation_html = rotation.to_html(index=False, classes='table table-striped', float_format="%.2f")

html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>美股每日熱力圖與資金輪動</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .container {{ display: flex; flex-direction: column; align-items: center; }}
        table {{ border-collapse: collapse; width: 50%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>資金輪動排行 (近5日表現)</h2>
        {rotation_html}
        <hr style="width:100%">
    </div>
    {fig.to_html(full_html=False, include_plotlyjs='cdn')}
</body>
</html>
"""

with open("index.html", "w", encoding="utf-8") as f:
    f.write(html_template)

print("✅ 執行完畢！已生成 index.html")