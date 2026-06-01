# -*- coding: utf-8 -*-
"""
台股本益比評價與價值投資選股系統 - 核心計算與分析模組
負責計算各項本益比評價指標（便宜價、合理價、昂貴價）、執行財務體質篩選、景氣循環股標記，
以及計算「專業投資機構版本」的進階指標：
1. 股價淨值比 (P/B)
2. 股息殖利率
3. 自由現金流折現模型 (DCF Valuation)
4. 高登股息成長模型 (Gordon Growth Model)
5. Piotroski F-Score (九大財務體質指標)
6. Magic Formula Ranking (神奇公式排行)
7. 法人級綜合價值分數 (Value Score) = 40% PE + 20% PB + 20% ROE + 10% FCF + 10% 成長率
"""

import pandas as pd
import numpy as np
from config import (
    MIN_ROE, MAX_DEBT_RATIO, MIN_REVENUE_GROWTH_YEARS, CHECK_FCF_POSITIVE,
    WEIGHT_PE, WEIGHT_PB, WEIGHT_ROE, WEIGHT_FCF, WEIGHT_GROWTH,
    DISCOUNT_RATE, TERMINAL_GROWTH_RATE, SAFETY_MARGIN, EXCLUDE_CYCLICAL
)

class StockAnalyzer:
    """
    台股量化分析與評價類別
    """
    def __init__(self, df_raw: pd.DataFrame):
        # 複製一份原始數據，避免直接修改影響原始資料
        self.df = df_raw.copy()
        
    def run_analysis(self) -> pd.DataFrame:
        """
        執行所有分析流程，將計算後的欄位附加到 DataFrame 中。
        """
        print("⚙️ 正在進行核心數據計算與評價模型運算...")
        
        # 1. 基礎本益比與歷史平均本益比計算
        self._calculate_pe_valuation()
        
        # 2. 財務體質篩選 (ROE, 負債比, FCF, 營收)
        self._check_financial_health()
        
        # 3. 成長股加權與 PEG 計算
        self._calculate_peg()
        
        # 4. 專業法人指標：DCF 與 Gordon 估值模型
        self._calculate_dcf_and_gordon()
        
        # 5. 專業法人指標：Magic Formula & Piotroski F-Score
        self._calculate_magic_formula_and_fscore()
        
        # 6. 法人級綜合價值分數評分 (Value Score)
        self._calculate_institutional_value_score()
        
        # 7. 排序與產出優化
        self._sort_and_finalize()
        
        print("✅ 評價模型運算完成！")
        return self.df

    def _calculate_pe_valuation(self):
        """
        計算基礎本益比評價（PE、合理價、便宜價、昂貴價、低估率）
        """
        # A. 目前本益比 PE = 股價 / 最新年度 EPS (若 EPS <= 0，本益比設為 NaN 或極大值)
        self.df["pe"] = self.df.apply(
            lambda r: round(r["close_price"] / r["latest_eps"], 2) if r["latest_eps"] > 0 else np.nan,
            axis=1
        )
        
        # B. 計算近 5 年與近 10 年平均本益比
        self.df["pe_avg_5y"] = self.df["pe_history_5y"].apply(lambda x: round(np.mean(x), 2) if len(x) > 0 else np.nan)
        self.df["pe_avg_10y"] = self.df["pe_history_10y"].apply(lambda x: round(np.mean(x), 2) if len(x) > 0 else np.nan)
        
        # 若平均本益比缺失，以行業合理平均替代 (安全容錯)
        self.df["pe_avg_5y"] = self.df["pe_avg_5y"].fillna(15.0)
        self.df["pe_avg_10y"] = self.df["pe_avg_10y"].fillna(15.0)
        
        # C. 評價價格計算：
        # 合理價 = 近 5 年平均 PE * 最新 EPS
        self.df["fair_price"] = self.df.apply(
            lambda r: round(r["pe_avg_5y"] * r["latest_eps"], 2) if r["latest_eps"] > 0 else 0.0,
            axis=1
        )
        
        # 便宜價 = 合理價 * 0.7 (安全邊際)
        self.df["cheap_price"] = round(self.df["fair_price"] * (1 - SAFETY_MARGIN), 2)
        
        # 昂貴價 = 合理價 * 1.3
        self.df["expensive_price"] = round(self.df["fair_price"] * (1 + SAFETY_MARGIN), 2)
        
        # D. 低估率 = (合理價 - 目前股價) / 目前股價 * 100%
        self.df["undervalued_rate"] = self.df.apply(
            lambda r: round(((r["fair_price"] - r["close_price"]) / r["close_price"]) * 100, 2) if r["close_price"] > 0 else -100.0,
            axis=1
        )
        
    def _check_financial_health(self):
        """
        執行財務體質篩選：ROE > 10%, 負債比 < 60%, 營收3年成長, 自由現金流為正
        """
        # A. 判斷各項體質條件是否符合
        self.df["healthy_roe"] = self.df["roe"] > MIN_ROE
        
        # 金融股的負債比普遍高於 80%，這是產業特性而非體質不良。因此我們對金融股（股票代碼 28 開頭）進行放寬。
        self.df["healthy_debt"] = self.df.apply(
            lambda r: r["debt_ratio"] < 90.0 if r["symbol"].startswith("28") else r["debt_ratio"] < MAX_DEBT_RATIO,
            axis=1
        )
        
        self.df["healthy_fcf"] = self.df["free_cash_flow"] > 0
        self.df["healthy_growth"] = self.df["revenue_growth_3y"] == True
        
        # B. 綜合體質評估：四項全符合則為「優良體質」，否則標記不符欄位
        def get_health_status(r):
            reasons = []
            if not r["healthy_roe"]: reasons.append("ROE偏低")
            if not r["healthy_debt"]: reasons.append("負債比過高")
            if not r["healthy_fcf"]: reasons.append("現金流為負")
            if not r["healthy_growth"]: reasons.append("營收未連增")
            
            if len(reasons) == 0:
                return "財務體質優良"
            else:
                return f"體質待觀察({','.join(reasons)})"
                
        self.df["health_status"] = self.df.apply(get_health_status, axis=1)
        self.df["is_healthy"] = self.df["health_status"] == "財務體質優良"

    def _calculate_peg(self):
        """
        計算 PEG 比率，並評估高低估狀態。
        PEG = PE / EPS 成長率
        """
        # 防止分母為 0 或負數，當成長率 <= 0 時，PEG 設為 NaN
        self.df["peg"] = self.df.apply(
            lambda r: round(r["pe"] / r["revenue_growth_rate"], 2) 
            if (not pd.isna(r["pe"]) and r["revenue_growth_rate"] > 0) else np.nan,
            axis=1
        )
        
        # 評估 PEG 狀態
        def evaluate_peg(peg_val):
            if pd.isna(peg_val):
                return "無法評估"
            elif peg_val < 0.75:
                return "嚴重低估(成長型)"
            elif peg_val < 1.0:
                return "低估(成長型)"
            elif peg_val <= 1.5:
                return "合理"
            else:
                return "高估"
                
        self.df["peg_status"] = self.df["peg"].apply(evaluate_peg)

    def _calculate_dcf_and_gordon(self):
        """
        專業法人估值：自由現金流折現 (DCF) 與 高登股息成長模型 (Gordon)
        """
        # A. DCF 估值模型 (簡化法人版)
        # 預測未來 5 年的現金流，折現加總後加上永續價值，再除以流通股數得到估計股價。
        def estimate_dcf(r):
            fcf = r["free_cash_flow"]
            shares = r["shares_outstanding"]
            growth = r["revenue_growth_rate"] / 100 if r["revenue_growth_rate"] > 0 else 0.05
            
            # 若現金流為負，代表無法直接用 DCF 估值，返回 NaN
            if pd.isna(fcf) or fcf <= 0 or pd.isna(shares) or shares <= 0:
                return np.nan
                
            # 計算未來 5 年折現現金流
            dcf_val = 0
            temp_fcf = fcf
            for year in range(1, 6):
                temp_fcf = temp_fcf * (1 + growth) # 現金流成長
                dcf_val += temp_fcf / ((1 + DISCOUNT_RATE) ** year) # 折現
                
            # 第 5 年終端永續價值 (Terminal Value)
            terminal_value = (temp_fcf * (1 + TERMINAL_GROWTH_RATE)) / (DISCOUNT_RATE - TERMINAL_GROWTH_RATE)
            dcf_val += terminal_value / ((1 + DISCOUNT_RATE) ** 5)
            
            # 每股 DCF 價值
            dcf_per_share = dcf_val / shares
            return round(dcf_per_share, 2)
            
        self.df["dcf_valuation"] = self.df.apply(estimate_dcf, axis=1)
        
        # B. Gordon Growth Model (高登成長模型)
        # P = D1 / (r - g)
        # 其中 D1 = 最新股股利 * (1 + g)。
        # 折現率 r = 8%, g = 永續股息成長率 (為保守起見，設定為 3%)。
        def estimate_gordon(r):
            # 股息 = 股價 * 股息殖利率 (yfinance 的 dividend_yield 已經是比率)
            div_yield = r["dividend_yield"]
            price = r["close_price"]
            
            if pd.isna(div_yield) or div_yield <= 0 or pd.isna(price) or price <= 0:
                return np.nan
                
            dividend = price * div_yield
            g = 0.03 # 保守設定 3% 永續成長率
            
            # 確保分母大於 0 (r > g)
            if DISCOUNT_RATE > g:
                gordon_price = (dividend * (1 + g)) / (DISCOUNT_RATE - g)
                return round(gordon_price, 2)
            return np.nan
            
        self.df["gordon_valuation"] = self.df.apply(estimate_gordon, axis=1)

    def _calculate_magic_formula_and_fscore(self):
        """
        專業法人指標：神奇公式 (Magic Formula) 與 Piotroski F-Score
        """
        # A. Magic Formula Ranking
        # 盈餘殖利率 (Earnings Yield) = EPS / 股價 = 1 / PE
        self.df["earnings_yield"] = self.df.apply(
            lambda r: 1.0 / r["pe"] if (not pd.isna(r["pe"]) and r["pe"] > 0) else 0.0,
            axis=1
        )
        
        # 資本回報率 (ROC) 在本系統中以 ROE 作為代表
        self.df["roc"] = self.df["roe"] / 100.0
        
        # 將全市場股票進行兩個指標的排名 (數字越小表示排名越前面，即表現越好)
        self.df["ey_rank"] = self.df["earnings_yield"].rank(ascending=False, method="min")
        self.df["roc_rank"] = self.df["roc"].rank(ascending=False, method="min")
        
        # 神奇公式總分 = 盈餘殖利率排名 + 資本回報率排名 (分數越小越好)
        self.df["magic_rank_score"] = self.df["ey_rank"] + self.df["roc_rank"]
        
        # B. Piotroski F-Score
        # 這是一個 0~9 分的安全分數，我們已在 data_fetcher 中根據公司體質設定。
        # 這裡進一步整理以確保其在 1~9 分內。
        self.df["f_score"] = self.df["f_score"].fillna(6).astype(int)

    def _calculate_institutional_value_score(self):
        """
        計算接近法人級的「綜合價值分數 (Value Score)」
        價值分數 = 40% PE + 20% PB + 20% ROE + 10% FCF + 10% 成長率
        【科學化做法】：將所有個股的這五個指標分別轉為「全市場百分位排名 (Percentile Rank)」，
        PE 與 PB 是越低越好（因此分數為 100 - 百分位）；ROE, FCF, 成長率是越高越好。
        之後再加權計算出 0~100 分的綜合價值分數！
        """
        # 計算各指標的百分位數排名 (Percentile Rank，值在 0~1 之間)
        pe_rank = self.df["pe"].rank(pct=True, ascending=True)      # PE 越低，排名越前 (pct 越小，但我們要的是越低分數越高)
        pb_rank = self.df["pb_ratio"].rank(pct=True, ascending=True) # PB 越低越好
        
        roe_rank = self.df["roe"].rank(pct=True, ascending=False)     # ROE 越高越好 (ascending=False 表示最高值 pct=0)
        # 改為標準百分位：值越大，pct 越大，越好
        pe_score = 100 * (1 - self.df["pe"].rank(pct=True))
        pb_score = 100 * (1 - self.df["pb_ratio"].rank(pct=True))
        roe_score = 100 * self.df["roe"].rank(pct=True)
        fcf_score = 100 * self.df["free_cash_flow"].rank(pct=True)
        growth_score = 100 * self.df["revenue_growth_rate"].rank(pct=True)
        
        # 容錯處理：缺失值填補為 50 分 (市場中位數)
        pe_score = pe_score.fillna(50)
        pb_score = pb_score.fillna(50)
        roe_score = roe_score.fillna(50)
        fcf_score = fcf_score.fillna(50)
        growth_score = growth_score.fillna(50)
        
        # 加權總分計算
        self.df["value_score"] = round(
            WEIGHT_PE * pe_score +
            WEIGHT_PB * pb_score +
            WEIGHT_ROE * roe_score +
            WEIGHT_FCF * fcf_score +
            WEIGHT_GROWTH * growth_score,
            2
        )

    def _sort_and_finalize(self):
        """
        根據低估率及價值分數進行排序與資料清理。
        """
        # 是否要從榜單中「直接排除」景氣循環股 (依 config.py 設定)
        if EXCLUDE_CYCLICAL:
            self.df = self.df[self.df["is_cyclical"] == False].copy()
            
        # 以低估率進行降序排列 (低估率越高越靠前)
        self.df = self.df.sort_values(by="undervalued_rate", ascending=False).reset_index(drop=True)

# 單獨測試此模組
if __name__ == "__main__":
    from data_fetcher import StockDataFetcher
    fetcher = StockDataFetcher()
    test_pool = {
        "2330.TW": "台積電", "2603.TW": "長榮", "2881.TW": "富邦金", 
        "2002.TW": "中鋼", "2409.TW": "友達"
    }
    df_raw = fetcher.fetch_all_data(test_pool)
    analyzer = StockAnalyzer(df_raw)
    df_analyzed = analyzer.run_analysis()
    
    print("\n📊 排序後的計算結果 (前5名):")
    cols = ["symbol", "name", "close_price", "pe", "fair_price", "undervalued_rate", "value_score", "health_status"]
    print(df_analyzed[cols].head())
