"""
检查报告生成器

生成格式化的检查报告。
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from .contracts import (
    TrustLevel,
    PipelineCheckResult,
    LayerCheckResult,
    CheckResult,
    RequirementType
)


class CheckReporter:
    """检查报告生成器"""
    
    def __init__(self):
        """初始化报告生成器"""
        pass
    
    def generate_report(self, result: PipelineCheckResult) -> str:
        """
        生成检查报告
        
        Args:
            result: 管线检查结果
            
        Returns:
            str: 格式化的报告
        """
        lines = []
        
        # 报告头部
        lines.extend(self._generate_header(result))
        
        # 各层检查详情
        lines.extend(self._generate_layer_details(result))
        
        # 失败项列表
        lines.extend(self._generate_failures(result))
        
        # 警告项列表
        lines.extend(self._generate_warnings(result))
        
        # 执行建议
        lines.extend(self._generate_recommendations(result))
        
        return '\n'.join(lines)
    
    def _generate_header(self, result: PipelineCheckResult) -> List[str]:
        """生成报告头部"""
        lines = []
        lines.append("=" * 70)
        lines.append("前置检查报告")
        lines.append("=" * 70)
        lines.append(f"报告时间: {result.timestamp}")
        lines.append(f"整体结果: {self._format_trust_level(result.overall_trust_level)}")
        lines.append(f"可信度分数: {result.overall_score:.1f}/100")
        
        if result.failed_layer:
            lines.append(f"失败层: {result.failed_layer}")
        
        lines.append("")
        return lines
    
    def _generate_layer_details(self, result: PipelineCheckResult) -> List[str]:
        """生成各层检查详情"""
        lines = []
        lines.append("-" * 70)
        lines.append("各层检查详情")
        lines.append("-" * 70)
        
        for layer_result in result.layer_results:
            lines.extend(self._generate_layer_section(layer_result))
        
        return lines
    
    def _generate_layer_section(self, layer_result: LayerCheckResult) -> List[str]:
        """生成单个层的报告部分"""
        lines = []
        lines.append(f"\n【Step{layer_result.layer_step} {layer_result.layer_name}】")
        lines.append(f"  可信度: {self._format_trust_level(layer_result.trust_level)}")
        lines.append(f"  质量分数: {layer_result.score:.1f}/100")
        
        # 硬性要求
        hard_results = [r for r in layer_result.results if r.req_type == RequirementType.HARD]
        if hard_results:
            lines.append("  硬性要求:")
            for r in hard_results:
                icon = "✓" if r.passed else "✗"
                lines.append(f"    {icon} {r.requirement_id} {r.requirement_name}: {r.message}")
        
        # 弹性要求
        elastic_results = [r for r in layer_result.results if r.req_type == RequirementType.ELASTIC]
        if elastic_results:
            lines.append("  弹性要求:")
            for r in elastic_results:
                icon = "✓" if r.passed else "⚠"
                lines.append(f"    {icon} {r.requirement_id} {r.requirement_name}: {r.message}")
        
        return lines
    
    def _generate_failures(self, result: PipelineCheckResult) -> List[str]:
        """生成失败项列表"""
        lines = []
        
        # 收集所有失败项
        failures = []
        for layer_result in result.layer_results:
            failures.extend(layer_result.hard_failures)
        
        if failures:
            lines.append("\n" + "-" * 70)
            lines.append("失败项列表")
            lines.append("-" * 70)
            
            for failure in failures:
                lines.append(f"\n❌ {failure.requirement_id} {failure.requirement_name}")
                lines.append(f"   详情: {failure.message}")
                lines.append(f"   实际值: {failure.actual_value}")
                lines.append(f"   期望值: {failure.expected_value}")
        
        return lines
    
    def _generate_warnings(self, result: PipelineCheckResult) -> List[str]:
        """生成警告项列表"""
        lines = []
        
        # 收集所有警告项
        warnings = []
        for layer_result in result.layer_results:
            warnings.extend(layer_result.elastic_warnings)
        
        if warnings:
            lines.append("\n" + "-" * 70)
            lines.append("警告项列表")
            lines.append("-" * 70)
            
            for warning in warnings:
                lines.append(f"\n⚠ {warning.requirement_id} {warning.requirement_name}")
                lines.append(f"   详情: {warning.message}")
                lines.append(f"   实际值: {warning.actual_value}")
                lines.append(f"   期望值: {warning.expected_value}")
        
        return lines
    
    def _generate_recommendations(self, result: PipelineCheckResult) -> List[str]:
        """生成执行建议"""
        lines = []
        lines.append("\n" + "=" * 70)
        lines.append("执行建议")
        lines.append("=" * 70)
        
        if result.overall_trust_level == TrustLevel.TRUSTED:
            lines.append("✓ 所有检查通过，结果可信，可以执行操作")
        elif result.overall_trust_level == TrustLevel.PARTIAL:
            lines.append("⚠ 部分弹性要求未达标，结果部分可信")
            lines.append("  建议:")
            lines.append("  1. 查看警告项列表，评估风险")
            lines.append("  2. 如风险可控，可以继续执行")
            lines.append("  3. 如风险不可控，建议修复后重新检查")
        else:
            lines.append("✗ 存在硬性要求失败，结果不可信")
            lines.append("  建议:")
            lines.append(f"  1. 修复 {result.failed_layer} 层的问题")
            lines.append("  2. 从数据层开始重新执行管线")
            lines.append("  3. 所有步骤通过后再执行操作")
        
        return lines
    
    def _format_trust_level(self, level: TrustLevel) -> str:
        """格式化可信度等级"""
        format_map = {
            TrustLevel.TRUSTED: "✓ TRUSTED (可信)",
            TrustLevel.PARTIAL: "⚠ PARTIAL (部分可信)",
            TrustLevel.UNTRUSTED: "✗ UNTRUSTED (不可信)"
        }
        return format_map.get(level, str(level))
    
    def generate_summary(self, result: PipelineCheckResult) -> Dict[str, Any]:
        """
        生成报告摘要
        
        Args:
            result: 管线检查结果
            
        Returns:
            Dict: 摘要信息
        """
        return {
            'timestamp': result.timestamp,
            'trust_level': result.overall_trust_level.value,
            'score': result.overall_score,
            'can_proceed': result.can_proceed,
            'failed_layer': result.failed_layer,
            'layer_count': len(result.layer_results),
            'hard_failures': sum(len(r.hard_failures) for r in result.layer_results),
            'elastic_warnings': sum(len(r.elastic_warnings) for r in result.layer_results),
        }
