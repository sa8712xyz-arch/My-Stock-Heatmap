import pandas as pd
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta
import requests
import io

try:
    # 取得台灣時間
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

    final_df = sp500.merge(performance_df, on='Symbol')
    final_df['Weight'] = 1 
    final_df['Root'] = "S&P 500 (點擊可放大)" 
    final_df = final_df.dropna()

    # --- 折線圖時間序列數據 ---
    cum_returns = ((close_data / close_data.iloc[0]) - 1) * 100
    cum_returns.index = pd.to_datetime(cum_returns.index).tz_localize(None).strftime('%Y-%m-%d')
    
    cum_returns_reset = cum_returns.reset_index()
    cum_returns_reset.rename(columns={cum_returns_reset.columns[0]: 'Date'}, inplace=True)
    
    melted_df = cum_returns_reset.melt(id_vars=['Date'], var_name='Symbol', value_name='Return_%')
    trend_df = pd.merge(melted_df, sp500, on='Symbol').dropna()

    print("4. 繪製圖表與產生網頁...")
    
    # ================== 新增：動態色階計算引擎 ==================
    # 計算當日漲跌幅的絕對值，並取 95% 的分位數作為顏色的極限值，排除極端暴漲暴跌干擾
    color_limit = final_df['Daily_Change_%'].abs().quantile(0.95)
    # 防呆：如果當天波動真的太小，設定一個最低門檻 1.5%，避免些微雜訊被過度放大
    if pd.isna(color_limit) or color_limit < 1.5:
        color_limit = 1.5
    # ==========================================================

    fig_treemap = px.treemap(
        final_df,
        path=['Root', 'GICS Sector', 'GICS Sub-Industry', 'Symbol'],
        values='Weight',
        color='Daily_Change_%',
        hover_data=['Daily_Change_%', 'Period_Change_%'],
        # 使用高對比五段式色階
        color_continuous_scale=[
            (0.00, "#8B0000"), # 深紅 (極弱)
            (0.25, "#FF4500"), # 亮紅 (偏弱)
            (0.50, "#FFFFFF"), # 純白 (平盤)
            (0.75, "#32CD32"), # 亮綠 (偏強)
            (1.00, "#006400")  # 深綠 (極強)
        ],
        color_continuous_midpoint=0,
        range_color=[-color_limit, color_limit],
        title=f"1. 美股今日產業熱力圖快照 (已啟用動態對比, 視覺極限值: ±{color_limit:.1f}%)",
        height=750  
    )
    fig_treemap.update_layout(margin=dict(t=40, l=10, r=10, b=10))

    sector_trend = trend_df.groupby(['Date', 'GICS Sector'])['Return_%'].mean().reset_index()
    fig_sector = px.line(sector_trend, x='Date', y='Return_%', color='GICS Sector', markers=True, title='2. 十大產業 (Sector) 近 10 日資金動能趨勢')
    
    treemap_html = fig_treemap.to_html(full_html=False, include_plotlyjs=False)
    sector_html = fig_sector.to_html(full_html=False, include_plotlyjs=False) 

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

    table_df = final_df[['Symbol', 'GICS Sector', 'GICS Sub-Industry', 'Daily_Change_%', 'Period_Change_%']].copy()
    table_df.columns = ['個股代號', '所屬產業', '子產業', '今日漲幅 (%)', '近10日總漲幅 (%)']
    table_df = table_df.sort_values(by='近10日總漲幅 (%)', ascending=False)
    stock_table_html = table_df.to_html(index=False, classes='table table-striped table-hover', float_format="%.2f")

    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>美股進階資金輪動儀表板</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f8f9fa; }}
            .container {{ max-width: 1200px; margin: auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h1 {{ text-align: center; color: #333; }}
            .dropdown-container {{ margin: 20px 0; padding: 15px; background: #e9ecef; border-radius: 5px; text-align: center; }}
            select {{ padding: 10px; font-size: 16px; border-radius: 5px; cursor: pointer; }}
            .table-container {{ max-height: 500px; overflow-y: auto; margin-top: 20px; border: 1px solid #ddd; border-radius: 5px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ padding: 12px; text-align: center; border-bottom: 1px solid #ddd; }}
            th {{ background-color: #343a40; color: white; position: sticky; top: 0; z-index: 1; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            tr:hover {{ background-color: #e9ecef; }}
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
            <h1>美股資金輪動儀表板 (更新時間: {tw_time_str} 台灣時間)</h1>
            {treemap_html}
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
            <hr style="margin: 40px 0;">
            <h2 style="text-align: center; color: #333;">4. S&P 500 個股排行榜 (近10日漲跌幅)</h2>
            <p style="text-align: center; color: #666;">※ 表格可上下滑動，已依照「近10日總漲幅」由高至低排序</p>
            <div class="table-container">
                {stock_table_html}
            </div>
        </div>
    </body>
    </html>
    """

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

    print("✅ 執行完畢！已生成高對比完美版 index.html")
except Exception as e:
    print(f"❌ 發生致命錯誤: {e}")
    raise e
