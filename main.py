import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta
import requests
import io

try:
    # 1. 取得台灣時間
    tw_time = datetime.utcnow() + timedelta(hours=8)
    tw_time_str = tw_time.strftime('%Y-%m-%d %H:%M')

    print("1. 正在從維基百科獲取 S&P 500 最新成分股...")
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    tables = pd.read_html(io.StringIO(response.text))
    sp500 = tables[0][['Symbol', 'GICS Sector', 'GICS Sub-Industry']]
    sp500['Symbol'] = sp500['Symbol'].str.replace('.', '-', regex=False)
    tickers = sp500['Symbol'].tolist()

    print("2. 正在從 Yahoo Finance 下載近 10 天的歷史價格...")
    data = yf.download(tickers, period="10d")
    
    if isinstance(data.columns, pd.MultiIndex):
        close_data = data['Close']
    else:
        close_data = data
        
    print("3. 數據運算與處理中...")
    if len(close_data) >= 2:
        daily_return = ((close_data.iloc[-1] / close_data.iloc[-2]) - 1) * 100
    else:
        daily_return = close_data.iloc[-1] * 0

    if len(close_data) >= 1:
        period_return = ((close_data.iloc[-1] / close_data.iloc[0]) - 1) * 100
    else:
        period_return = daily_return

    performance_df = pd.DataFrame({
        'Symbol': daily_return.index,
        'Daily_Change_%': daily_return.values,
        'Period_Change_%': period_return.values
    })

    final_df = sp500.merge(performance_df, on='Symbol').dropna()

    # --- 產業折線圖專用的時間序列數據 ---
    cum_returns = ((close_data / close_data.iloc[0]) - 1) * 100
    cum_returns.index = pd.to_datetime(cum_returns.index).tz_localize(None)
    
    cum_returns_reset = cum_returns.reset_index()
    cum_returns_reset.rename(columns={cum_returns_reset.columns[0]: 'Date'}, inplace=True)
    
    melted_df = cum_returns_reset.melt(id_vars=['Date'], var_name='Symbol', value_name='Return_%')
    trend_df = pd.merge(melted_df, sp500, on='Symbol').dropna()

    print("4. 繪製圖表與產生網頁...")

    # 【區塊 1】十大產業動能折線圖
    sector_trend = trend_df.groupby(['Date', 'GICS Sector'])['Return_%'].mean().reset_index()
    fig_sector = px.line(sector_trend, x='Date', y='Return_%', color='GICS Sector', markers=True, title='1. 十大產業 (Sector) 近 10 日資金動能趨勢')
    fig_sector.update_xaxes(tickformat="%Y-%m-%d")
    
    # ====== 核心修正：強制鎖定圖例，不允許任何線條被隱藏 ======
    fig_sector.update_layout(
        legend_itemclick=False,
        legend_itemdoubleclick=False
    )
    # =======================================================
    
    sector_html = fig_sector.to_html(full_html=False, include_plotlyjs=False) 

    # 【區塊 2】S&P 500 個股總排行表
    table_df = final_df[['Symbol', 'GICS Sector', 'GICS Sub-Industry', 'Daily_Change_%', 'Period_Change_%']].copy()
    table_df.columns = ['個股代號', '所屬產業', '子產業', '今日漲幅 (%)', '近10日總漲幅 (%)']
    table_df = table_df.sort_values(by='近10日總漲幅 (%)', ascending=False)
    stock_table_html = table_df.to_html(index=False, classes='table table-striped table-hover', float_format="%.2f")

    # --- 組合最終網頁 ---
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>美股資金輪動儀表板</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
            .container {{ max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #333; }}
            
            /* 表格的專屬 CSS 美化 */
            .table-container {{ max-height: 800px; overflow-y: auto; margin-top: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #343a40; color: white; position: sticky; top: 0; z-index: 1; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #e9ecef; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>美股資金輪動儀表板 (更新時間: {tw_time_str} 台灣時間)</h1>
            
            {sector_html}
            
            <hr style="margin: 40px 0;">
            
            <h2 style="text-align: center; color: #333;">2. S&P 500 個股排行榜 (近 10 日漲跌幅)</h2>
            <p style="text-align: center; color: #666;">※ 表格可上下滑動，已依照「近 10 日總漲幅」由高至低排序</p>
            <div class="table-container">
                {stock_table_html}
            </div>
            
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

    print("✅ 執行完畢！已強制鎖定全部線條顯示")
except Exception as e:
    print(f"❌ 發生致命錯誤: {e}")
    raise e
