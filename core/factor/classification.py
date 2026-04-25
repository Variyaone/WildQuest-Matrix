"""
因子分类体系模块

定义因子的分类结构，按类别组织因子便于管理和使用。
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


class FactorCategory(Enum):
    """因子一级分类"""
    MOMENTUM = "动量类"
    VALUE = "价值类"
    QUALITY = "质量类"
    VOLATILITY = "波动率类"
    LIQUIDITY = "流动性类"
    SIZE = "规模类"
    SENTIMENT = "情绪类"
    TECHNICAL = "技术类"
    ALTERNATIVE = "另类数据类"


class FactorSubCategory(Enum):
    """因子二级分类"""
    TIME_SERIES_MOMENTUM = "时间序列动量"
    CROSS_SECTIONAL_MOMENTUM = "横截面动量"
    TECHNICAL_PATTERN_MOMENTUM = "技术形态动量"
    
    VALUATION = "估值因子"
    RELATIVE_VALUE = "相对价值"
    
    PROFITABILITY = "盈利能力"
    GROWTH = "成长能力"
    OPERATING_EFFICIENCY = "运营效率"
    FINANCIAL_HEALTH = "财务健康"
    
    HISTORICAL_VOLATILITY = "历史波动率"
    IDIOSYNCRATIC_VOLATILITY = "特质波动率"
    VOLATILITY_CHANGE = "波动率变化"
    
    VOLUME_FACTOR = "成交量因子"
    LIQUIDITY_INDICATOR = "流动性指标"
    LIQUIDITY_RISK = "流动性风险"
    
    MARKET_CAP = "市值因子"
    SIZE_CHANGE = "规模变化"
    
    ANALYST_SENTIMENT = "分析师情绪"
    MARKET_SENTIMENT = "市场情绪"
    NEWS_SENTIMENT = "舆情因子"
    
    TREND_FACTOR = "趋势因子"
    REVERSAL_FACTOR = "反转因子"
    PATTERN_FACTOR = "形态因子"
    
    SUPPLY_CHAIN = "供应链因子"
    INSIDER_TRADING = "高管增减持"
    INSTITUTIONAL_HOLDING = "机构持仓变化"


@dataclass
class FactorTypeInfo:
    """因子类型信息"""
    category: FactorCategory
    sub_category: FactorSubCategory
    description: str
    typical_factors: List[str] = field(default_factory=list)


FACTOR_CLASSIFICATION: Dict[FactorCategory, Dict[FactorSubCategory, FactorTypeInfo]] = {
    FactorCategory.MOMENTUM: {
        FactorSubCategory.TIME_SERIES_MOMENTUM: FactorTypeInfo(
            category=FactorCategory.MOMENTUM,
            sub_category=FactorSubCategory.TIME_SERIES_MOMENTUM,
            description="基于历史价格时间序列的动量因子",
            typical_factors=["过去20日收益率", "过去60日收益率", "过去120日收益率"]
        ),
        FactorSubCategory.CROSS_SECTIONAL_MOMENTUM: FactorTypeInfo(
            category=FactorCategory.MOMENTUM,
            sub_category=FactorSubCategory.CROSS_SECTIONAL_MOMENTUM,
            description="基于横截面比较的动量因子",
            typical_factors=["相对强弱指标", "行业动量"]
        ),
        FactorSubCategory.TECHNICAL_PATTERN_MOMENTUM: FactorTypeInfo(
            category=FactorCategory.MOMENTUM,
            sub_category=FactorSubCategory.TECHNICAL_PATTERN_MOMENTUM,
            description="基于技术指标的动量因子",
            typical_factors=["MACD信号", "RSI指标"]
        ),
    },
    FactorCategory.VALUE: {
        FactorSubCategory.VALUATION: FactorTypeInfo(
            category=FactorCategory.VALUE,
            sub_category=FactorSubCategory.VALUATION,
            description="基于估值指标的因子",
            typical_factors=["市盈率PE", "市净率PB", "市销率PS", "EV/EBITDA"]
        ),
        FactorSubCategory.RELATIVE_VALUE: FactorTypeInfo(
            category=FactorCategory.VALUE,
            sub_category=FactorSubCategory.RELATIVE_VALUE,
            description="基于相对估值比较的因子",
            typical_factors=["PEG比率", "股息率"]
        ),
    },
    FactorCategory.QUALITY: {
        FactorSubCategory.PROFITABILITY: FactorTypeInfo(
            category=FactorCategory.QUALITY,
            sub_category=FactorSubCategory.PROFITABILITY,
            description="反映公司盈利能力的因子",
            typical_factors=["ROE", "ROA", "净利率"]
        ),
        FactorSubCategory.GROWTH: FactorTypeInfo(
            category=FactorCategory.QUALITY,
            sub_category=FactorSubCategory.GROWTH,
            description="反映公司成长能力的因子",
            typical_factors=["营收增长率", "净利润增长率"]
        ),
        FactorSubCategory.OPERATING_EFFICIENCY: FactorTypeInfo(
            category=FactorCategory.QUALITY,
            sub_category=FactorSubCategory.OPERATING_EFFICIENCY,
            description="反映公司运营效率的因子",
            typical_factors=["资产周转率", "存货周转率"]
        ),
        FactorSubCategory.FINANCIAL_HEALTH: FactorTypeInfo(
            category=FactorCategory.QUALITY,
            sub_category=FactorSubCategory.FINANCIAL_HEALTH,
            description="反映公司财务健康状况的因子",
            typical_factors=["资产负债率", "流动比率", "现金流质量"]
        ),
    },
    FactorCategory.VOLATILITY: {
        FactorSubCategory.HISTORICAL_VOLATILITY: FactorTypeInfo(
            category=FactorCategory.VOLATILITY,
            sub_category=FactorSubCategory.HISTORICAL_VOLATILITY,
            description="基于历史波动率的因子",
            typical_factors=["20日波动率", "60日波动率"]
        ),
        FactorSubCategory.IDIOSYNCRATIC_VOLATILITY: FactorTypeInfo(
            category=FactorCategory.VOLATILITY,
            sub_category=FactorSubCategory.IDIOSYNCRATIC_VOLATILITY,
            description="基于特质波动率的因子",
            typical_factors=["残差波动率"]
        ),
        FactorSubCategory.VOLATILITY_CHANGE: FactorTypeInfo(
            category=FactorCategory.VOLATILITY,
            sub_category=FactorSubCategory.VOLATILITY_CHANGE,
            description="基于波动率变化的因子",
            typical_factors=["波动率变化率", "波动率偏度"]
        ),
    },
    FactorCategory.LIQUIDITY: {
        FactorSubCategory.VOLUME_FACTOR: FactorTypeInfo(
            category=FactorCategory.LIQUIDITY,
            sub_category=FactorSubCategory.VOLUME_FACTOR,
            description="基于成交量的因子",
            typical_factors=["换手率", "成交额", "量价相关性"]
        ),
        FactorSubCategory.LIQUIDITY_INDICATOR: FactorTypeInfo(
            category=FactorCategory.LIQUIDITY,
            sub_category=FactorSubCategory.LIQUIDITY_INDICATOR,
            description="基于流动性指标的因子",
            typical_factors=["Amihud非流动性", "买卖价差"]
        ),
        FactorSubCategory.LIQUIDITY_RISK: FactorTypeInfo(
            category=FactorCategory.LIQUIDITY,
            sub_category=FactorSubCategory.LIQUIDITY_RISK,
            description="基于流动性风险的因子",
            typical_factors=["流动性冲击成本"]
        ),
    },
    FactorCategory.SIZE: {
        FactorSubCategory.MARKET_CAP: FactorTypeInfo(
            category=FactorCategory.SIZE,
            sub_category=FactorSubCategory.MARKET_CAP,
            description="基于市值的因子",
            typical_factors=["总市值", "流通市值"]
        ),
        FactorSubCategory.SIZE_CHANGE: FactorTypeInfo(
            category=FactorCategory.SIZE,
            sub_category=FactorSubCategory.SIZE_CHANGE,
            description="基于规模变化的因子",
            typical_factors=["市值增长率"]
        ),
    },
    FactorCategory.SENTIMENT: {
        FactorSubCategory.ANALYST_SENTIMENT: FactorTypeInfo(
            category=FactorCategory.SENTIMENT,
            sub_category=FactorSubCategory.ANALYST_SENTIMENT,
            description="基于分析师情绪的因子",
            typical_factors=["分析师评级", "盈利预测调整"]
        ),
        FactorSubCategory.MARKET_SENTIMENT: FactorTypeInfo(
            category=FactorCategory.SENTIMENT,
            sub_category=FactorSubCategory.MARKET_SENTIMENT,
            description="基于市场情绪的因子",
            typical_factors=["融资融券余额", "北向资金流向"]
        ),
        FactorSubCategory.NEWS_SENTIMENT: FactorTypeInfo(
            category=FactorCategory.SENTIMENT,
            sub_category=FactorSubCategory.NEWS_SENTIMENT,
            description="基于舆情分析的因子",
            typical_factors=["新闻情感得分"]
        ),
    },
    FactorCategory.TECHNICAL: {
        FactorSubCategory.TREND_FACTOR: FactorTypeInfo(
            category=FactorCategory.TECHNICAL,
            sub_category=FactorSubCategory.TREND_FACTOR,
            description="基于趋势的技术因子",
            typical_factors=["均线偏离", "布林带位置"]
        ),
        FactorSubCategory.REVERSAL_FACTOR: FactorTypeInfo(
            category=FactorCategory.TECHNICAL,
            sub_category=FactorSubCategory.REVERSAL_FACTOR,
            description="基于反转的技术因子",
            typical_factors=["短期反转", "长期反转"]
        ),
        FactorSubCategory.PATTERN_FACTOR: FactorTypeInfo(
            category=FactorCategory.TECHNICAL,
            sub_category=FactorSubCategory.PATTERN_FACTOR,
            description="基于形态的技术因子",
            typical_factors=["K线形态", "缺口因子"]
        ),
    },
    FactorCategory.ALTERNATIVE: {
        FactorSubCategory.SUPPLY_CHAIN: FactorTypeInfo(
            category=FactorCategory.ALTERNATIVE,
            sub_category=FactorSubCategory.SUPPLY_CHAIN,
            description="基于供应链数据的因子",
            typical_factors=["供应链因子"]
        ),
        FactorSubCategory.INSIDER_TRADING: FactorTypeInfo(
            category=FactorCategory.ALTERNATIVE,
            sub_category=FactorSubCategory.INSIDER_TRADING,
            description="基于高管交易的因子",
            typical_factors=["高管增减持"]
        ),
        FactorSubCategory.INSTITUTIONAL_HOLDING: FactorTypeInfo(
            category=FactorCategory.ALTERNATIVE,
            sub_category=FactorSubCategory.INSTITUTIONAL_HOLDING,
            description="基于机构持仓的因子",
            typical_factors=["机构持仓变化"]
        ),
    },
}


class FactorClassification:
    """
    因子分类管理器
    
    管理因子的分类体系，支持按类别查询和组织因子。
    """
    
    def __init__(self):
        """初始化因子分类管理器"""
        self._classification = FACTOR_CLASSIFICATION
    
    def get_all_categories(self) -> List[FactorCategory]:
        """获取所有一级分类"""
        return list(self._classification.keys())
    
    def get_sub_categories(self, category: FactorCategory) -> List[FactorSubCategory]:
        """获取指定一级分类下的所有二级分类"""
        if category not in self._classification:
            return []
        return list(self._classification[category].keys())
    
    def get_factor_type_info(
        self, 
        category: FactorCategory, 
        sub_category: FactorSubCategory
    ) -> Optional[FactorTypeInfo]:
        """获取因子类型信息"""
        if category not in self._classification:
            return None
        if sub_category not in self._classification[category]:
            return None
        return self._classification[category][sub_category]
    
    def get_category_description(self, category: FactorCategory) -> str:
        """获取一级分类描述"""
        descriptions = {
            FactorCategory.MOMENTUM: "动量类因子：基于价格动量和趋势的因子",
            FactorCategory.VALUE: "价值类因子：基于估值指标的因子",
            FactorCategory.QUALITY: "质量类因子：反映公司基本面质量的因子",
            FactorCategory.VOLATILITY: "波动率类因子：基于价格波动特征的因子",
            FactorCategory.LIQUIDITY: "流动性类因子：基于交易活跃度的因子",
            FactorCategory.SIZE: "规模类因子：基于公司规模的因子",
            FactorCategory.SENTIMENT: "情绪类因子：反映市场情绪的因子",
            FactorCategory.TECHNICAL: "技术类因子：基于技术分析的因子",
            FactorCategory.ALTERNATIVE: "另类数据类因子：基于非传统数据的因子",
        }
        return descriptions.get(category, "")
    
    def classify_factor(
        self, 
        category: FactorCategory, 
        sub_category: FactorSubCategory
    ) -> Dict[str, Any]:
        """
        分类因子
        
        Args:
            category: 一级分类
            sub_category: 二级分类
            
        Returns:
            分类信息字典
        """
        info = self.get_factor_type_info(category, sub_category)
        if info is None:
            return {}
        
        return {
            "category": category.value,
            "category_code": category.name,
            "sub_category": sub_category.value,
            "sub_category_code": sub_category.name,
            "description": info.description,
            "typical_factors": info.typical_factors,
        }
    
    def find_category_by_name(self, name: str) -> Optional[FactorCategory]:
        """根据名称查找一级分类"""
        for category in FactorCategory:
            if category.value == name or category.name == name:
                return category
        return None
    
    def find_sub_category_by_name(self, name: str) -> Optional[FactorSubCategory]:
        """根据名称查找二级分类"""
        for sub_cat in FactorSubCategory:
            if sub_cat.value == name or sub_cat.name == name:
                return sub_cat
        return None
    
    def get_classification_tree(self) -> Dict[str, Any]:
        """获取完整的分类树结构"""
        tree = {}
        for category, sub_cats in self._classification.items():
            tree[category.value] = {
                "code": category.name,
                "sub_categories": {}
            }
            for sub_cat, info in sub_cats.items():
                tree[category.value]["sub_categories"][sub_cat.value] = {
                    "code": sub_cat.name,
                    "description": info.description,
                    "typical_factors": info.typical_factors
                }
        return tree


_default_classification: Optional[FactorClassification] = None


def get_factor_classification() -> FactorClassification:
    """获取全局因子分类管理器实例"""
    global _default_classification
    if _default_classification is None:
        _default_classification = FactorClassification()
    return _default_classification


def reset_factor_classification():
    """重置全局因子分类管理器"""
    global _default_classification
    _default_classification = None
