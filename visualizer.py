# -*- coding: utf-8 -*-
"""
台股本益比評價與價值投資選股系統 - 視覺化繪圖模組
負責生成 4 張極具專業法人感的精美投資圖表：
1. TOP 20 最低估個股長條圖 (展示低估幅度)
2. 全市場 PE 本益比分佈直方圖 (了解估值落點)
3. 不同產業的平均低估率與價值分數比較圖
4. 核心選股散佈圖：本益比 (PE) vs 股東權益報酬率 (ROE)，一眼找出「高成長、低估值」的黃金交叉股
【中文字型防亂碼設計】：
自動偵測 Windows 系統中的「微軟正黑體 (Microsoft JhengHei)」，保證圖表上的中文完美顯示，不出現方塊亂碼！
"""

import os
import matplotlib
# 使用 'Agg' 後端，可在背景直接生成並儲存圖表，不會彈出視窗，完美支持排程自動執行
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
from config import CHARTS_DIR

# ==============================================================================
# 中文字型與樣式設定
# ==============================================================================
plt.style.use("seaborn-v0_8-darkgrid" if "seaborn-v0_8-darkgrid" in plt.style.available else "fast")

# 尋找 Windows 系統的微軟正黑體
font_candidates = ["Microsoft JhengHei", "sans-serif", "Arial"]
for font in font_candidates:
    try:
        plt.rcParams["font.family"] = font
        plt.rcParams["axes.unicode_minus"] = False  # 解決負號 '-' 顯示為方塊的問題
        break
    except:
        pass

# 專業調色盤
COLOR_PRIMARY = "#1f77b4"  # 科技藍
COLOR_ACCENT = "#ff7f0e"   # 溫暖橘
COLOR_BG = "#f5f6f8"       # 優雅灰背景

class StockVisualizer:
    """
    圖表繪製類別
    """
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        
    def generate_all_charts(self):
        """
        一鍵生成所有 4 張圖表並儲存。
        """
        print("📊 正在繪製並輸出精美視覺化圖表...")
        
        # 建立保存目錄
        os.makedirs(CHARTS_DIR, exist_ok=True)
        
        self.plot_undervalued_bar()
        self.plot_pe_distribution()
        self.plot_sector_comparison()
        self.plot_pe_vs_roe_scatter()
        
        print(f"🎉 所有圖表已成功儲存至目錄：{os.path.abspath(CHARTS_DIR)}")

    def plot_undervalued_bar(self):
        """
        1. 最被低估個股排行長條圖 (取前 20 名展示)
        """
        plt.figure(figsize=(12, 6.5))
        
        # 取低估率前 20 名
        top_20 = self.df.head(20).copy()
        
        # 繪製漸層感的長條圖
        colors = sns.color_palette("coolwarm", len(top_20))
        bars = plt.bar(top_20["name"], top_20["undervalued_rate"], color=colors, edgecolor="grey", alpha=0.85)
        
        # 加數值標籤在柱狀圖上方
        for bar in bars:
            height = bar.get_height()
            plt.text(
                bar.get_x() + bar.get_width()/2.0, 
                height + 1, 
                f"{height:+.1f}%", 
                ha="center", 
                va="bottom", 
                fontsize=9, 
                fontweight="bold"
            )
            
        plt.title("🔥 台股最被低估個股 TOP 20 排行 (依合理價低估幅度)", fontsize=16, fontweight="bold", pad=20)
        plt.xlabel("股票名稱", fontsize=12, labelpad=10)
        plt.ylabel("股價相較合理價低估率 (%)", fontsize=12, labelpad=10)
        plt.xticks(rotation=45, ha="right", fontsize=10)
        plt.grid(axis="y", linestyle="--", alpha=0.7)
        plt.tight_layout()
        
        plt.savefig(os.path.join(CHARTS_DIR, "01_top_20_undervalued.png"), dpi=200)
        plt.close()

    def plot_pe_distribution(self):
        """
        2. PE 本益比分佈直方圖
        """
        plt.figure(figsize=(10, 6))
        
        # 過濾掉異常或小於零的 PE
        valid_pe = self.df[self.df["pe"] > 0]["pe"].dropna()
        
        # 繪製直方圖與核密度曲線
        sns.histplot(valid_pe, bins=15, kde=True, color="#2ca02c", edgecolor="white", alpha=0.6)
        
        # 標記市場中位數本益比
        median_pe = valid_pe.median()
        plt.axvline(median_pe, color="red", linestyle="--", linewidth=2, label=f"本益比中位數: {median_pe:.1f}倍")
        
        plt.title("📊 台股評估標的 PE (本益比) 分佈圖", fontsize=16, fontweight="bold", pad=15)
        plt.xlabel("本益比 (倍)", fontsize=12, labelpad=10)
        plt.ylabel("公司數量", fontsize=12, labelpad=10)
        plt.legend(fontsize=11)
        plt.grid(linestyle="--", alpha=0.5)
        plt.tight_layout()
        
        plt.savefig(os.path.join(CHARTS_DIR, "02_pe_distribution.png"), dpi=200)
        plt.close()

    def plot_sector_comparison(self):
        """
        3. 產業比較圖：比較不同產業別的平均低估率與價值分數
        """
        plt.figure(figsize=(11, 6))
        
        # 依照景氣循環分類與一般股分類
        # 計算各產業平均低估率
        sector_grouped = self.df.groupby("cyclical_sector").agg(
            avg_undervalued=("undervalued_rate", "mean"),
            avg_value_score=("value_score", "mean"),
            count=("symbol", "count")
        ).reset_index()
        
        # 排除無樣本或少於2個的分類以求視覺效果
        sector_grouped = sector_grouped.sort_values(by="avg_value_score", ascending=False)
        
        # 雙 Y 軸繪圖
        ax1 = sns.barplot(x="cyclical_sector", y="avg_value_score", data=sector_grouped, color="#1f77b4", alpha=0.7)
        plt.xlabel("產業類別 / 景氣分類", fontsize=12, labelpad=10)
        ax1.set_ylabel("平均法人綜合價值分數 (0~100)", color="#1f77b4", fontsize=12)
        ax1.tick_params(axis="y", labelcolor="#1f77b4")
        
        # 加上折線圖表示平均低估率
        ax2 = ax1.twinx()
        sns.lineplot(
            x="cyclical_sector", 
            y="avg_undervalued", 
            data=sector_grouped, 
            color="#d62728", 
            marker="o", 
            linewidth=3, 
            markersize=8, 
            ax=ax2
        )
        ax2.set_ylabel("平均合理低估率 (%)", color="#d62728", fontsize=12)
        ax2.tick_params(axis="y", labelcolor="#d62728")
        
        # 在折線點上加上文字標籤
        for i, val in enumerate(sector_grouped["avg_undervalued"]):
            ax2.text(i, val + 1.5, f"{val:+.1f}%", color="#d62728", ha="center", fontweight="bold", fontsize=9)
            
        plt.title("🏢 台股各產業板塊：價值分數與合理低估率對比", fontsize=16, fontweight="bold", pad=20)
        plt.tight_layout()
        
        plt.savefig(os.path.join(CHARTS_DIR, "03_sector_comparison.png"), dpi=200)
        plt.close()

    def plot_pe_vs_roe_scatter(self):
        """
        4. 散佈圖（PE vs ROE）：一眼看出高 ROE 且低 PE 的超級優質股
        """
        plt.figure(figsize=(11, 6.5))
        
        # 過濾正常範圍進行縮放，避免極端異常值撐大圖表
        plot_df = self.df[(self.df["pe"] > 0) & (self.df["pe"] < 50) & (self.df["roe"] > 0) & (self.df["roe"] < 50)].copy()
        
        # 使用價值分數作散佈點大小，低估率做顏色深淺
        scatter = plt.scatter(
            plot_df["pe"], 
            plot_df["roe"], 
            s=plot_df["value_score"] * 3.5, 
            c=plot_df["undervalued_rate"], 
            cmap="RdYlGn", 
            edgecolors="black", 
            alpha=0.8,
            linewidths=0.8
        )
        
        # 加上顏色條
        cbar = plt.colorbar(scatter)
        cbar.set_label("股價低估率 (%)", rotation=270, labelpad=15, fontsize=11)
        
        # 標記台灣前幾大權值股的名稱
        highlights = ["台積電", "聯發科", "鴻海", "中鋼", "長榮", "富邦金"]
        for idx, row in plot_df.iterrows():
            if row["name"] in highlights:
                plt.annotate(
                    row["name"],
                    (row["pe"], row["roe"]),
                    textcoords="offset points",
                    xytext=(0, 10),
                    ha="center",
                    fontsize=10,
                    fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="yellow", alpha=0.5, edgecolor="orange")
                )
                
        # 繪製四象限輔助線 (以平均本益比15，ROE 10%為黃金分隔線)
        plt.axvline(15, color="grey", linestyle="--", alpha=0.5)
        plt.axhline(10, color="grey", linestyle="--", alpha=0.5)
        
        # 加上象限文字說明
        plt.text(5, 45, "🌟 高ROE + 低PE\n(黃金價值選股區)", color="green", fontsize=11, fontweight="bold")
        plt.text(35, 5, "⚠️ 低ROE + 高PE\n(高风险泡沫區)", color="red", fontsize=11, fontweight="bold")
        
        plt.title("🎯 價值投資核心散佈圖：PE (本益比) vs ROE (股東權益報酬率)", fontsize=16, fontweight="bold", pad=20)
        plt.xlabel("目前本益比 (倍) [越低越划算]", fontsize=12, labelpad=10)
        plt.ylabel("股東權益報酬率 ROE (%) [越高越賺錢]", fontsize=12, labelpad=10)
        plt.grid(True, linestyle=":", alpha=0.6)
        plt.tight_layout()
        
        plt.savefig(os.path.join(CHARTS_DIR, "04_pe_vs_roe_scatter.png"), dpi=200)
        plt.close()

# 單獨測試此模組
if __name__ == "__main__":
    from data_fetcher import StockDataFetcher
    from analyzer import StockAnalyzer
    fetcher = StockDataFetcher()
    from config import STOCK_POOL
    df_raw = fetcher.fetch_all_data(STOCK_POOL)
    analyzer = StockAnalyzer(df_raw)
    df_analyzed = analyzer.run_analysis()
    
    visualizer = StockVisualizer(df_analyzed)
    visualizer.generate_all_charts()
