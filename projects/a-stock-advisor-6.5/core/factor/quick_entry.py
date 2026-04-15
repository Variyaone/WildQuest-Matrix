"""
快速入库接口

支持快速录入因子、策略到库中，包括：
- 多来源支持（论文、第三方、用户分享）
- 自动分类和标签
- 自动验证
- CLI交互式录入
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import re
import logging

from .registry import (
    FactorRegistry,
    FactorMetadata,
    FactorCategory,
    FactorSubCategory,
    FactorDirection,
    FactorSource,
    ValidationStatus,
    get_factor_registry
)
from .enhanced_validator import (
    EnhancedFactorValidator,
    ValidationLevel,
    EnhancedValidationResult
)

logger = logging.getLogger(__name__)


@dataclass
class QuickEntryResult:
    """快速入库结果"""
    success: bool
    item_id: str
    item_name: str
    item_type: str
    message: str
    validation_result: Optional[EnhancedValidationResult] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class FactorQuickEntry:
    """
    因子快速入库
    
    支持多种录入方式：
    1. 从文本描述录入
    2. 从论文信息录入
    3. 从第三方来源录入
    4. 从用户分享录入
    """
    
    SOURCE_MAPPING = {
        "论文": FactorSource.ACADEMIC_PAPER,
        "学术论文": FactorSource.ACADEMIC_PAPER,
        "academic": FactorSource.ACADEMIC_PAPER,
        "自研": FactorSource.SELF_DEVELOPED,
        "自己": FactorSource.SELF_DEVELOPED,
        "self": FactorSource.SELF_DEVELOPED,
        "第三方": FactorSource.THIRD_PARTY,
        "third": FactorSource.THIRD_PARTY,
        "alpha101": FactorSource.ALPHA101,
        "alpha191": FactorSource.ALPHA191,
        "worldquant": FactorSource.WORLD_QUANT,
        "WorldQuant": FactorSource.WORLD_QUANT,
    }
    
    CATEGORY_KEYWORDS = {
        FactorCategory.MOMENTUM: ["动量", "momentum", "趋势", "trend", "涨幅", "收益"],
        FactorCategory.VALUE: ["估值", "value", "pe", "pb", "市盈率", "市净率", "价值"],
        FactorCategory.QUALITY: ["质量", "quality", "盈利", "roe", "roa", "财务"],
        FactorCategory.VOLATILITY: ["波动", "volatility", "风险", "risk", "标准差"],
        FactorCategory.LIQUIDITY: ["流动性", "liquidity", "换手", "turnover", "成交"],
        FactorCategory.SIZE: ["规模", "size", "市值", "market_cap", "大盘", "小盘"],
        FactorCategory.SENTIMENT: ["情绪", "sentiment", "舆情", "关注度"],
        FactorCategory.TECHNICAL: ["技术", "technical", "均线", "ma", "macd", "rsi"],
        FactorCategory.ALTERNATIVE: ["另类", "alternative", "供应链", "新闻", "社交"],
    }
    
    def __init__(self, registry: Optional[FactorRegistry] = None):
        self._registry = registry or get_factor_registry()
        self._validator = EnhancedFactorValidator(ValidationLevel.STANDARD)
    
    def quick_add(
        self,
        name: str,
        formula: str,
        description: str = "",
        source: str = "用户分享",
        category: Optional[str] = None,
        direction: str = "正向",
        tags: Optional[List[str]] = None,
        auto_validate: bool = True,
        author: str = "",
        paper_title: str = "",
        paper_url: str = ""
    ) -> QuickEntryResult:
        """
        快速添加因子
        
        Args:
            name: 因子名称
            formula: 因子公式
            description: 因子描述
            source: 来源（论文/第三方/用户分享/自研）
            category: 分类（可选，自动推断）
            direction: 方向（正向/反向）
            tags: 标签列表
            auto_validate: 是否自动验证
            author: 作者
            paper_title: 论文标题
            paper_url: 论文链接
            
        Returns:
            QuickEntryResult: 入库结果
        """
        try:
            if not name or not formula:
                return QuickEntryResult(
                    success=False,
                    item_id="",
                    item_name=name or "未知",
                    item_type="factor",
                    message="因子名称和公式不能为空"
                )
            
            existing = self._registry.get_by_name(name)
            if existing:
                return QuickEntryResult(
                    success=False,
                    item_id=existing.id,
                    item_name=name,
                    item_type="factor",
                    message=f"因子名称已存在: {existing.id}",
                    warnings=[f"已存在同名因子，ID: {existing.id}"]
                )
            
            warnings = []
            validated_formula = formula
            
            latex_patterns = [r'\\frac', r'\\sum', r'\\int', r'\\prod', r'\\sqrt', 
                            r'\\alpha', r'\\beta', r'\\gamma', r'\\delta',
                            r'\\begin{', r'\\end{', r'\\left', r'\\right']
            
            is_latex = any(re.search(p, formula, re.IGNORECASE) for p in latex_patterns)
            
            if is_latex:
                try:
                    from core.rdagent_integration.latex_converter import convert_factor_to_code
                    success, python_code, error = convert_factor_to_code(
                        name, formula, description
                    )
                    if success:
                        validated_formula = python_code
                        warnings.append("LaTeX公式已自动转换为Python代码")
                    else:
                        warnings.append(f"LaTeX转换失败: {error}")
                        warnings.append("请提供可执行的Python代码")
                        return QuickEntryResult(
                            success=False,
                            item_id="",
                            item_name=name,
                            item_type="factor",
                            message=f"LaTeX公式转换失败: {error}",
                            warnings=warnings
                        )
                except ImportError:
                    warnings.append("LaTeX转换器未安装，请提供Python代码")
                    return QuickEntryResult(
                        success=False,
                        item_id="",
                        item_name=name,
                        item_type="factor",
                        message="LaTeX公式无法直接入库，需要提供可执行的Python代码",
                        warnings=warnings
                    )
            
            try:
                compile(validated_formula, '<string>', 'exec')
            except SyntaxError:
                if not any(kw in validated_formula for kw in ['close', 'open', 'high', 'low', 'volume', 'return', 'price']):
                    warnings.append("公式可能不是有效的Python表达式，验证时可能失败")
            
            factor_source = self._parse_source(source)
            
            factor_category, sub_category = self._infer_category(name, description, formula, category)
            
            factor_direction = self._parse_direction(direction)
            
            full_description = self._build_description(
                description, author, paper_title, paper_url
            )
            
            auto_tags = self._extract_tags(name, description, formula)
            if tags:
                auto_tags = list(set(auto_tags + tags))
            
            factor = self._registry.register(
                name=name,
                description=full_description,
                formula=validated_formula,
                source=factor_source.value,
                category=factor_category,
                sub_category=sub_category,
                direction=factor_direction,
                tags=auto_tags,
                parameters={"original_formula": formula} if validated_formula != formula else None
            )
            
            message = f"因子入库成功: {factor.id}"
            validation_result = None
            
            if auto_validate:
                message += " (待验证)"
            
            return QuickEntryResult(
                success=True,
                item_id=factor.id,
                item_name=name,
                item_type="factor",
                message=message,
                validation_result=validation_result,
                warnings=warnings
            )
            
        except Exception as e:
            logger.error(f"快速入库失败: {e}")
            return QuickEntryResult(
                success=False,
                item_id="",
                item_name=name,
                item_type="factor",
                message=f"入库失败: {str(e)}"
            )
    
    def quick_add_from_text(
        self,
        text: str,
        auto_validate: bool = True
    ) -> QuickEntryResult:
        """
        从文本描述快速添加因子
        
        支持格式：
        - 名称: xxx, 公式: xxx, 描述: xxx
        - 因子名称: xxx
          公式: xxx
          描述: xxx
        
        Args:
            text: 文本描述
            auto_validate: 是否自动验证
            
        Returns:
            QuickEntryResult: 入库结果
        """
        try:
            parsed = self._parse_text_input(text)
            
            if not parsed.get("name"):
                return QuickEntryResult(
                    success=False,
                    item_id="",
                    item_name="",
                    item_type="factor",
                    message="无法从文本中解析出因子名称"
                )
            
            return self.quick_add(
                name=parsed.get("name", ""),
                formula=parsed.get("formula", ""),
                description=parsed.get("description", ""),
                source=parsed.get("source", "用户分享"),
                category=parsed.get("category"),
                direction=parsed.get("direction", "正向"),
                tags=parsed.get("tags"),
                auto_validate=auto_validate
            )
            
        except Exception as e:
            return QuickEntryResult(
                success=False,
                item_id="",
                item_name="",
                item_type="factor",
                message=f"解析失败: {str(e)}"
            )
    
    def quick_add_from_paper(
        self,
        paper_title: str,
        paper_url: str,
        author: str,
        factor_name: str,
        formula: str,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> QuickEntryResult:
        """
        从论文信息添加因子
        
        Args:
            paper_title: 论文标题
            paper_url: 论文链接
            author: 作者
            factor_name: 因子名称
            formula: 因子公式
            description: 因子描述
            tags: 标签
            
        Returns:
            QuickEntryResult: 入库结果
        """
        full_name = f"{factor_name}"
        
        return self.quick_add(
            name=full_name,
            formula=formula,
            description=description,
            source="学术论文",
            tags=tags,
            auto_validate=True,
            author=author,
            paper_title=paper_title,
            paper_url=paper_url
        )
    
    def quick_add_batch(
        self,
        factors: List[Dict[str, str]],
        auto_validate: bool = True
    ) -> List[QuickEntryResult]:
        """
        批量快速入库
        
        Args:
            factors: 因子列表，每个元素包含name, formula, description等
            auto_validate: 是否自动验证
            
        Returns:
            List[QuickEntryResult]: 入库结果列表
        """
        results = []
        
        for factor_data in factors:
            result = self.quick_add(
                name=factor_data.get("name", ""),
                formula=factor_data.get("formula", ""),
                description=factor_data.get("description", ""),
                source=factor_data.get("source", "用户分享"),
                category=factor_data.get("category"),
                direction=factor_data.get("direction", "正向"),
                tags=factor_data.get("tags"),
                auto_validate=auto_validate
            )
            results.append(result)
        
        return results
    
    def _parse_source(self, source: str) -> FactorSource:
        """解析来源"""
        source_lower = source.lower()
        
        for key, factor_source in self.SOURCE_MAPPING.items():
            if key.lower() in source_lower:
                return factor_source
        
        return FactorSource.THIRD_PARTY
    
    def _parse_direction(self, direction: str) -> FactorDirection:
        """解析方向"""
        direction_lower = direction.lower()
        
        if "反" in direction_lower or "negative" in direction_lower:
            return FactorDirection.NEGATIVE
        
        return FactorDirection.POSITIVE
    
    def _infer_category(
        self,
        name: str,
        description: str,
        formula: str,
        category: Optional[str]
    ) -> tuple:
        """推断因子分类"""
        from .classification import get_factor_classification
        
        classification = get_factor_classification()
        
        if category:
            for cat in FactorCategory:
                if category.lower() in cat.value.lower() or cat.value.lower() in category.lower():
                    sub_cats = classification.get_sub_categories(cat)
                    return cat, sub_cats[0] if sub_cats else FactorSubCategory.TIME_SERIES_MOMENTUM
        
        combined_text = f"{name} {description} {formula}".lower()
        
        for category_enum, keywords in self.CATEGORY_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    sub_cats = classification.get_sub_categories(category_enum)
                    return category_enum, sub_cats[0] if sub_cats else FactorSubCategory.TIME_SERIES_MOMENTUM
        
        return FactorCategory.TECHNICAL, FactorSubCategory.TREND_FACTOR
    
    def _build_description(
        self,
        description: str,
        author: str,
        paper_title: str,
        paper_url: str
    ) -> str:
        """构建完整描述"""
        parts = []
        
        if description:
            parts.append(description)
        
        if author:
            parts.append(f"作者: {author}")
        
        if paper_title:
            parts.append(f"论文: {paper_title}")
        
        if paper_url:
            parts.append(f"链接: {paper_url}")
        
        return " | ".join(parts) if parts else "快速入库因子"
    
    def _extract_tags(
        self,
        name: str,
        description: str,
        formula: str
    ) -> List[str]:
        """提取标签"""
        tags = []
        
        combined = f"{name} {description} {formula}".lower()
        
        tag_keywords = {
            "动量": ["动量", "momentum"],
            "反转": ["反转", "reversal"],
            "波动": ["波动", "volatility"],
            "流动性": ["流动性", "liquidity", "换手"],
            "估值": ["估值", "value", "pe", "pb"],
            "质量": ["质量", "quality", "盈利"],
            "技术": ["技术", "technical", "均线"],
            "情绪": ["情绪", "sentiment"],
        }
        
        for tag, keywords in tag_keywords.items():
            for keyword in keywords:
                if keyword in combined:
                    tags.append(tag)
                    break
        
        return list(set(tags))
    
    def _parse_text_input(self, text: str) -> Dict[str, Any]:
        """解析文本输入"""
        result = {}
        
        patterns = {
            "name": [r"名称[：:]\s*(.+?)(?:\n|,|，|$)", r"因子名称[：:]\s*(.+?)(?:\n|,|，|$)"],
            "formula": [r"公式[：:]\s*(.+?)(?:\n|描述|来源|$)", r"计算公式[：:]\s*(.+?)(?:\n|描述|来源|$)"],
            "description": [r"描述[：:]\s*(.+?)(?:\n|来源|分类|$)", r"说明[：:]\s*(.+?)(?:\n|来源|分类|$)"],
            "source": [r"来源[：:]\s*(.+?)(?:\n|分类|方向|$)"],
            "category": [r"分类[：:]\s*(.+?)(?:\n|方向|标签|$)"],
            "direction": [r"方向[：:]\s*(.+?)(?:\n|标签|$)"],
        }
        
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    result[key] = match.group(1).strip()
                    break
        
        if not result.get("name"):
            lines = text.strip().split('\n')
            if lines:
                first_line = lines[0].strip()
                if len(first_line) < 50:
                    result["name"] = first_line
        
        return result


class StrategyQuickEntry:
    """
    策略快速入库
    
    支持快速录入策略到策略库。
    """
    
    def __init__(self):
        from ..strategy.registry import get_strategy_registry
        self._registry = get_strategy_registry()
    
    def quick_add(
        self,
        name: str,
        description: str,
        factors: List[str],
        rebalance_freq: str = "月度",
        stock_pool: str = "全市场",
        max_stocks: int = 30,
        source: str = "用户分享",
        tags: Optional[List[str]] = None
    ) -> QuickEntryResult:
        """
        快速添加策略
        
        Args:
            name: 策略名称
            description: 策略描述
            factors: 因子列表
            rebalance_freq: 调仓频率
            stock_pool: 股票池
            max_stocks: 最大持仓数
            source: 来源
            tags: 标签
            
        Returns:
            QuickEntryResult: 入库结果
        """
        try:
            if not name:
                return QuickEntryResult(
                    success=False,
                    item_id="",
                    item_name="",
                    item_type="strategy",
                    message="策略名称不能为空"
                )
            
            strategy = self._registry.register(
                name=name,
                description=description,
                factors=factors,
                rebalance_freq=rebalance_freq,
                stock_pool=stock_pool,
                max_stocks=max_stocks,
                source=source,
                tags=tags or []
            )
            
            return QuickEntryResult(
                success=True,
                item_id=strategy.id,
                item_name=name,
                item_type="strategy",
                message=f"策略入库成功: {strategy.id}"
            )
            
        except Exception as e:
            logger.error(f"策略入库失败: {e}")
            return QuickEntryResult(
                success=False,
                item_id="",
                item_name=name,
                item_type="strategy",
                message=f"入库失败: {str(e)}"
            )


def get_factor_quick_entry() -> FactorQuickEntry:
    """获取因子快速入库实例"""
    return FactorQuickEntry()


def get_strategy_quick_entry() -> StrategyQuickEntry:
    """获取策略快速入库实例"""
    return StrategyQuickEntry()
