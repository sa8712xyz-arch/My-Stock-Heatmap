import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime
import requests
import io

try:
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
    # --- 給熱力圖用的單日數據 ---
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

    final_df = sp500.merge(performance_df, on='Symbol')
    final_df['Weight'] = 1 
    final_df = final_df.dropna()

    # --- 給折線圖用的 10 日時間序列數據 ---
    cum_returns = ((close_data / close_data.iloc[0]) - 1) * 100
    cum_returns.index = pd.to_datetime(cum_returns.index).strftime('%m-%d')
    
    # 【關鍵修復】重設索引並強制將第一欄命名為 'Date'，防止 KeyError
    cum_returns_reset = cum_returns.reset_index()
    cum_returns_reset.rename(columns={cum_returns_reset.columns[0]: 'Date'}, inplace=True)
    
    melted_df = cum_returns_reset.melt(id_vars=['Date'], var_name='Symbol', value_name='Return_%')
    trend_df = pd.merge(melted_df, sp500, on='Symbol').dropna()

    print("4. 繪製圖表與產生網頁...")
    # 圖表 1：原版熱力圖
    fig_treemap = px.treemap(
        final_df,
        path=[px.Constant("S&P 500 (點擊可放大)"), 'GICS Sector', 'GICS Sub-Industry', 'Symbol'],
        values='Weight',
        color='Daily_Change_%',
        hover_data=['Daily_Change_%', 'Period_Change_%'],
        color_continuous_scale='RdYlGn',
        color_continuous_midpoint=0,
        range_color=[-3, 3],
        title="1. 美股今日產業熱力圖快照"
    )
    fig_treemap.update_layout(margin=dict(t=40, l=10, r=10, b=10))

    # 圖表 2：板塊 10 日動能折線圖
    sector_trend = trend_df.groupby(['Date', 'GICS Sector'])['Return_%'].mean().reset_index()
    fig_sector = px.line(sector_trend, x='Date', y='Return_%', color='GICS Sector', markers=True, title='2. 十大產業 (Sector) 近 10 日資金動能趨勢')
    sector_html = fig_sector.to_html(full_html=False, include_plotlyjs='cdn') 

    # 圖表 3：個股 10 日動能透視鏡
    sectors = trend_df['GICS Sector'].unique()
    dropdown_options = ""
    stock_charts_html = ""

    for i, sector in enumerate(sectors):
        sector_data = trend_df[trend_df['GICS Sector'] == sector]
        fig_stock = px.line(sector_data, x='Date', y='Return_%', color='Symbol', hover_data=['GICS Sub-Industry'], markers=True, title=f'3. 個股動能透視：{sector}')
        display_style = "block" if i == 0 else "none"
        stock_charts_html += f"<div id='chart-{i}' class='stock-chart' style='display:{display_style}; width:100%;'>"
        stock_charts_html += fig_stock.to_html(full_html=False, include_plotlyjs=False)
        stock_charts_html += "</div>"
        dropdown_options += f"<option value='chart-{i}'>{sector}</option>"

    # 組合最終網頁
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>美股進階資金輪動儀表板</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
            .container {{ max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #333; }}
            .dropdown-container {{ margin: 20px 0; padding: 15px; background: #e9ecef; border-radius: 5px; text-align: center; }}
            select {{ padding: 10px; font-size: 16px; border-radius: 5px; cursor: pointer; }}
        </style>
        <script>
            function changeSector(chartId) {{
                var charts = document.getElementsByClassName('stock-chart');
                for (var i = 0; i < charts.length; i++) {{
                    charts[i].style.display = 'none';
                }}
                document.getElementById(chartId).style.display = 'block';
            }}
        </script>
    </head>
    <body>
        <div class="container">
            <h1>美股資金輪動儀表板 (更新時間: {datetime.now().strftime('%Y-%m-%d')})</h1>
            {fig_treemap.to_html(full_html=False, include_plotlyjs=False)}
            <hr style="margin: 40px 0;">
            {sector_html}
            <hr style="margin: 40px 0;">
            <div class="dropdown-container">
                <label for="sector-select" style="font-size: 18px; font-weight: bold;">🔍 選擇板塊以檢視內部個股輪動：</label>
                <select id="sector-select" onchange="changeSector(this.value)">
                    {dropdown_options}
                </select>
            </div>
            {stock_charts_html}
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

    print("✅ 執行完畢！已生成升級版 index.html")
except Exception as e:
    print(f"❌ 發生致命錯誤: {e}")
    raise e
