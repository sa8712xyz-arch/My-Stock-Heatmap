import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import io

try:
    # 1. 取得台灣時間
    tw_time = datetime.utcnow() + timedelta(hours=8)
    tw_time_str = tw_time.strftime('%Y-%m-%d %H:%M')

    print("1. 正在獲取 S&P 500 最新成分股...")
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(response.text))
    sp500 = tables[0][['Symbol', 'GICS Sector', 'GICS Sub-Industry']]
    sp500['Symbol'] = sp500['Symbol'].str.replace('.', '-', regex=False)
    tickers = sp500['Symbol'].tolist()

    print("2. 下載數據並進行資料搶救...")
    data = yf.download(tickers, period="10d")['Close']
    
    # [cite: 64, 68] 使用 ffill().bfill() 確保數據不遺漏
    data = data.ffill().bfill()
    
    print("3. 計算漲跌幅並篩選前 20 名...")
    daily_return = ((data.iloc[-1] / data.iloc[-2]) - 1) * 100
    period_return = ((data.iloc[-1] / data.iloc[0]) - 1) * 100

    performance_df = pd.DataFrame({
        'Symbol': daily_return.index,
        'Daily_Change_%': daily_return.values,
        'Period_Change_%': period_return.values
    })

    final_df = sp500.merge(performance_df, on='Symbol').dropna()
    final_df.columns = ['個股代號', '所屬產業', '子產業', '今日漲幅 (%)', '近10日總漲幅 (%)']
    
    # [cite: 47] 依照近10日漲幅由高至低排序，並只取前 20 名
    top_20_df = final_df.sort_values(by='近10日總漲幅 (%)', ascending=False).head(20)

    # 4. 產出 HTML 表格
    stock_table_html = top_20_df.to_html(index=False, classes='table table-striped', float_format="%.2f")

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>美股 10 日強勢股排行榜</title>
        <style>
            body {{ font-family: sans-serif; margin: 30px; background-color: #f4f7f6; }}
            .container {{ max-width: 900px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #2c3e50; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th {{ background: #27ae60; color: white; padding: 12px; }}
            td {{ padding: 10px; text-align: center; border-bottom: 1px solid #eee; }}
            tr:hover {{ background: #f1f1f1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>S&P 500 前 20 強強勢股 (近 10 日)</h1>
            <p style="text-align: center;">最後更新 (台灣): {tw_time_str}</p>
            {stock_table_html}
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("✅ 前 20 名排行更新成功")
except Exception as e:
    print(f"❌ 錯誤: {e}")
    raise e
