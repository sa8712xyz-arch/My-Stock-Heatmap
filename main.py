import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import requests
import io

try:
    # 取得台灣時間
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

    print("2. 下載近 10 天數據並進行資料搶救...")
    data = yf.download(tickers, period="10d")['Close']
    
    # 【關鍵】填補空白資料，防止股票被誤刪
    data = data.ffill().bfill()
    
    print("3. 計算漲跌幅與排名...")
    daily_return = ((data.iloc[-1] / data.iloc[-2]) - 1) * 100
    period_return = ((data.iloc[-1] / data.iloc[0]) - 1) * 100

    performance_df = pd.DataFrame({
        'Symbol': daily_return.index,
        'Daily_Change_%': daily_return.values,
        'Period_Change_%': period_return.values
    })

    final_df = sp500.merge(performance_df, on='Symbol').dropna()
    final_df.columns = ['個股代號', '所屬產業', '子產業', '今日漲幅 (%)', '近10日總漲幅 (%)']
    final_df = final_df.sort_values(by='近10日總漲幅 (%)', ascending=False)

    # 4. 產出純淨 HTML 表格
    stock_table_html = final_df.to_html(index=False, classes='table table-striped', float_format="%.2f")

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>美股資金輪動監控</title>
        <style>
            body {{ font-family: sans-serif; margin: 30px; background-color: #f4f7f6; }}
            .container {{ max-width: 1000px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1, h2 {{ text-align: center; color: #2c3e50; }}
            .table-container {{ max-height: 800px; overflow-y: auto; border: 1px solid #eee; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th {{ background: #34495e; color: white; position: sticky; top: 0; padding: 12px; }}
            td {{ padding: 10px; text-align: center; border-bottom: 1px solid #eee; }}
            tr:hover {{ background: #f9f9f9; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>美股個股排行榜</h1>
            <p style="text-align: center;">最後更新 (台灣): {tw_time_str}</p>
            <div class="table-container">
                {stock_table_html}
            </div>
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)
    print("✅ 網頁更新成功")
except Exception as e:
    print(f"❌ 錯誤: {e}")
    raise e
