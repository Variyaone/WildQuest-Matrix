"""
数据契约定义模块

定义各层的数据输入输出契约，确保数据格式统一。
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
import pandas as pd


class RequirementType(Enum):
    """要求类型"""
    HARD = "hard"      # 硬性要求 - 必须满足，否则一票否决
    ELASTIC = "elastic"  # 弹性要求 - 有条件可适当让步
    MARGINAL = "marginal"  # 边际要求 - 锦上添花，没有不影响


class TrustLevel(Enum):
    """结果可信度等级"""
    TRUSTED = "trusted"      # 可信 - 所有硬性要求通过
    PARTIAL = "partial"      # 部分可信 - 弹性要求有偏差
    UNTRUSTED = "untrusted"  # 不可信 - 硬性要求失败


@dataclass
class Requirement:
    """检查要求定义"""
    id: str                          # 要求编号 (如 H1, E1, M1)
    name: str                        # 要求名称
    description: str                 # 要求描述
    req_type: RequirementType        # 要求类型
    check_func: Callable             # 检查函数
    ideal_standard: Any              # 理想标准
    tolerance: Optional[Any] = None  # 容忍范围（弹性要求）
    
    def __post_init__(self):
        """验证要求定义"""
        if self.req_type == RequirementType.HARD and self.tolerance is not None:
            raise ValueError("硬性要求不应设置容忍范围")


@dataclass
class CheckResult:
    """检查结果"""
    requirement_id: str              # 要求编号
    requirement_name: str            # 要求名称
    req_type: RequirementType        # 要求类型
    passed: bool                     # 是否通过
    actual_value: Any                # 实际值
    expected_value: Any              # 期望值
    message: str                     # 检查消息
    details: Dict[str, Any] = field(default_factory=dict)  # 详细信息
    
    @property
    def is_critical(self) -> bool:
        """是否为关键失败（硬性要求失败）"""
        return self.req_type == RequirementType.HARD and not self.passed


@dataclass
class LayerCheckResult:
    """单层检查结果"""
    layer_name: str                          # 层名称
    layer_step: int                          # 层序号
    results: List[CheckResult]               # 各要求检查结果
    trust_level: TrustLevel                  # 可信度等级
    score: float                             # 质量分数 (0-100)
    timestamp: str                           # 检查时间
    
    @property
    def hard_failures(self) -> List[CheckResult]:
        """硬性要求失败项"""
        return [r for r in self.results if r.is_critical]
    
    @property
    def elastic_warnings(self) -> List[CheckResult]:
        """弹性要求警告项"""
        return [r for r in self.results 
                if r.req_type == RequirementType.ELASTIC and not r.passed]
    
    @property
    def passed(self) -> bool:
        """是否通过所有硬性要求"""
        return len(self.hard_failures) == 0


@dataclass
class PipelineCheckResult:
    """管线整体检查结果"""
    overall_trust_level: TrustLevel          # 整体可信度
    overall_score: float                     # 整体质量分数
    layer_results: List[LayerCheckResult]    # 各层检查结果
    failed_layer: Optional[str] = None       # 首次失败的层
    timestamp: str = ""                      # 检查时间
    
    @property
    def can_proceed(self) -> bool:
        """是否可以继续执行"""
        return self.overall_trust_level != TrustLevel.UNTRUSTED


# ==================== 数据层契约 ====================

class DataLayerContract:
    """数据层契约"""
    
    # 必需字段
    REQUIRED_FIELDS = ['stock_code', 'date', 'open', 'high', 'low', 'close', 'volume']
    
    # 硬性要求
    HARD_REQUIREMENTS = [
        {
            'id': 'H1',
            'name': '数据非空',
            'description': 'market_data行数 > 0',
            'check': lambda df: len(df) > 0 if df is not None else False,
        },
        {
            'id': 'H2',
            'name': '必需字段完整',
            'description': 'open/high/low/close/volume/stock_code/date 字段齐全',
            'check': lambda df: all(col in df.columns for col in DataLayerContract.REQUIRED_FIELDS) if df is not None else False,
        },
        {
            'id': 'H3',
            'name': '时间序列连续',
            'description': '缺失率 < 10%',
            'check': lambda df: DataLayerContract._check_continuity(df),
        },
        {
            'id': 'H4',
            'name': '价格逻辑一致',
            'description': 'high >= max(open, close), low <= min(open, close)',
            'check': lambda df: DataLayerContract._check_price_logic(df),
        },
        {
            'id': 'H5',
            'name': '无未来数据泄露',
            'description': '无穿越数据',
            'check': lambda df: True,  # 具体实现需要上下文
        },
    ]
    
    # 弹性要求
    ELASTIC_REQUIREMENTS = [
        {
            'id': 'E1',
            'name': '数据完整性',
            'description': '数据完整性 >= 99%',
            'ideal': 0.99,
            'tolerance': 0.95,
        },
        {
            'id': 'E2',
            'name': '数据时效性',
            'description': '< 24小时（实盘）/ < 72小时（回测）',
            'ideal': 24,
            'tolerance': 72,
        },
        {
            'id': 'E3',
            'name': '质量分数',
            'description': '>= 80分',
            'ideal': 80,
            'tolerance': 70,
        },
        {
            'id': 'E4',
            'name': '多源一致性',
            'description': '>= 95%',
            'ideal': 0.95,
            'tolerance': 0.90,
        },
        {
            'id': 'E5',
            'name': '异常值比例',
            'description': '< 0.5%',
            'ideal': 0.005,
            'tolerance': 0.02,
        },
    ]
    
    @staticmethod
    def _check_continuity(df: pd.DataFrame) -> bool:
        """检查时间序列连续性"""
        if df is None or len(df) == 0:
            return False
        try:
            # 按股票分组检查
            grouped = df.groupby('stock_code')
            for stock_code, group in grouped:
                if len(group) <= 1:
                    continue
                dates = pd.to_datetime(group['date']).sort_values()
                expected_days = (dates.max() - dates.min()).days + 1
                actual_days = len(dates)
                # 允许10%的缺失
                if actual_days < expected_days * 0.9:
                    return False
            return True
        except Exception:
            return False
    
    @staticmethod
    def _check_price_logic(df: pd.DataFrame) -> bool:
        """检查价格逻辑一致性"""
        if df is None or len(df) == 0:
            return False
        try:
            # 检查 high >= max(open, close) 和 low <= min(open, close)
            valid_high = (df['high'] >= df[['open', 'close']].max(axis=1)).all()
            valid_low = (df['low'] <= df[['open', 'close']].min(axis=1)).all()
            return bool(valid_high and valid_low)
        except Exception:
            return False


# ==================== 因子层契约 ====================

class FactorLayerContract:
    """因子层契约"""
    
    # 必需字段
    REQUIRED_FIELDS = ['stock_code', 'date', 'factor_id', 'factor_value']
    
    # 硬性要求
    HARD_REQUIREMENTS = [
        {
            'id': 'H1',
            'name': '因子数据非空',
            'description': 'factor_df行数 > 0',
        },
        {
            'id': 'H2',
            'name': '至少1个有效因子',
            'description': 'factor_list非空',
        },
        {
            'id': 'H3',
            'name': '因子值非全NaN',
            'description': '非NaN比例 >= 50%',
        },
    ]
    
    # 弹性要求
    ELASTIC_REQUIREMENTS = [
        {
            'id': 'E1',
            'name': 'IC均值',
            'description': '>= 0.02（绝对值）',
            'ideal': 0.02,
            'tolerance': 0.01,
        },
        {
            'id': 'E2',
            'name': 'IR信息比率',
            'description': '>= 0.3',
            'ideal': 0.3,
            'tolerance': 0.2,
        },
        {
            'id': 'E3',
            'name': '因子相关性',
            'description': '< 0.7',
            'ideal': 0.7,
            'tolerance': 0.8,
        },
        {
            'id': 'E4',
            'name': '单调性',
            'description': '>= 0.6',
            'ideal': 0.6,
            'tolerance': 0.5,
        },
    ]


# ==================== 策略层契约 ====================

class StrategyLayerContract:
    """策略层契约"""
    
    # 硬性要求
    HARD_REQUIREMENTS = [
        {
            'id': 'H1',
            'name': '选股结果非空',
            'description': 'stock_selection非空',
        },
        {
            'id': 'H2',
            'name': '信号组合有效',
            'description': '信号编号存在',
        },
        {
            'id': 'H3',
            'name': '策略配置完整',
            'description': '必需参数齐全',
        },
        {
            'id': 'H4',
            'name': '回测验证通过',
            'description': '无致命错误',
        },
    ]
    
    # 弹性要求
    ELASTIC_REQUIREMENTS = [
        {
            'id': 'E1',
            'name': '策略胜率',
            'description': '>= 55%',
            'ideal': 0.55,
            'tolerance': 0.50,
        },
        {
            'id': 'E2',
            'name': '夏普比率',
            'description': '>= 1.0',
            'ideal': 1.0,
            'tolerance': 0.8,
        },
        {
            'id': 'E3',
            'name': '最大回撤',
            'description': '<= 20%',
            'ideal': 0.20,
            'tolerance': 0.25,
        },
        {
            'id': 'E4',
            'name': '换手率',
            'description': '<= 30%',
            'ideal': 0.30,
            'tolerance': 0.40,
        },
        {
            'id': 'E5',
            'name': '与基准相关性',
            'description': '<= 0.8',
            'ideal': 0.8,
            'tolerance': 0.9,
        },
    ]


# ==================== 组合优化层契约 ====================

class PortfolioLayerContract:
    """组合优化层契约"""
    
    # 硬性要求
    HARD_REQUIREMENTS = [
        {
            'id': 'H1',
            'name': '权重归一化',
            'description': '权重和在[0.95, 1.05]',
        },
        {
            'id': 'H2',
            'name': '单资产权重上限',
            'description': '<= 15%',
        },
        {
            'id': 'H3',
            'name': '权重非负',
            'description': '>= 0',
        },
        {
            'id': 'H4',
            'name': '输入有效性',
            'description': '选股结果非空',
        },
    ]
    
    # 弹性要求
    ELASTIC_REQUIREMENTS = [
        {
            'id': 'E1',
            'name': '行业集中度',
            'description': '<= 30%',
            'ideal': 0.30,
            'tolerance': 0.35,
        },
        {
            'id': 'E2',
            'name': '持仓数量',
            'description': '[5, 20]范围内',
            'ideal': (5, 20),
            'tolerance': (3, 25),
        },
        {
            'id': 'E3',
            'name': '换手率控制',
            'description': '<= 20%',
            'ideal': 0.20,
            'tolerance': 0.30,
        },
        {
            'id': 'E4',
            'name': '优化方法适配',
            'description': '根据数据特征选择',
        },
    ]


# ==================== 风控层契约 ====================

class RiskLayerContract:
    """风控层契约"""
    
    # 硬性要求
    HARD_REQUIREMENTS = [
        {
            'id': 'H1',
            'name': '单票权重上限',
            'description': '<= 12%',
        },
        {
            'id': 'H2',
            'name': '行业集中度',
            'description': '<= 30%',
        },
        {
            'id': 'H3',
            'name': '总仓位上限',
            'description': '<= 95%',
        },
        {
            'id': 'H4',
            'name': '止损线检查',
            'description': '回撤 <= 15%',
        },
        {
            'id': 'H5',
            'name': '黑名单检查',
            'description': '无禁买股票',
        },
    ]
    
    # 弹性要求
    ELASTIC_REQUIREMENTS = [
        {
            'id': 'E1',
            'name': '持仓数量',
            'description': '[5, 20]',
        },
        {
            'id': 'E2',
            'name': '换手率',
            'description': '<= 20%',
        },
        {
            'id': 'E3',
            'name': '流动性',
            'description': '成交额 > 1000万',
        },
        {
            'id': 'E4',
            'name': '相关性',
            'description': '股票间 < 0.7',
        },
        {
            'id': 'E5',
            'name': 'Beta暴露',
            'description': '|β| < 0.3',
        },
    ]


# ==================== 交易层契约 ====================

class TradingLayerContract:
    """交易层契约"""
    
    # 硬性要求
    HARD_REQUIREMENTS = [
        {
            'id': 'H1',
            'name': '订单有效性',
            'description': '数量 > 0, 价格合理',
        },
        {
            'id': 'H2',
            'name': '资金充足',
            'description': '可用资金 >= 所需资金',
        },
        {
            'id': 'H3',
            'name': '持仓充足',
            'description': '卖出数量 <= 持仓数量',
        },
        {
            'id': 'H4',
            'name': '交易时间',
            'description': '在交易时段内',
        },
    ]
    
    # 弹性要求
    ELASTIC_REQUIREMENTS = [
        {
            'id': 'E1',
            'name': '订单数量',
            'description': '<= 20笔',
        },
        {
            'id': 'E2',
            'name': '单笔金额',
            'description': '<= 总资产10%',
        },
        {
            'id': 'E3',
            'name': '价格偏离',
            'description': '<= 涨跌停限制',
        },
        {
            'id': 'E4',
            'name': '执行时机',
            'description': '非开盘/收盘前10分钟',
        },
    ]


# 层契约映射
LAYER_CONTRACTS = {
    'data': DataLayerContract,
    'factor': FactorLayerContract,
    'strategy': StrategyLayerContract,
    'portfolio': PortfolioLayerContract,
    'risk': RiskLayerContract,
    'trading': TradingLayerContract,
}
