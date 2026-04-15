"""
RDAgent因子脚本转换器

将RDAgent生成的因子脚本转换为项目可用的格式。
"""

import ast
import re
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConvertedFactor:
    """转换后的因子"""
    name: str
    formula: str
    description: str
    original_code: str
    dependencies: List[str]
    variables: Dict[str, str]
    source: str = "RDAgent自动挖掘"


class RDAgentFactorConverter:
    """
    RDAgent因子脚本转换器
    
    将RDAgent生成的因子脚本（使用daily_pv.h5）转换为
    项目可用的格式（接受DataFrame参数）。
    """
    
    COLUMN_MAPPINGS = {
        '$close': 'close',
        '$open': 'open',
        '$high': 'high',
        '$low': 'low',
        '$volume': 'volume',
        'instrument': 'stock_code',
        'datetime': 'date',
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def convert_script(self, script_path: str) -> Optional[ConvertedFactor]:
        """
        转换单个因子脚本
        
        Args:
            script_path: 脚本文件路径
        
        Returns:
            转换后的因子对象，失败返回None
        """
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                original_code = f.read()
            
            tree = ast.parse(original_code)
            
            factor_name = self._extract_factor_name(tree, original_code)
            if not factor_name:
                self.logger.warning(f"无法提取因子名称: {script_path}")
                return None
            
            calculate_func = self._find_calculate_function(tree)
            if not calculate_func:
                self.logger.warning(f"未找到计算函数: {script_path}")
                return None
            
            formula_code = self._extract_formula(calculate_func, original_code)
            if not formula_code:
                self.logger.warning(f"无法提取公式: {script_path}")
                return None
            
            # 先转换列名和操作
            converted_formula = self._convert_formula(formula_code)
            
            # 再转换为表达式格式
            converted_formula = self._wrap_as_function(converted_formula)
            
            dependencies = self._extract_dependencies(converted_formula)
            
            variables = self._extract_variables(converted_formula)
            
            description = self._generate_description(factor_name, converted_formula)
            
            return ConvertedFactor(
                name=factor_name,
                formula=converted_formula,
                description=description,
                original_code=original_code,
                dependencies=dependencies,
                variables=variables,
                source="RDAgent自动挖掘"
            )
            
        except Exception as e:
            self.logger.error(f"转换脚本失败 {script_path}: {e}")
            return None
    
    def convert_workspace(
        self,
        workspace_path: str,
        output_file: Optional[str] = None
    ) -> List[ConvertedFactor]:
        """
        转换整个workspace中的因子脚本
        
        Args:
            workspace_path: RDAgent workspace路径
            output_file: 输出JSON文件路径（可选）
        
        Returns:
            转换后的因子列表
        """
        import json
        from pathlib import Path
        
        workspace = Path(workspace_path)
        if not workspace.exists():
            self.logger.error(f"Workspace不存在: {workspace_path}")
            return []
        
        factors = []
        
        for factor_dir in workspace.iterdir():
            if not factor_dir.is_dir():
                continue
            
            factor_script = factor_dir / "factor.py"
            if not factor_script.exists():
                continue
            
            self.logger.info(f"转换因子: {factor_dir.name}")
            converted = self.convert_script(str(factor_script))
            
            if converted:
                factors.append(converted)
                self.logger.info(f"  ✓ 成功: {converted.name}")
            else:
                self.logger.warning(f"  ✗ 失败: {factor_dir.name}")
        
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            factors_data = []
            for f in factors:
                factors_data.append({
                    "name": f.name,
                    "formula": f.formula,
                    "description": f.description,
                    "original_code": f.original_code,
                    "dependencies": f.dependencies,
                    "variables": f.variables,
                    "source": f.source,
                })
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(factors_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"\n已保存 {len(factors)} 个因子到: {output_file}")
        
        return factors
    
    def _extract_factor_name(self, tree: ast.AST, code: str) -> Optional[str]:
        """提取因子名称"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('calculate_'):
                    return node.name.replace('calculate_', '')
        
        match = re.search(r"df\[['\"](\w+)['\"]\]\s*=", code)
        if match:
            return match.group(1)
        
        return None
    
    def _find_calculate_function(self, tree: ast.AST) -> Optional[ast.FunctionDef]:
        """查找计算函数"""
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.startswith('calculate_'):
                    return node
        return None
    
    def _extract_formula(self, func_node: ast.FunctionDef, original_code: str) -> Optional[str]:
        """提取公式代码"""
        formulas = []
        
        for node in ast.walk(func_node):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript):
                        if isinstance(target.value, ast.Name) and target.value.id == 'df':
                            if isinstance(target.slice, ast.Constant):
                                col_name = target.slice.value
                                if col_name not in ['datetime', 'instrument', 'date', 'stock_code']:
                                    start_line = node.lineno - 1
                                    end_line = node.end_lineno if hasattr(node, 'end_lineno') else start_line + 1
                                    lines = original_code.split('\n')
                                    formula_line = '\n'.join(lines[start_line:end_line])
                                    # 去除每行的前导空格
                                    formula_line = '\n'.join(line.strip() for line in formula_line.split('\n'))
                                    formulas.append(formula_line)
        
        if formulas:
            return '\n'.join(formulas)
        
        return None
    
    def _convert_formula(self, formula_code: str) -> str:
        """转换公式代码"""
        converted = formula_code
        
        # 列名映射
        for old_col, new_col in self.COLUMN_MAPPINGS.items():
            escaped_old_col = re.escape(old_col)
            converted = re.sub(
                rf"df\[['\"]{escaped_old_col}['\"]\]",
                f"df['{new_col}']",
                converted
            )
            converted = re.sub(
                rf"\['{escaped_old_col}'\]",
                f"['{new_col}']",
                converted
            )
        
        # 修复groupby + rolling的索引问题
        # 将 df.groupby('col')['val'].rolling(N).func() 
        # 转换为 df.groupby('col')['val'].transform(lambda x: x.rolling(N).func())
        pattern = r"df\.groupby\(['\"](\w+)['\"]\)\[['\"](\w+)['\"]\]\.rolling\(([^)]+)\)\.(\w+)\(\)"
        
        def replace_rolling(match):
            group_col = match.group(1)
            value_col = match.group(2)
            window = match.group(3)
            func = match.group(4)
            return f"df.groupby('{group_col}')['{value_col}'].transform(lambda x: x.rolling({window}).{func}())"
        
        converted = re.sub(pattern, replace_rolling, converted)
        
        # 修复groupby + diff的写法（虽然通常可以工作，但统一使用transform更安全）
        # df.groupby('col')['val'].diff() -> df.groupby('col')['val'].transform(lambda x: x.diff())
        # 但实际上diff()可以直接赋值，所以不需要修改
        
        # 转换groupby操作中的列名
        converted = self._convert_groupby_operations(converted)
        
        return converted
    
    def _convert_groupby_operations(self, code: str) -> str:
        """转换groupby操作"""
        code = re.sub(
            r"df\.groupby\(['\"]instrument['\"]\)",
            "df.groupby('stock_code')",
            code
        )
        
        code = re.sub(
            r"df\.groupby\(['\"]datetime['\"]\)",
            "df.groupby('date')",
            code
        )
        
        return code
    
    def _wrap_as_function(self, formula_code: str) -> str:
        """将公式转换为表达式格式（因子引擎需要表达式，不是函数定义）"""
        # 去除每行的前导空格
        lines = [line.strip() for line in formula_code.strip().split('\n') if line.strip()]
        
        # 单行公式：直接提取表达式
        if len(lines) == 1 and '=' in lines[0]:
            match = re.match(r"df\[['\"](\w+)['\"]\]\s*=\s*(.+)", lines[0])
            if match:
                expression = match.group(2).strip()
                return expression
        
        # 多行公式：尝试内联中间变量
        # 收集所有赋值语句
        assignments = []
        for line in lines:
            if line.strip():
                match = re.search(r"df\[['\"]([^'\"]+)['\"]\]\s*=\s*(.+)", line)
                if match:
                    var_name = match.group(1)
                    expression = match.group(2).strip()
                    assignments.append((var_name, expression))
        
        if not assignments:
            return formula_code
        
        # 从最后一个赋值开始，尝试内联
        final_var, final_expr = assignments[-1]
        
        # 对于包含groupby操作的复杂公式，我们采用特殊处理
        # 构建一个包含所有中间变量计算的完整表达式
        if any('groupby' in expr for var, expr in assignments):
            # 对于groupby公式，我们需要保留中间变量
            # 使用exec方式执行，但包装成表达式
            # 创建一个包含所有计算的代码块
            calc_lines = []
            for var_name, var_expr in assignments:
                calc_lines.append(f"df['{var_name}'] = {var_expr}")
            
            # 返回一个特殊的表达式，让引擎知道需要先执行中间计算
            # 使用分号分隔的多行表达式
            full_expr = "; ".join(calc_lines) + f"; df['{final_var}']"
            return full_expr
        
        # 对于非groupby公式，尝试简单内联
        inlined_expr = final_expr
        max_iterations = 10
        
        for _ in range(max_iterations):
            changed = False
            for var_name, var_expr in reversed(assignments[:-1]):
                patterns = [
                    (f"df['{var_name}']", f"({var_expr})"),
                    (f'df["{var_name}"]', f"({var_expr})"),
                ]
                for pattern, replacement in patterns:
                    if pattern in inlined_expr:
                        inlined_expr = inlined_expr.replace(pattern, replacement)
                        changed = True
            
            if not changed:
                break
        
        return inlined_expr
    
    def _extract_factor_name_from_code(self, code: str) -> str:
        """从代码中提取因子名称"""
        match = re.search(r"df\[['\"]([^'\"]+)['\"]\]\s*=", code)
        if match:
            return match.group(1)
        return "factor"
    
    def _extract_dependencies(self, formula: str) -> List[str]:
        """提取依赖的列"""
        dependencies = set()
        
        standard_cols = ['close', 'open', 'high', 'low', 'volume', 'date', 'stock_code']
        
        for col in standard_cols:
            if f"df['{col}']" in formula or f'df["{col}"]' in formula:
                dependencies.add(col)
        
        return sorted(list(dependencies))
    
    def _extract_variables(self, formula: str) -> Dict[str, str]:
        """提取变量说明"""
        variables = {}
        
        col_descriptions = {
            'close': '收盘价',
            'open': '开盘价',
            'high': '最高价',
            'low': '最低价',
            'volume': '成交量',
            'date': '日期',
            'stock_code': '股票代码',
        }
        
        for col, desc in col_descriptions.items():
            if f"df['{col}']" in formula or f'df["{col}"]' in formula:
                variables[col] = desc
        
        window_match = re.search(r'\.shift\((\d+)\)', formula)
        if window_match:
            variables['window'] = f'回看窗口: {window_match.group(1)}天'
        
        rolling_match = re.search(r'\.rolling\((\d+)', formula)
        if rolling_match:
            variables['rolling_window'] = f'滚动窗口: {rolling_match.group(1)}天'
        
        return variables
    
    def _generate_description(self, name: str, formula: str) -> str:
        """生成因子描述"""
        desc_parts = [f"因子名称: {name}"]
        
        if 'shift' in formula:
            match = re.search(r'\.shift\((\d+)\)', formula)
            if match:
                desc_parts.append(f"回看期: {match.group(1)}天")
        
        if 'rolling' in formula:
            match = re.search(r'\.rolling\((\d+)', formula)
            if match:
                desc_parts.append(f"滚动窗口: {match.group(1)}天")
        
        if 'momentum' in name.lower():
            desc_parts.append("类型: 动量因子")
        elif 'volume' in name.lower():
            desc_parts.append("类型: 成交量因子")
        elif 'volatility' in name.lower():
            desc_parts.append("类型: 波动率因子")
        
        desc_parts.append("来源: RDAgent自动挖掘")
        
        return " | ".join(desc_parts)


def convert_rdagent_factors(
    workspace_path: str = "git_ignore_folder/RD-Agent_workspace",
    output_file: str = "converted_rdagent_factors.json"
) -> List[ConvertedFactor]:
    """
    转换RDAgent因子
    
    Args:
        workspace_path: RDAgent workspace路径
        output_file: 输出文件路径
    
    Returns:
        转换后的因子列表
    """
    converter = RDAgentFactorConverter()
    return converter.convert_workspace(workspace_path, output_file)


def import_converted_factors(
    factors_file: str = "converted_rdagent_factors.json",
    auto_validate: bool = False
) -> Dict[str, Any]:
    """
    导入转换后的因子到因子库
    
    Args:
        factors_file: 转换后的因子JSON文件
        auto_validate: 是否自动验证
    
    Returns:
        导入结果
    """
    import json
    from pathlib import Path
    from core.factor.quick_entry import FactorQuickEntry
    
    result = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "factors": [],
        "errors": [],
    }
    
    factors_path = Path(factors_file)
    if not factors_path.exists():
        logger.error(f"因子文件不存在: {factors_file}")
        return result
    
    with open(factors_path, 'r', encoding='utf-8') as f:
        factors_data = json.load(f)
    
    result["total"] = len(factors_data)
    logger.info(f"\n{'=' * 60}")
    logger.info("导入RDAgent转换因子到因子库")
    logger.info("=" * 60)
    logger.info(f"共 {len(factors_data)} 个因子待导入\n")
    
    quick_entry = FactorQuickEntry()
    
    for i, factor_data in enumerate(factors_data):
        name = factor_data.get("name", f"Factor_{i+1}")
        formula = factor_data.get("formula", "")
        description = factor_data.get("description", "")
        source = factor_data.get("source", "RDAgent自动挖掘")
        
        logger.info(f"[{i+1}/{len(factors_data)}] 导入: {name}")
        
        try:
            entry_result = quick_entry.quick_add(
                name=name,
                formula=formula,
                description=description,
                source=source,
                auto_validate=auto_validate,
            )
            
            if entry_result.success:
                result["success"] += 1
                result["factors"].append({
                    "id": entry_result.item_id,
                    "name": name,
                    "status": "success",
                })
                logger.info(f"  ✓ 成功: {entry_result.item_id}")
            else:
                if "已存在" in entry_result.message:
                    result["skipped"] += 1
                    logger.info(f"  - 跳过: {entry_result.message}")
                else:
                    result["failed"] += 1
                    result["errors"].append(f"{name}: {entry_result.message}")
                    logger.error(f"  ✗ 失败: {entry_result.message}")
        
        except Exception as e:
            result["failed"] += 1
            result["errors"].append(f"{name}: {str(e)}")
            logger.error(f"  ✗ 异常: {e}")
    
    logger.info(f"\n{'=' * 60}")
    logger.info("导入完成")
    logger.info("=" * 60)
    logger.info(f"总计: {result['total']} 个")
    logger.info(f"成功: {result['success']} 个")
    logger.info(f"跳过: {result['skipped']} 个")
    logger.info(f"失败: {result['failed']} 个")
    
    return result
