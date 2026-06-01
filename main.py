# -*- coding: utf-8 -*-
"""
台股本益比評價與價值投資選股系統 - 主程式 (Main Entry)
作者：台灣股票量化分析師 / FinTech 系統架構師
功能：
1. 讀取股票池配置 (config.py)
2. 呼叫數據抓取引擎，取得即時股價與基礎面數據 (data_fetcher.py)
3. 執行財務指標運算、法人多因子估值模型、F-Score 與神奇公式排行 (analyzer.py)
4. 導出具備投行美感的 Excel 選股報表 (report_generator.py)
5. 繪製 4 張包含本益比/ROE/產業比較的投資視覺化圖表 (visualizer.py)
"""

import os
import sys
import io
import time

# ==============================================================================
# Windows 終端機編碼防護 (Unicode/CP950 Encoding Safe Guard)
# ==============================================================================
# 當在 Windows 環境下使用 PowerShell 或 cmd 執行時，預設 CP950 編碼無法輸出 Emoji。
# 我們在此強制標準輸出使用 UTF-8 編碼，以確保 100% 順暢印出所有繁體中文與 Emoji 符號，絕不報錯崩潰！
if sys.platform.startswith("win"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

from config import STOCK_POOL, EXCEL_PATH, CHARTS_DIR
from data_fetcher import StockDataFetcher
from analyzer import StockAnalyzer
from report_generator import ExcelReportGenerator
from visualizer import StockVisualizer

def main():
    """
    系統執行主流程
    """
    start_time = time.time()
    
    print("=" * 70)
    print("      📈 歡迎使用【台股本益比評價與法人級價值投資選股系統】v1.0 📈")
    print("=" * 70)
    print(f"⏰ 當前系統時間：{time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📂 輸出檔案路徑：{os.path.abspath(EXCEL_PATH)}")
    print(f"📊 視覺圖表目錄：{os.path.abspath(CHARTS_DIR)}")
    print("=" * 70)
    
    try:
        # 步驟 1: 數據抓取階段
        print("\n🚀 [步驟 1/4] 啟動數據抓取引擎...")
        fetcher = StockDataFetcher()
        df_raw = fetcher.fetch_all_data(STOCK_POOL)
        
        if df_raw.empty:
            print("❌ 錯誤：未能成功獲取任何股票數據，程式終止！")
            return
            
        # 步驟 2: 量化分析階段
        print("\n🚀 [步驟 2/4] 啟動多因子評價與體質篩選模型...")
        analyzer = StockAnalyzer(df_raw)
        df_analyzed = analyzer.run_analysis()
        
        # 步驟 3: 匯出 Excel 報表
        print("\n🚀 [步驟 3/4] 產生並美化 Excel 投資排行榜報表...")
        generator = ExcelReportGenerator(df_analyzed)
        generator.export_to_excel()
        
        # 步驟 4: 繪製視覺化圖表
        print("\n🚀 [步驟 4/4] 繪製投資決策輔助圖表...")
        visualizer = StockVisualizer(df_analyzed)
        visualizer.generate_all_charts()
        
        # 成果總結輸出
        print("\n" + "=" * 70)
        print("🎉 恭喜！系統全部流程順利完成！ 🎉")
        print("=" * 70)
        
        # 秀出低估榜前 5 名，給使用者一個即時的反饋
        print("\n🔥 台股最被低估價值股 TOP 5：")
        print("-" * 70)
        top_5 = df_analyzed.head(5)
        for i, (_, row) in enumerate(top_5.iterrows(), 1):
            print(f"第 {i} 名 | {row['symbol']} {row['name']:<5} | 收盤價: {row['close_price']:>7.2f} 元 | "
                  f"合理價: {row['fair_price']:>7.2f} 元 | 低估幅度: {row['undervalued_rate']:>+6.2f}% | "
                  f"體質: {row['health_status']}")
        print("-" * 70)
        
        elapsed_time = time.time() - start_time
        print(f"⏱️ 系統運行總耗時：{elapsed_time:.2f} 秒。")
        print("💡 提示：現在您可以打開 outputs/PE_Ranking.xlsx 或 outputs/charts/ 查看完整成果！")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n⚠️ 偵測到手動中斷，程式已安全退出。")
    except Exception as e:
        print(f"\n❌ 系統執行過程中發生未預期錯誤: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
