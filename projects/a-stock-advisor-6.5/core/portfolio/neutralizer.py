"""
组合中性化处理器模块

支持多种中性化方式:
- 行业中性化
- 风格中性化（市值、估值等）
- 市值中性化
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from core.infrastructure.exceptions import AppException, ErrorCode

logger = logging.getLogger(__name__)


class NeutralizationStatus(Enum):
    """中性化状态"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    SKIPPED = "skipped"
    INVALID_INPUT = "invalid_input"


@dataclass
class NeutralizationResult:
    """中性化结果"""
    status: NeutralizationStatus
    weights: Dict[str, float] = field(default_factory=dict)
    message: str = ""
    industry_adjusted: bool = False
    style_adjusted: bool = False
    market_cap_adjusted: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def is_success(self) -> bool:
        return self.status in [NeutralizationStatus.SUCCESS, NeutralizationStatus.PARTIAL, NeutralizationStatus.SKIPPED]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'status': self.status.value,
            'weights': self.weights,
            'message': self.message,
            'industry_adjusted': self.industry_adjusted,
            'style_adjusted': self.style_adjusted,
            'market_cap_adjusted': self.market_cap_adjusted,
            'details': self.details,
            'errors': self.errors,
            'warnings': self.warnings
        }


class NeutralizationError(AppException):
    """中性化错误异常"""
    
    def __init__(self, message: str, details: Optional[Dict] = None, cause: Optional[Exception] = None):
        super().__init__(
            message=message,
            code=ErrorCode.STRATEGY_ERROR,
            details=details or {},
            cause=cause
        )


class PortfolioNeutralizer:
    """
    组合中性化器
    
    支持多种中性化方式:
    - 行业中性化: 各行业权重与基准一致
    - 风格中性化: 风格因子暴露归零
    - 市值中性化: 市值因子暴露归零
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.neutralize_industry = self.config.get("neutralize_industry", True)
        self.neutralize_style = self.config.get("neutralize_style", False)
        self.neutralize_market_cap = self.config.get("neutralize_market_cap", False)
        self.max_industry_deviation = self.config.get("max_industry_deviation", 0.05)
        self.max_style_deviation = self.config.get("max_style_deviation", 0.05)
        self.max_market_cap_deviation = self.config.get("max_market_cap_deviation", 0.05)
    
    def _validate_portfolio(self, portfolio: dict) -> Tuple[bool, str]:
        """验证组合权重"""
        if portfolio is None:
            return False, "组合权重不能为None"
        
        if not isinstance(portfolio, dict):
            return False, f"组合权重必须是字典类型，当前类型: {type(portfolio)}"
        
        for stock_code, weight in portfolio.items():
            if not isinstance(stock_code, str):
                return False, f"股票代码必须是字符串类型，当前类型: {type(stock_code)}"
            
            if not isinstance(weight, (int, float)):
                return False, f"权重必须是数值类型，{stock_code} 当前类型: {type(weight)}"
            
            if weight < 0:
                return False, f"权重不能为负数，{stock_code} = {weight}"
        
        return True, ""
    
    def neutralize(
        self,
        portfolio: dict,
        market_data: Any = None,
        industry_weights: dict = None,
        style_exposures: dict = None,
        market_cap_exposures: dict = None,
        neutralize_industry: bool = None,
        neutralize_style: bool = None,
        neutralize_market_cap: bool = None
    ) -> NeutralizationResult:
        """
        组合中性化
        
        Args:
            portfolio: 组合权重字典 {stock_code: weight}
            market_data: 市场数据（包含行业、市值等信息）
            industry_weights: 基准行业权重 {industry: weight}
            style_exposures: 股票风格暴露 {stock_code: {style: exposure}}
            market_cap_exposures: 股票市值暴露 {stock_code: exposure}
            neutralize_industry: 是否行业中性化
            neutralize_style: 是否风格中性化
            neutralize_market_cap: 是否市值中性化
            
        Returns:
            NeutralizationResult: 包含状态、权重、错误信息等
        """
        valid, error_msg = self._validate_portfolio(portfolio)
        if not valid:
            logger.error(f"组合权重验证失败: {error_msg}")
            return NeutralizationResult(
                status=NeutralizationStatus.INVALID_INPUT,
                message=error_msg,
                errors=[error_msg]
            )
        
        if not portfolio:
            logger.warning("组合为空，跳过中性化")
            return NeutralizationResult(
                status=NeutralizationStatus.SKIPPED,
                message="组合为空，跳过中性化",
                weights={}
            )
        
        if neutralize_industry is None:
            neutralize_industry = self.neutralize_industry
        if neutralize_style is None:
            neutralize_style = self.neutralize_style
        if neutralize_market_cap is None:
            neutralize_market_cap = self.neutralize_market_cap
        
        neutralized_portfolio = portfolio.copy()
        errors = []
        warnings = []
        industry_adjusted = False
        style_adjusted = False
        market_cap_adjusted = False
        
        if neutralize_industry:
            result = self._neutralize_industry(
                neutralized_portfolio, market_data, industry_weights
            )
            if result.get('error'):
                errors.append(f"行业中性化失败: {result['error']}")
            elif result.get('warning'):
                warnings.append(result['warning'])
            else:
                neutralized_portfolio = result.get('portfolio', neutralized_portfolio)
                industry_adjusted = result.get('adjusted', False)
        
        if neutralize_style:
            result = self._neutralize_style(
                neutralized_portfolio, market_data, style_exposures
            )
            if result.get('error'):
                errors.append(f"风格中性化失败: {result['error']}")
            elif result.get('warning'):
                warnings.append(result['warning'])
            else:
                neutralized_portfolio = result.get('portfolio', neutralized_portfolio)
                style_adjusted = result.get('adjusted', False)
        
        if neutralize_market_cap:
            result = self._neutralize_market_cap(
                neutralized_portfolio, market_data, market_cap_exposures
            )
            if result.get('error'):
                errors.append(f"市值中性化失败: {result['error']}")
            elif result.get('warning'):
                warnings.append(result['warning'])
            else:
                neutralized_portfolio = result.get('portfolio', neutralized_portfolio)
                market_cap_adjusted = result.get('adjusted', False)
        
        if errors:
            status = NeutralizationStatus.FAILED if len(errors) > 1 or (not industry_adjusted and not style_adjusted and not market_cap_adjusted) else NeutralizationStatus.PARTIAL
            logger.error(f"中性化过程中发生错误: {errors}")
        elif warnings:
            status = NeutralizationStatus.PARTIAL
            logger.warning(f"中性化过程中有警告: {warnings}")
        else:
            status = NeutralizationStatus.SUCCESS
        
        logger.info(f"组合中性化完成: {len(neutralized_portfolio)} 只股票, 状态: {status.value}")
        
        return NeutralizationResult(
            status=status,
            weights=neutralized_portfolio,
            message=f"中性化完成，行业调整: {industry_adjusted}, 风格调整: {style_adjusted}, 市值调整: {market_cap_adjusted}",
            industry_adjusted=industry_adjusted,
            style_adjusted=style_adjusted,
            market_cap_adjusted=market_cap_adjusted,
            details={
                'original_stock_count': len(portfolio),
                'final_stock_count': len(neutralized_portfolio),
                'total_weight': sum(neutralized_portfolio.values())
            },
            errors=errors,
            warnings=warnings
        )
    
    def _neutralize_industry(
        self,
        portfolio: dict,
        market_data: Any,
        benchmark_industry_weights: dict = None
    ) -> dict:
        """行业中性化"""
        result = {'portfolio': portfolio, 'adjusted': False, 'error': None, 'warning': None}
        
        try:
            stock_codes = list(portfolio.keys())
            
            industry_exposures = self._get_industry_exposures(stock_codes, market_data)
            
            if not industry_exposures:
                msg = "无法获取行业暴露，跳过行业中性化"
                logger.warning(msg)
                result['warning'] = msg
                return result
            
            portfolio_industry_weights = {}
            for stock, weight in portfolio.items():
                industry = industry_exposures.get(stock, "其他")
                portfolio_industry_weights[industry] = portfolio_industry_weights.get(industry, 0) + weight
            
            if benchmark_industry_weights is None:
                benchmark_industry_weights = self._get_benchmark_industry_weights(market_data)
            
            if not benchmark_industry_weights:
                msg = "无法获取基准行业权重，跳过行业中性化"
                logger.warning(msg)
                result['warning'] = msg
                return result
            
            adjustments = {}
            for industry in benchmark_industry_weights:
                target_weight = benchmark_industry_weights[industry]
                current_weight = portfolio_industry_weights.get(industry, 0)
                deviation = current_weight - target_weight
                
                if abs(deviation) > self.max_industry_deviation:
                    adjustments[industry] = -deviation
            
            if adjustments:
                neutralized_portfolio = self._apply_industry_adjustments(
                    portfolio, industry_exposures, adjustments
                )
                logger.info(f"行业中性化调整: {len(adjustments)} 个行业")
                result['portfolio'] = neutralized_portfolio
                result['adjusted'] = True
                return result
            
            return result
            
        except Exception as e:
            error_msg = f"行业中性化异常: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _neutralize_style(
        self,
        portfolio: dict,
        market_data: Any,
        style_exposures: dict = None
    ) -> dict:
        """风格中性化"""
        result = {'portfolio': portfolio, 'adjusted': False, 'error': None, 'warning': None}
        
        try:
            stock_codes = list(portfolio.keys())
            
            if style_exposures is None:
                style_exposures = self._get_style_exposures(stock_codes, market_data)
            
            if not style_exposures:
                msg = "无法获取风格暴露，跳过风格中性化"
                logger.warning(msg)
                result['warning'] = msg
                return result
            
            portfolio_style_exposures = {}
            for stock, weight in portfolio.items():
                for style, exposure in style_exposures.get(stock, {}).items():
                    portfolio_style_exposures[style] = portfolio_style_exposures.get(style, 0) + weight * exposure
            
            benchmark_style_exposures = self._get_benchmark_style_exposures(market_data)
            
            if not benchmark_style_exposures:
                benchmark_style_exposures = {style: 0 for style in portfolio_style_exposures}
            
            adjustments = {}
            for style in portfolio_style_exposures:
                target_exposure = benchmark_style_exposures.get(style, 0)
                current_exposure = portfolio_style_exposures.get(style, 0)
                deviation = current_exposure - target_exposure
                
                if abs(deviation) > self.max_style_deviation:
                    adjustments[style] = -deviation
            
            if adjustments:
                neutralized_portfolio = self._apply_style_adjustments(
                    portfolio, style_exposures, adjustments
                )
                logger.info(f"风格中性化调整: {len(adjustments)} 个风格因子")
                result['portfolio'] = neutralized_portfolio
                result['adjusted'] = True
                return result
            
            return result
            
        except Exception as e:
            error_msg = f"风格中性化异常: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _neutralize_market_cap(
        self,
        portfolio: dict,
        market_data: Any,
        market_cap_exposures: dict = None
    ) -> dict:
        """市值中性化"""
        result = {'portfolio': portfolio, 'adjusted': False, 'error': None, 'warning': None}
        
        try:
            stock_codes = list(portfolio.keys())
            
            if market_cap_exposures is None:
                market_cap_exposures = self._get_market_cap_exposures(stock_codes, market_data)
            
            if not market_cap_exposures:
                msg = "无法获取市值暴露，跳过市值中性化"
                logger.warning(msg)
                result['warning'] = msg
                return result
            
            portfolio_market_cap_exposure = 0
            for stock, weight in portfolio.items():
                exposure = market_cap_exposures.get(stock, 0)
                portfolio_market_cap_exposure += weight * exposure
            
            if abs(portfolio_market_cap_exposure) > self.max_market_cap_deviation:
                neutralized_portfolio = self._apply_market_cap_adjustments(
                    portfolio, market_cap_exposures, -portfolio_market_cap_exposure
                )
                logger.info("市值中性化调整完成")
                result['portfolio'] = neutralized_portfolio
                result['adjusted'] = True
                return result
            
            return result
            
        except Exception as e:
            error_msg = f"市值中性化异常: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _get_industry_exposures(
        self,
        stock_codes: List[str],
        market_data: Any
    ) -> Dict[str, str]:
        """获取行业暴露"""
        try:
            if market_data is None:
                logger.error("市场数据为None")
                return {}
            
            if hasattr(market_data, 'columns'):
                if 'industry' in market_data.columns:
                    industry_data = market_data[market_data.index.isin(stock_codes)]
                    return industry_data['industry'].to_dict()
                elif '行业' in market_data.columns:
                    industry_data = market_data[market_data.index.isin(stock_codes)]
                    return industry_data['行业'].to_dict()
            
            logger.warning("市场数据中未找到行业列")
            return {}
        except Exception as e:
            logger.error(f"获取行业暴露失败: {e}")
            return {}
    
    def _get_benchmark_industry_weights(self, market_data: Any) -> Dict[str, float]:
        """获取基准行业权重"""
        try:
            if market_data is None:
                logger.error("市场数据为None")
                return {}
            
            if hasattr(market_data, 'columns'):
                if 'industry' in market_data.columns:
                    industry_counts = market_data['industry'].value_counts(normalize=True)
                    return industry_counts.to_dict()
                elif '行业' in market_data.columns:
                    industry_counts = market_data['行业'].value_counts(normalize=True)
                    return industry_counts.to_dict()
            
            return {}
        except Exception as e:
            logger.error(f"获取基准行业权重失败: {e}")
            return {}
    
    def _get_style_exposures(
        self,
        stock_codes: List[str],
        market_data: Any
    ) -> Dict[str, Dict[str, float]]:
        """获取风格暴露"""
        try:
            if market_data is None:
                logger.error("市场数据为None")
                return {}
            
            if not hasattr(market_data, 'columns'):
                return {}
            
            style_columns = []
            for col in ['market_cap', 'pe_ratio', 'pb_ratio', '市值', '市盈率', '市净率', 'beta', 'momentum']:
                if col in market_data.columns:
                    style_columns.append(col)
            
            if not style_columns:
                return {}
            
            stock_data = market_data[market_data.index.isin(stock_codes)]
            
            style_exposures = {}
            for stock in stock_codes:
                if stock in stock_data.index:
                    exposures = {}
                    for col in style_columns:
                        value = stock_data.loc[stock, col]
                        if pd.notna(value):
                            exposures[col] = float(value)
                    style_exposures[stock] = exposures
            
            return style_exposures
            
        except Exception as e:
            logger.error(f"获取风格暴露失败: {e}")
            return {}
    
    def _get_benchmark_style_exposures(self, market_data: Any) -> Dict[str, float]:
        """获取基准风格暴露"""
        try:
            if market_data is None:
                logger.error("市场数据为None")
                return {}
            
            if not hasattr(market_data, 'columns'):
                return {}
            
            style_columns = []
            for col in ['market_cap', 'pe_ratio', 'pb_ratio', '市值', '市盈率', '市净率', 'beta', 'momentum']:
                if col in market_data.columns:
                    style_columns.append(col)
            
            if not style_columns:
                return {}
            
            benchmark_exposures = {}
            for col in style_columns:
                mean_value = market_data[col].mean()
                if pd.notna(mean_value):
                    benchmark_exposures[col] = float(mean_value)
            
            return benchmark_exposures
            
        except Exception as e:
            logger.error(f"获取基准风格暴露失败: {e}")
            return {}
    
    def _get_market_cap_exposures(
        self,
        stock_codes: List[str],
        market_data: Any
    ) -> Dict[str, float]:
        """获取市值暴露"""
        try:
            if market_data is None:
                logger.error("市场数据为None")
                return {}
            
            if not hasattr(market_data, 'columns'):
                return {}
            
            market_cap_col = None
            for col in ['market_cap', '市值', 'total_mv']:
                if col in market_data.columns:
                    market_cap_col = col
                    break
            
            if market_cap_col is None:
                return {}
            
            stock_data = market_data[market_data.index.isin(stock_codes)]
            
            market_cap_values = stock_data[market_cap_col]
            if market_cap_values.isna().all():
                return {}
            
            mean_cap = market_cap_values.mean()
            std_cap = market_cap_values.std()
            
            if std_cap == 0:
                std_cap = 1
            
            market_cap_exposures = {}
            for stock in stock_codes:
                if stock in stock_data.index:
                    value = stock_data.loc[stock, market_cap_col]
                    if pd.notna(value):
                        market_cap_exposures[stock] = (value - mean_cap) / std_cap
            
            return market_cap_exposures
            
        except Exception as e:
            logger.error(f"获取市值暴露失败: {e}")
            return {}
    
    def _apply_industry_adjustments(
        self,
        portfolio: dict,
        industry_exposures: dict,
        adjustments: dict
    ) -> dict:
        """应用行业调整"""
        neutralized_portfolio = portfolio.copy()
        
        for stock in neutralized_portfolio:
            industry = industry_exposures.get(stock, "其他")
            if industry in adjustments:
                adjustment_factor = 1 + adjustments[industry]
                neutralized_portfolio[stock] *= adjustment_factor
        
        total_weight = sum(neutralized_portfolio.values())
        if total_weight > 0:
            neutralized_portfolio = {
                k: v / total_weight for k, v in neutralized_portfolio.items()
            }
        else:
            logger.error("调整后总权重为0，返回原始组合")
            return portfolio.copy()
        
        return neutralized_portfolio
    
    def _apply_style_adjustments(
        self,
        portfolio: dict,
        style_exposures: dict,
        adjustments: dict
    ) -> dict:
        """应用风格调整"""
        neutralized_portfolio = portfolio.copy()
        
        for stock in neutralized_portfolio:
            stock_styles = style_exposures.get(stock, {})
            total_adjustment = 0
            
            for style, adjustment in adjustments.items():
                if style in stock_styles:
                    total_adjustment += stock_styles[style] * adjustment
            
            adjustment_factor = 1 + total_adjustment
            neutralized_portfolio[stock] *= adjustment_factor
        
        total_weight = sum(neutralized_portfolio.values())
        if total_weight > 0:
            neutralized_portfolio = {
                k: v / total_weight for k, v in neutralized_portfolio.items()
            }
        else:
            logger.error("调整后总权重为0，返回原始组合")
            return portfolio.copy()
        
        return neutralized_portfolio
    
    def _apply_market_cap_adjustments(
        self,
        portfolio: dict,
        market_cap_exposures: dict,
        target_adjustment: float
    ) -> dict:
        """应用市值调整"""
        neutralized_portfolio = portfolio.copy()
        
        total_exposure = sum(
            portfolio.get(stock, 0) * market_cap_exposures.get(stock, 0)
            for stock in portfolio
        )
        
        if total_exposure == 0:
            return portfolio.copy()
        
        for stock in neutralized_portfolio:
            exposure = market_cap_exposures.get(stock, 0)
            if exposure != 0:
                adjustment = -target_adjustment * (exposure / total_exposure)
                neutralized_portfolio[stock] *= (1 + adjustment)
        
        total_weight = sum(neutralized_portfolio.values())
        if total_weight > 0:
            neutralized_portfolio = {
                k: v / total_weight for k, v in neutralized_portfolio.items()
            }
        else:
            logger.error("调整后总权重为0，返回原始组合")
            return portfolio.copy()
        
        return neutralized_portfolio


__all__ = [
    'NeutralizationStatus',
    'NeutralizationResult',
    'NeutralizationError',
    'PortfolioNeutralizer',
]
