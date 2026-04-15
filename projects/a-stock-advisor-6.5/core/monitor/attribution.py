"""
归因分析模块

分析收益来源，支持Brinson归因、因子归因、行业归因等。
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import pandas as pd
import numpy as np

from core.infrastructure.logging import get_logger


class AttributionType(Enum):
    """归因类型"""
    BRINSON = "brinson"     # Brinson归因
    FACTOR = "factor"       # 因子归因
    INDUSTRY = "industry"   # 行业归因
    STOCK = "stock"         # 个股归因


@dataclass
class AttributionItem:
    """归因项"""
    name: str
    contribution: float
    weight: float
    return_rate: float
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AttributionResult:
    """归因结果"""
    attribution_type: AttributionType
    total_return: float
    benchmark_return: float
    excess_return: float
    items: List[AttributionItem] = field(default_factory=list)
    date: str = ""
    generated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "attribution_type": self.attribution_type.value,
            "total_return": self.total_return,
            "benchmark_return": self.benchmark_return,
            "excess_return": self.excess_return,
            "items": [i.to_dict() for i in self.items],
            "date": self.date,
            "generated_at": self.generated_at.isoformat()
        }
    
    def get_top_contributors(self, n: int = 10) -> List[AttributionItem]:
        """获取最大贡献项"""
        sorted_items = sorted(self.items, key=lambda x: x.contribution, reverse=True)
        return sorted_items[:n]
    
    def get_top_detractors(self, n: int = 10) -> List[AttributionItem]:
        """获取最大拖累项"""
        sorted_items = sorted(self.items, key=lambda x: x.contribution)
        return sorted_items[:n]


@dataclass
class BrinsonResult:
    """Brinson归因结果"""
    allocation_effect: float = 0.0      # 配置效应
    selection_effect: float = 0.0       # 选择效应
    interaction_effect: float = 0.0     # 交互效应
    total_excess: float = 0.0           # 总超额
    details: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AttributionAnalyzer:
    """归因分析器"""
    
    def __init__(
        self,
        analyzer_id: str = "main",
        storage_path: str = "./data/attribution"
    ):
        self.analyzer_id = analyzer_id
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.logger = get_logger("monitor.attribution")
    
    def analyze_brinson(
        self,
        portfolio_returns: pd.DataFrame,
        benchmark_returns: pd.DataFrame,
        portfolio_weights: pd.DataFrame,
        benchmark_weights: pd.DataFrame
    ) -> BrinsonResult:
        """
        Brinson归因分析
        
        Args:
            portfolio_returns: 组合收益率 (index: 行业, columns: 收益率)
            benchmark_returns: 基准收益率 (index: 行业, columns: 收益率)
            portfolio_weights: 组合权重 (index: 行业, columns: 权重)
            benchmark_weights: 基准权重 (index: 行业, columns: 权重)
        
        Returns:
            BrinsonResult: Brinson归因结果
        """
        industries = portfolio_returns.index.union(benchmark_returns.index)
        
        allocation_effect = 0.0
        selection_effect = 0.0
        interaction_effect = 0.0
        details = []
        
        for industry in industries:
            wp = portfolio_weights.loc[industry, 'weight'] if industry in portfolio_weights.index else 0
            wb = benchmark_weights.loc[industry, 'weight'] if industry in benchmark_weights.index else 0
            rp = portfolio_returns.loc[industry, 'return'] if industry in portfolio_returns.index else 0
            rb = benchmark_returns.loc[industry, 'return'] if industry in benchmark_returns.index else 0
            
            alloc = (wp - wb) * rb
            select = wb * (rp - rb)
            interact = (wp - wb) * (rp - rb)
            
            allocation_effect += alloc
            selection_effect += select
            interaction_effect += interact
            
            details.append({
                "industry": industry,
                "portfolio_weight": wp,
                "benchmark_weight": wb,
                "portfolio_return": rp,
                "benchmark_return": rb,
                "allocation_effect": alloc,
                "selection_effect": select,
                "interaction_effect": interact
            })
        
        total_excess = allocation_effect + selection_effect + interaction_effect
        
        return BrinsonResult(
            allocation_effect=allocation_effect,
            selection_effect=selection_effect,
            interaction_effect=interaction_effect,
            total_excess=total_excess,
            details=details
        )
    
    def analyze_factor(
        self,
        returns: pd.Series,
        factor_exposures: pd.DataFrame,
        factor_returns: pd.Series
    ) -> AttributionResult:
        """
        因子归因分析
        
        Args:
            returns: 组合收益率序列
            factor_exposures: 因子暴露矩阵 (index: 时间, columns: 因子)
            factor_returns: 因子收益率序列 (index: 因子)
        
        Returns:
            AttributionResult: 因子归因结果
        """
        total_return = returns.sum() if len(returns) > 0 else 0
        
        items = []
        for factor in factor_exposures.columns:
            exposure = factor_exposures[factor].mean()
            factor_ret = factor_returns.get(factor, 0)
            contribution = exposure * factor_ret
            
            items.append(AttributionItem(
                name=factor,
                contribution=contribution,
                weight=exposure,
                return_rate=factor_ret,
                details={"exposure": exposure, "factor_return": factor_ret}
            ))
        
        return AttributionResult(
            attribution_type=AttributionType.FACTOR,
            total_return=total_return,
            benchmark_return=0,
            excess_return=total_return,
            items=items,
            date=datetime.now().strftime("%Y-%m-%d")
        )
    
    def analyze_industry(
        self,
        portfolio_returns: pd.DataFrame,
        portfolio_weights: pd.DataFrame
    ) -> AttributionResult:
        """
        行业归因分析
        
        Args:
            portfolio_returns: 行业收益率 (index: 行业, columns: 收益率)
            portfolio_weights: 行业权重 (index: 行业, columns: 权重)
        
        Returns:
            AttributionResult: 行业归因结果
        """
        total_return = 0.0
        items = []
        
        for industry in portfolio_returns.index:
            weight = portfolio_weights.loc[industry, 'weight'] if industry in portfolio_weights.index else 0
            ret = portfolio_returns.loc[industry, 'return'] if industry in portfolio_returns.index else 0
            contribution = weight * ret
            
            total_return += contribution
            
            items.append(AttributionItem(
                name=industry,
                contribution=contribution,
                weight=weight,
                return_rate=ret
            ))
        
        return AttributionResult(
            attribution_type=AttributionType.INDUSTRY,
            total_return=total_return,
            benchmark_return=0,
            excess_return=total_return,
            items=items,
            date=datetime.now().strftime("%Y-%m-%d")
        )
    
    def analyze_stock(
        self,
        stock_returns: pd.DataFrame,
        stock_weights: pd.DataFrame
    ) -> AttributionResult:
        """
        个股归因分析
        
        Args:
            stock_returns: 个股收益率 (index: 股票代码, columns: 收益率)
            stock_weights: 个股权重 (index: 股票代码, columns: 权重)
        
        Returns:
            AttributionResult: 个股归因结果
        """
        total_return = 0.0
        items = []
        
        for stock in stock_returns.index:
            weight = stock_weights.loc[stock, 'weight'] if stock in stock_weights.index else 0
            ret = stock_returns.loc[stock, 'return'] if stock in stock_returns.index else 0
            contribution = weight * ret
            
            total_return += contribution
            
            items.append(AttributionItem(
                name=stock,
                contribution=contribution,
                weight=weight,
                return_rate=ret
            ))
        
        return AttributionResult(
            attribution_type=AttributionType.STOCK,
            total_return=total_return,
            benchmark_return=0,
            excess_return=total_return,
            items=items,
            date=datetime.now().strftime("%Y-%m-%d")
        )
    
    def comprehensive_attribution(
        self,
        portfolio_data: Dict[str, Any],
        benchmark_data: Dict[str, Any]
    ) -> Dict[str, AttributionResult]:
        """
        综合归因分析
        
        Args:
            portfolio_data: 组合数据
            benchmark_data: 基准数据
        
        Returns:
            Dict[str, AttributionResult]: 各类归因结果
        """
        results = {}
        
        if "industry_returns" in portfolio_data and "industry_weights" in portfolio_data:
            portfolio_returns = pd.DataFrame(portfolio_data["industry_returns"])
            portfolio_weights = pd.DataFrame(portfolio_data["industry_weights"])
            
            if "industry_returns" in benchmark_data and "industry_weights" in benchmark_data:
                benchmark_returns = pd.DataFrame(benchmark_data["industry_returns"])
                benchmark_weights = pd.DataFrame(benchmark_data["industry_weights"])
                
                brinson = self.analyze_brinson(
                    portfolio_returns, benchmark_returns,
                    portfolio_weights, benchmark_weights
                )
                
                results["brinson"] = AttributionResult(
                    attribution_type=AttributionType.BRINSON,
                    total_return=portfolio_returns['return'].sum() if 'return' in portfolio_returns.columns else 0,
                    benchmark_return=benchmark_returns['return'].sum() if 'return' in benchmark_returns.columns else 0,
                    excess_return=brinson.total_excess,
                    items=[
                        AttributionItem(
                            name="配置效应",
                            contribution=brinson.allocation_effect,
                            weight=1.0,
                            return_rate=brinson.allocation_effect
                        ),
                        AttributionItem(
                            name="选择效应",
                            contribution=brinson.selection_effect,
                            weight=1.0,
                            return_rate=brinson.selection_effect
                        ),
                        AttributionItem(
                            name="交互效应",
                            contribution=brinson.interaction_effect,
                            weight=1.0,
                            return_rate=brinson.interaction_effect
                        )
                    ]
                )
        
        if "factor_exposures" in portfolio_data and "factor_returns" in portfolio_data:
            returns = pd.Series(portfolio_data.get("returns", []))
            exposures = pd.DataFrame(portfolio_data["factor_exposures"])
            factor_rets = pd.Series(portfolio_data["factor_returns"])
            
            results["factor"] = self.analyze_factor(returns, exposures, factor_rets)
        
        if "industry_returns" in portfolio_data and "industry_weights" in portfolio_data:
            portfolio_returns = pd.DataFrame(portfolio_data["industry_returns"])
            portfolio_weights = pd.DataFrame(portfolio_data["industry_weights"])
            
            results["industry"] = self.analyze_industry(portfolio_returns, portfolio_weights)
        
        if "stock_returns" in portfolio_data and "stock_weights" in portfolio_data:
            stock_returns = pd.DataFrame(portfolio_data["stock_returns"])
            stock_weights = pd.DataFrame(portfolio_data["stock_weights"])
            
            results["stock"] = self.analyze_stock(stock_returns, stock_weights)
        
        return results
    
    def save_result(self, result: AttributionResult, name: str) -> bool:
        """保存归因结果"""
        file_path = self.storage_path / f"{name}.json"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"保存归因结果: {name}")
        return True
    
    def load_result(self, name: str) -> Optional[AttributionResult]:
        """加载归因结果"""
        file_path = self.storage_path / f"{name}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return AttributionResult(
                attribution_type=AttributionType(data["attribution_type"]),
                total_return=data["total_return"],
                benchmark_return=data["benchmark_return"],
                excess_return=data["excess_return"],
                items=[
                    AttributionItem(**item) for item in data["items"]
                ],
                date=data["date"]
            )
        
        except Exception as e:
            self.logger.error(f"加载归因结果失败: {e}")
            return None
    
    def generate_report(self, result: AttributionResult) -> str:
        """生成归因报告"""
        lines = [
            f"# 归因分析报告 ({result.attribution_type.value})",
            "",
            f"**分析日期**: {result.date}",
            f"**总收益**: {result.total_return:.2%}",
            f"**基准收益**: {result.benchmark_return:.2%}",
            f"**超额收益**: {result.excess_return:.2%}",
            "",
            "## 主要贡献项 (Top 10)",
            ""
        ]
        
        for item in result.get_top_contributors(10):
            lines.append(f"- **{item.name}**: {item.contribution:.4f} (权重: {item.weight:.2%}, 收益: {item.return_rate:.2%})")
        
        lines.extend([
            "",
            "## 主要拖累项 (Top 10)",
            ""
        ])
        
        for item in result.get_top_detractors(10):
            lines.append(f"- **{item.name}**: {item.contribution:.4f} (权重: {item.weight:.2%}, 收益: {item.return_rate:.2%})")
        
        return "\n".join(lines)
