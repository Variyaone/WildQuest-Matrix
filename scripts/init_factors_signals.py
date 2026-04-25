#!/usr/bin/env python3
"""
因子和信号初始化脚本

自动注册策略依赖的所有因子和信号定义。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.factor import (
    get_factor_registry,
    reset_factor_registry,
    FactorCategory,
    FactorSubCategory,
    FactorDirection,
    FactorStatus
)
from core.signal import (
    get_signal_registry,
    reset_signal_registry,
    SignalType,
    SignalDirection,
    SignalStatus,
    SignalRules
)


FACTORS_TO_REGISTER = [
    {
        "name": "MA_5_20_Cross",
        "description": "5日均线与20日均线交叉信号因子。当短期均线上穿长期均线时产生买入信号。",
        "formula": "MA(close, 5) - MA(close, 20)",
        "source": "经典技术指标",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["均线", "趋势", "技术分析"]
    },
    {
        "name": "MA_10_60_Cross",
        "description": "10日均线与60日均线交叉信号因子。中期趋势确认信号。",
        "formula": "MA(close, 10) - MA(close, 60)",
        "source": "经典技术指标",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["均线", "趋势", "技术分析"]
    },
    {
        "name": "Momentum_3M",
        "description": "3个月(63日)价格动量因子。衡量中期价格趋势强度。",
        "formula": "(close - close.shift(63)) / close.shift(63)",
        "source": "经典动量因子",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.TIME_SERIES_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "tags": ["动量", "趋势"]
    },
    {
        "name": "Reversal_1M",
        "description": "1个月(21日)反转因子。捕捉短期超跌反弹机会。",
        "formula": "(close - close.shift(21)) / close.shift(21)",
        "source": "经典反转因子",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.REVERSAL_FACTOR,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["反转", "短期"]
    },
    {
        "name": "Volume_Breakout",
        "description": "成交量突破因子。当成交量超过20日均量的1.5倍时触发。",
        "formula": "volume / MA(volume, 20)",
        "source": "经典量价因子",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["成交量", "突破"]
    },
    {
        "name": "PE_Ratio",
        "description": "市盈率因子。衡量股票估值水平，PE越低越有投资价值。",
        "formula": "market_cap / net_profit",
        "source": "基本面因子",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["估值", "价值投资", "基本面"]
    },
    {
        "name": "PB_Ratio",
        "description": "市净率因子。衡量股价相对于净资产的估值水平。",
        "formula": "market_cap / net_assets",
        "source": "基本面因子",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["估值", "价值投资", "基本面"]
    },
    {
        "name": "ROE_Growth",
        "description": "ROE增长率因子。衡量公司盈利能力的改善程度。",
        "formula": "(ROE_t - ROE_t-4) / abs(ROE_t-4)",
        "source": "基本面因子",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.PROFITABILITY,
        "direction": FactorDirection.POSITIVE,
        "tags": ["盈利能力", "成长", "基本面"]
    },
    {
        "name": "Earnings_Growth",
        "description": "净利润增长率因子。衡量公司盈利增长速度。",
        "formula": "(net_profit_t - net_profit_t-4) / abs(net_profit_t-4)",
        "source": "基本面因子",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.GROWTH,
        "direction": FactorDirection.POSITIVE,
        "tags": ["盈利增长", "成长", "基本面"]
    },
    {
        "name": "Market_Cap_Small",
        "description": "小市值因子。偏好市值较小的股票，小盘股效应。",
        "formula": "-log(market_cap)",
        "source": "规模因子",
        "category": FactorCategory.SIZE,
        "sub_category": FactorSubCategory.MARKET_CAP,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["市值", "小盘股"]
    },
    {
        "name": "Turnover_Rate",
        "description": "换手率因子。衡量股票交易活跃度。",
        "formula": "volume / float_shares",
        "source": "流动性因子",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["流动性", "换手率"]
    },
    {
        "name": "Price_Momentum",
        "description": "价格动量因子。20日价格变化率。",
        "formula": "(close - close.shift(20)) / close.shift(20)",
        "source": "动量因子",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.TIME_SERIES_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "tags": ["动量", "价格"]
    },
    {
        "name": "Dividend_Yield",
        "description": "股息率因子。衡量股票分红收益率。",
        "formula": "annual_dividend / close",
        "source": "价值因子",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.RELATIVE_VALUE,
        "direction": FactorDirection.POSITIVE,
        "tags": ["红利", "价值投资"]
    },
    {
        "name": "Volatility_Low",
        "description": "低波动率因子。偏好历史波动率较低的股票。",
        "formula": "-std(close.pct_change(), 20)",
        "source": "波动率因子",
        "category": FactorCategory.VOLATILITY,
        "sub_category": FactorSubCategory.HISTORICAL_VOLATILITY,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["波动率", "低波动"]
    },
    {
        "name": "Beta_Low",
        "description": "低Beta因子。偏好系统性风险较低的股票。",
        "formula": "-beta(stock_return, index_return, 60)",
        "source": "风险因子",
        "category": FactorCategory.VOLATILITY,
        "sub_category": FactorSubCategory.HISTORICAL_VOLATILITY,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["Beta", "风险"]
    },
    {
        "name": "Industry_Momentum",
        "description": "行业动量因子。基于行业相对强弱进行选股。",
        "formula": "industry_return_rank",
        "source": "行业因子",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.CROSS_SECTIONAL_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "tags": ["行业", "动量"]
    },
    {
        "name": "Fund_Flow",
        "description": "资金流向因子。追踪主力资金流入流出。",
        "formula": "large_buy_amount - large_sell_amount",
        "source": "资金流因子",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.MARKET_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "tags": ["资金流", "主力资金"]
    },
    {
        "name": "Relative_Strength",
        "description": "相对强弱因子。股票相对于基准的表现。",
        "formula": "stock_return - benchmark_return",
        "source": "技术因子",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["相对强弱", "技术分析"]
    },
    {
        "name": "Northbound_Buy",
        "description": "北向资金买入因子。追踪外资买入动向。",
        "formula": "northbound_buy_amount",
        "source": "资金流因子",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.MARKET_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "tags": ["北向资金", "外资"]
    },
    {
        "name": "Northbound_Holding",
        "description": "北向资金持仓因子。追踪外资持仓变化。",
        "formula": "northbound_holding_change",
        "source": "资金流因子",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.MARKET_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "tags": ["北向资金", "外资"]
    },
    {
        "name": "Price_Strength",
        "description": "价格强度因子。衡量股价相对位置。",
        "formula": "(close - low_20d) / (high_20d - low_20d)",
        "source": "技术因子",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["价格强度", "技术分析"]
    },
    {
        "name": "ROE_High",
        "description": "高ROE因子。偏好净资产收益率高的公司。",
        "formula": "ROE",
        "source": "质量因子",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.PROFITABILITY,
        "direction": FactorDirection.POSITIVE,
        "tags": ["ROE", "盈利能力"]
    },
    {
        "name": "Cash_Flow_Positive",
        "description": "正向现金流因子。偏好经营现金流为正的公司。",
        "formula": "operating_cash_flow",
        "source": "质量因子",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.FINANCIAL_HEALTH,
        "direction": FactorDirection.POSITIVE,
        "tags": ["现金流", "财务健康"]
    },
    {
        "name": "Debt_Ratio_Low",
        "description": "低负债率因子。偏好资产负债率低的公司。",
        "formula": "-debt_ratio",
        "source": "质量因子",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.FINANCIAL_HEALTH,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["负债率", "财务健康"]
    },
    {
        "name": "Gross_Margin_High",
        "description": "高毛利率因子。偏好毛利率高的公司。",
        "formula": "gross_margin",
        "source": "质量因子",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.PROFITABILITY,
        "direction": FactorDirection.POSITIVE,
        "tags": ["毛利率", "盈利能力"]
    },
    {
        "name": "Breakout_MA",
        "description": "均线突破因子。股价突破关键均线。",
        "formula": "close / MA(close, 60) - 1",
        "source": "技术因子",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["突破", "均线"]
    },
    {
        "name": "Breakout_High",
        "description": "突破前高因子。股价突破20日高点。",
        "formula": "close / high_20d - 1",
        "source": "技术因子",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["突破", "新高"]
    },
    {
        "name": "Volume_Surge",
        "description": "成交量激增因子。成交量异常放大。",
        "formula": "volume / MA(volume, 20) - 1",
        "source": "量价因子",
        "category": FactorCategory.LIQUIDITY,
        "sub_category": FactorSubCategory.VOLUME_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["成交量", "放量"]
    },
    {
        "name": "MACD_Cross",
        "description": "MACD金叉因子。MACD线上穿信号线。",
        "formula": "MACD(12,26,9) - Signal(12,26,9)",
        "source": "技术因子",
        "category": FactorCategory.TECHNICAL,
        "sub_category": FactorSubCategory.TREND_FACTOR,
        "direction": FactorDirection.POSITIVE,
        "tags": ["MACD", "技术指标"]
    },
    {
        "name": "Earnings_Surprise",
        "description": "业绩超预期因子。实际业绩超出分析师预期。",
        "formula": "(actual_eps - expected_eps) / abs(expected_eps)",
        "source": "事件因子",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.ANALYST_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "tags": ["业绩", "超预期"]
    },
    {
        "name": "Buyback_Announce",
        "description": "回购公告因子。公司发布股票回购计划。",
        "formula": "buyback_announcement",
        "source": "事件因子",
        "category": FactorCategory.ALTERNATIVE,
        "sub_category": FactorSubCategory.INSIDER_TRADING,
        "direction": FactorDirection.POSITIVE,
        "tags": ["回购", "事件"]
    },
    {
        "name": "Insider_Buy",
        "description": "高管增持因子。公司高管买入自家股票。",
        "formula": "insider_buy_amount",
        "source": "事件因子",
        "category": FactorCategory.ALTERNATIVE,
        "sub_category": FactorSubCategory.INSIDER_TRADING,
        "direction": FactorDirection.POSITIVE,
        "tags": ["高管增持", "事件"]
    },
    {
        "name": "Analyst_Upgrade",
        "description": "分析师上调评级因子。分析师上调股票评级。",
        "formula": "rating_change",
        "source": "情绪因子",
        "category": FactorCategory.SENTIMENT,
        "sub_category": FactorSubCategory.ANALYST_SENTIMENT,
        "direction": FactorDirection.POSITIVE,
        "tags": ["分析师", "评级"]
    },
    {
        "name": "PS_Low",
        "description": "低市销率因子。偏好PS较低的公司。",
        "formula": "-market_cap / revenue",
        "source": "估值因子",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["估值", "市销率"]
    },
    {
        "name": "Value_Score",
        "description": "综合价值得分因子。综合PE、PB、PS等估值指标。",
        "formula": "rank(PE) + rank(PB) + rank(PS)",
        "source": "综合因子",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["估值", "综合"]
    },
    {
        "name": "Value_Factor",
        "description": "价值因子。综合估值指标选股。",
        "formula": "composite_value_score",
        "source": "多因子模型",
        "category": FactorCategory.VALUE,
        "sub_category": FactorSubCategory.VALUATION,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["价值", "多因子"]
    },
    {
        "name": "Quality_Factor",
        "description": "质量因子。综合盈利能力、财务健康等指标。",
        "formula": "composite_quality_score",
        "source": "多因子模型",
        "category": FactorCategory.QUALITY,
        "sub_category": FactorSubCategory.PROFITABILITY,
        "direction": FactorDirection.POSITIVE,
        "tags": ["质量", "多因子"]
    },
    {
        "name": "Momentum_Factor",
        "description": "动量因子。综合价格动量指标。",
        "formula": "composite_momentum_score",
        "source": "多因子模型",
        "category": FactorCategory.MOMENTUM,
        "sub_category": FactorSubCategory.TIME_SERIES_MOMENTUM,
        "direction": FactorDirection.POSITIVE,
        "tags": ["动量", "多因子"]
    },
    {
        "name": "Size_Factor",
        "description": "规模因子。基于市值大小选股。",
        "formula": "log(market_cap)",
        "source": "多因子模型",
        "category": FactorCategory.SIZE,
        "sub_category": FactorSubCategory.MARKET_CAP,
        "direction": FactorDirection.NEGATIVE,
        "tags": ["规模", "多因子"]
    },
]


SIGNALS_TO_REGISTER = [
    {
        "name": "ma_cross_5_20",
        "description": "5日/20日均线金叉买入信号。短期均线上穿长期均线时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["MA_5_20_Cross"],
            weights=[1.0],
            threshold=0.0,
            conditions=["MA_5 > MA_20", "MA_5_prev <= MA_20_prev"],
            combination_method="threshold"
        ),
        "source": "经典技术信号",
        "tags": ["均线", "金叉", "趋势"]
    },
    {
        "name": "ma_cross_10_60",
        "description": "10日/60日均线金叉买入信号。中期趋势确认信号。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["MA_10_60_Cross"],
            weights=[1.0],
            threshold=0.0,
            conditions=["MA_10 > MA_60", "MA_10_prev <= MA_60_prev"],
            combination_method="threshold"
        ),
        "source": "经典技术信号",
        "tags": ["均线", "金叉", "趋势"]
    },
    {
        "name": "momentum_3m",
        "description": "3个月动量信号。中期价格趋势向上时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Momentum_3M"],
            weights=[1.0],
            threshold=0.05,
            conditions=["Momentum_3M > 0.05"],
            combination_method="threshold"
        ),
        "source": "动量信号",
        "tags": ["动量", "趋势"]
    },
    {
        "name": "reversal_1m",
        "description": "1个月反转信号。短期超跌反弹机会。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Reversal_1M"],
            weights=[1.0],
            threshold=-0.15,
            conditions=["Reversal_1M < -0.15"],
            combination_method="threshold"
        ),
        "source": "反转信号",
        "tags": ["反转", "反弹"]
    },
    {
        "name": "volume_breakout",
        "description": "成交量突破信号。放量突破时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Volume_Breakout"],
            weights=[1.0],
            threshold=1.5,
            conditions=["Volume_Breakout > 1.5"],
            combination_method="threshold"
        ),
        "source": "量价信号",
        "tags": ["成交量", "突破"]
    },
    {
        "name": "pe_ratio",
        "description": "低PE估值信号。PE低于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["PE_Ratio"],
            weights=[1.0],
            threshold=30.0,
            conditions=["PE_Ratio > 0", "PE_Ratio < 30"],
            combination_method="threshold"
        ),
        "source": "价值信号",
        "tags": ["估值", "PE"]
    },
    {
        "name": "pb_ratio",
        "description": "低PB估值信号。PB低于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["PB_Ratio"],
            weights=[1.0],
            threshold=3.0,
            conditions=["PB_Ratio > 0", "PB_Ratio < 3"],
            combination_method="threshold"
        ),
        "source": "价值信号",
        "tags": ["估值", "PB"]
    },
    {
        "name": "roe_growth",
        "description": "ROE增长信号。ROE持续改善时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["ROE_Growth"],
            weights=[1.0],
            threshold=0.1,
            conditions=["ROE_Growth > 0.1"],
            combination_method="threshold"
        ),
        "source": "质量信号",
        "tags": ["ROE", "成长"]
    },
    {
        "name": "earnings_growth",
        "description": "盈利增长信号。净利润持续增长时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Earnings_Growth"],
            weights=[1.0],
            threshold=0.15,
            conditions=["Earnings_Growth > 0.15"],
            combination_method="threshold"
        ),
        "source": "成长信号",
        "tags": ["盈利", "成长"]
    },
    {
        "name": "market_cap_small",
        "description": "小市值信号。偏好小盘股。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Market_Cap_Small"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Market_Cap < 100亿"],
            combination_method="rank"
        ),
        "source": "规模信号",
        "tags": ["市值", "小盘股"]
    },
    {
        "name": "turnover_rate",
        "description": "高换手率信号。交易活跃度高时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Turnover_Rate"],
            weights=[1.0],
            threshold=0.02,
            conditions=["Turnover_Rate > 0.02"],
            combination_method="threshold"
        ),
        "source": "流动性信号",
        "tags": ["换手率", "流动性"]
    },
    {
        "name": "price_momentum",
        "description": "价格动量信号。短期价格上涨趋势。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Price_Momentum"],
            weights=[1.0],
            threshold=0.05,
            conditions=["Price_Momentum > 0.05"],
            combination_method="threshold"
        ),
        "source": "动量信号",
        "tags": ["动量", "价格"]
    },
    {
        "name": "dividend_yield",
        "description": "高股息信号。股息率高于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Dividend_Yield"],
            weights=[1.0],
            threshold=0.03,
            conditions=["Dividend_Yield > 0.03"],
            combination_method="threshold"
        ),
        "source": "红利信号",
        "tags": ["红利", "收益"]
    },
    {
        "name": "volatility_low",
        "description": "低波动信号。波动率低于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Volatility_Low"],
            weights=[1.0],
            threshold=0.25,
            conditions=["Volatility < 0.25"],
            combination_method="threshold"
        ),
        "source": "波动率信号",
        "tags": ["波动率", "低波动"]
    },
    {
        "name": "beta_low",
        "description": "低Beta信号。系统性风险较低时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Beta_Low"],
            weights=[1.0],
            threshold=0.8,
            conditions=["Beta < 0.8"],
            combination_method="threshold"
        ),
        "source": "风险信号",
        "tags": ["Beta", "风险"]
    },
    {
        "name": "industry_momentum",
        "description": "行业动量信号。行业相对强势时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Industry_Momentum"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Industry_Rank > 0.7"],
            combination_method="rank"
        ),
        "source": "行业信号",
        "tags": ["行业", "动量"]
    },
    {
        "name": "fund_flow",
        "description": "资金流入信号。主力资金净流入时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Fund_Flow"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Fund_Flow > 0"],
            combination_method="threshold"
        ),
        "source": "资金流信号",
        "tags": ["资金流", "主力"]
    },
    {
        "name": "relative_strength",
        "description": "相对强弱信号。跑赢基准时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Relative_Strength"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Relative_Strength > 0"],
            combination_method="threshold"
        ),
        "source": "技术信号",
        "tags": ["相对强弱", "技术"]
    },
    {
        "name": "northbound_buy",
        "description": "北向资金买入信号。外资买入时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Northbound_Buy"],
            weights=[1.0],
            threshold=50000000,
            conditions=["Northbound_Buy > 50000000"],
            combination_method="threshold"
        ),
        "source": "资金流信号",
        "tags": ["北向资金", "外资"]
    },
    {
        "name": "northbound_holding",
        "description": "北向资金持仓信号。外资持仓增加时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Northbound_Holding"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Northbound_Holding_Change > 0"],
            combination_method="threshold"
        ),
        "source": "资金流信号",
        "tags": ["北向资金", "外资"]
    },
    {
        "name": "price_strength",
        "description": "价格强度信号。股价处于相对高位时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Price_Strength"],
            weights=[1.0],
            threshold=0.7,
            conditions=["Price_Strength > 0.7"],
            combination_method="threshold"
        ),
        "source": "技术信号",
        "tags": ["价格强度", "技术"]
    },
    {
        "name": "roe_high",
        "description": "高ROE信号。ROE高于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["ROE_High"],
            weights=[1.0],
            threshold=0.12,
            conditions=["ROE > 0.12"],
            combination_method="threshold"
        ),
        "source": "质量信号",
        "tags": ["ROE", "盈利"]
    },
    {
        "name": "cash_flow_positive",
        "description": "正向现金流信号。经营现金流为正时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Cash_Flow_Positive"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Operating_Cash_Flow > 0"],
            combination_method="threshold"
        ),
        "source": "质量信号",
        "tags": ["现金流", "财务"]
    },
    {
        "name": "debt_ratio_low",
        "description": "低负债信号。资产负债率低于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Debt_Ratio_Low"],
            weights=[1.0],
            threshold=0.6,
            conditions=["Debt_Ratio < 0.6"],
            combination_method="threshold"
        ),
        "source": "质量信号",
        "tags": ["负债率", "财务"]
    },
    {
        "name": "gross_margin_high",
        "description": "高毛利率信号。毛利率高于阈值时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Gross_Margin_High"],
            weights=[1.0],
            threshold=0.2,
            conditions=["Gross_Margin > 0.2"],
            combination_method="threshold"
        ),
        "source": "质量信号",
        "tags": ["毛利率", "盈利"]
    },
    {
        "name": "breakout_ma",
        "description": "均线突破信号。股价突破60日均线时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Breakout_MA"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Close > MA_60", "Close_prev <= MA_60_prev"],
            combination_method="threshold"
        ),
        "source": "技术信号",
        "tags": ["突破", "均线"]
    },
    {
        "name": "breakout_high",
        "description": "突破前高信号。股价突破20日高点时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Breakout_High"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Close > High_20d_prev"],
            combination_method="threshold"
        ),
        "source": "技术信号",
        "tags": ["突破", "新高"]
    },
    {
        "name": "volume_surge",
        "description": "成交量激增信号。成交量异常放大时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Volume_Surge"],
            weights=[1.0],
            threshold=1.0,
            conditions=["Volume_Surge > 1.0"],
            combination_method="threshold"
        ),
        "source": "量价信号",
        "tags": ["成交量", "放量"]
    },
    {
        "name": "macd_cross",
        "description": "MACD金叉信号。MACD线上穿信号线时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["MACD_Cross"],
            weights=[1.0],
            threshold=0.0,
            conditions=["MACD > Signal", "MACD_prev <= Signal_prev"],
            combination_method="threshold"
        ),
        "source": "技术信号",
        "tags": ["MACD", "金叉"]
    },
    {
        "name": "earnings_surprise",
        "description": "业绩超预期信号。实际业绩超出预期时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Earnings_Surprise"],
            weights=[1.0],
            threshold=0.1,
            conditions=["Earnings_Surprise > 0.1"],
            combination_method="threshold"
        ),
        "source": "事件信号",
        "tags": ["业绩", "超预期"]
    },
    {
        "name": "buyback_announce",
        "description": "回购公告信号。公司发布回购计划时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Buyback_Announce"],
            weights=[1.0],
            threshold=1.0,
            conditions=["Buyback_Announced == True"],
            combination_method="threshold"
        ),
        "source": "事件信号",
        "tags": ["回购", "事件"]
    },
    {
        "name": "insider_buy",
        "description": "高管增持信号。高管买入自家股票时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Insider_Buy"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Insider_Buy > 0"],
            combination_method="threshold"
        ),
        "source": "事件信号",
        "tags": ["高管增持", "事件"]
    },
    {
        "name": "analyst_upgrade",
        "description": "分析师上调信号。分析师上调评级时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Analyst_Upgrade"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Rating_Change > 0"],
            combination_method="threshold"
        ),
        "source": "情绪信号",
        "tags": ["分析师", "评级"]
    },
    {
        "name": "pe_low",
        "description": "低PE信号。PE处于历史低位时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["PE_Ratio"],
            weights=[1.0],
            threshold=20.0,
            conditions=["PE_Percentile < 20"],
            combination_method="rank"
        ),
        "source": "价值信号",
        "tags": ["估值", "PE"]
    },
    {
        "name": "pb_low",
        "description": "低PB信号。PB处于历史低位时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["PB_Ratio"],
            weights=[1.0],
            threshold=20.0,
            conditions=["PB_Percentile < 20"],
            combination_method="rank"
        ),
        "source": "价值信号",
        "tags": ["估值", "PB"]
    },
    {
        "name": "ps_low",
        "description": "低PS信号。PS处于历史低位时触发。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["PS_Low"],
            weights=[1.0],
            threshold=20.0,
            conditions=["PS_Percentile < 20"],
            combination_method="rank"
        ),
        "source": "价值信号",
        "tags": ["估值", "PS"]
    },
    {
        "name": "value_score",
        "description": "综合价值信号。综合估值指标选股。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Value_Score"],
            weights=[1.0],
            threshold=0.3,
            conditions=["Value_Score_Rank < 0.3"],
            combination_method="rank"
        ),
        "source": "价值信号",
        "tags": ["估值", "综合"]
    },
    {
        "name": "value_factor",
        "description": "价值因子信号。多因子价值选股。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Value_Factor"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Value_Factor_Score > 0"],
            combination_method="weighted_sum"
        ),
        "source": "多因子信号",
        "tags": ["价值", "多因子"]
    },
    {
        "name": "quality_factor",
        "description": "质量因子信号。多因子质量选股。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Quality_Factor"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Quality_Factor_Score > 0"],
            combination_method="weighted_sum"
        ),
        "source": "多因子信号",
        "tags": ["质量", "多因子"]
    },
    {
        "name": "momentum_factor",
        "description": "动量因子信号。多因子动量选股。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Momentum_Factor"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Momentum_Factor_Score > 0"],
            combination_method="weighted_sum"
        ),
        "source": "多因子信号",
        "tags": ["动量", "多因子"]
    },
    {
        "name": "size_factor",
        "description": "规模因子信号。多因子规模选股。",
        "signal_type": SignalType.STOCK_SELECTION,
        "direction": SignalDirection.BUY,
        "rules": SignalRules(
            factors=["Size_Factor"],
            weights=[1.0],
            threshold=0.0,
            conditions=["Size_Factor_Score > 0"],
            combination_method="weighted_sum"
        ),
        "source": "多因子信号",
        "tags": ["规模", "多因子"]
    },
]


def init_factors():
    """初始化因子注册表"""
    print("=" * 60)
    print("初始化因子注册表")
    print("=" * 60)
    
    reset_factor_registry()
    registry = get_factor_registry()
    
    registered = 0
    skipped = 0
    
    for factor_config in FACTORS_TO_REGISTER:
        existing = registry.get_by_name(factor_config["name"])
        if existing:
            skipped += 1
            continue
        
        factor = registry.register(
            name=factor_config["name"],
            description=factor_config["description"],
            formula=factor_config["formula"],
            source=factor_config["source"],
            category=factor_config["category"],
            sub_category=factor_config["sub_category"],
            direction=factor_config["direction"],
            tags=factor_config["tags"]
        )
        registered += 1
        print(f"  ✓ 注册因子: {factor.name} ({factor.id})")
    
    print()
    print(f"因子注册完成: 新注册 {registered} 个, 跳过 {skipped} 个")
    print(f"当前因子总数: {registry.get_factor_count()}")
    
    return registry


def init_signals():
    """初始化信号注册表"""
    print()
    print("=" * 60)
    print("初始化信号注册表")
    print("=" * 60)
    
    reset_signal_registry()
    registry = get_signal_registry()
    
    registered = 0
    skipped = 0
    
    for signal_config in SIGNALS_TO_REGISTER:
        existing = registry.get_by_name(signal_config["name"])
        if existing:
            skipped += 1
            continue
        
        signal = registry.register(
            name=signal_config["name"],
            description=signal_config["description"],
            signal_type=signal_config["signal_type"],
            direction=signal_config["direction"],
            rules=signal_config["rules"],
            source=signal_config["source"],
            tags=signal_config["tags"]
        )
        registered += 1
        print(f"  ✓ 注册信号: {signal.name} ({signal.id})")
    
    print()
    print(f"信号注册完成: 新注册 {registered} 个, 跳过 {skipped} 个")
    print(f"当前信号总数: {registry.get_signal_count()}")
    
    return registry


def main():
    """主函数"""
    print()
    print("*" * 60)
    print("  WildQuest Matrix - 因子和信号初始化")
    print("*" * 60)
    print()
    
    factor_registry = init_factors()
    signal_registry = init_signals()
    
    print()
    print("=" * 60)
    print("初始化完成")
    print("=" * 60)
    print(f"因子总数: {factor_registry.get_factor_count()}")
    print(f"信号总数: {signal_registry.get_signal_count()}")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
