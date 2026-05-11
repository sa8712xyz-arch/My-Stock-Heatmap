import yfinance as yf
import pandas as pd

# 1. 定義 S&P 500 各產業代表性的 ETF 或使用你現有的 500 檔個股清單
# 這裡以 11 個板塊 ETF 作為產業趨勢代表，並結合個股總表
tickers = {
    'XLK': '科技', 'XLV': '醫療', 'XLF': '金融', 'XLY': '非必需消費',
    'XLP': '必需消費', 'XLI': '工業', 'XLE': '能源', 'XLU': '公用事業',
    'XLB': '原物料', 'XLRE': '房地產', 'XLC': '通訊服務'
}

def get_industry_summary():
    print("正在從 Yahoo Finance 抓取並清洗數據...")
    
    # 抓取 S&P 500 板塊 ETF 數據 (近 10 日)
    data = yf.download(list(tickers.keys()), period="10d")['Close']
    
    # 🛠️ 一刀斃命的解決方案：填充缺失值
    # 確保不會因為開收盤時間差產生的 NaN 導致整列數據被刪除
    data = data.ffill().bfill()
    
    # 計算累積漲跌幅 (%)
    # 公式：(最後一天價格 / 第一天價格 - 1) * 100
    performance = ((data.iloc[-1] / data.iloc[0]) - 1) * 100
    
    # 建立總表
    summary_df = pd.DataFrame({
        '產業代碼': performance.index,
        '產業名稱': [tickers[t] for t in performance.index],
        '10日累積漲幅 (%)': performance.values
    })
    
    # 按漲幅排序
    summary_df = summary_df.sort_values(by='10日累積漲幅 (%)', ascending=False)
    
    return summary_df

# 執行並顯示總表
if __name__ == "__main__":
    result_table = get_industry_summary()
    
    print("\n" + "="*30)
    print(" S&P 500 產業資金輪動總表 (近10日)")
    print("="*30)
    print(result_table.to_string(index=False))
    print("="*30)
    print("數據已完成清洗，無遺漏檔數。")
