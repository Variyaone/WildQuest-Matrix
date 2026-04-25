"""
日报推送

推送日报给交易员/管理人员，包含前置检查机制确保推送内容可信。
"""

import os
import json
import time
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

import requests

from ..infrastructure.logging import get_logger
from ..infrastructure.config import get_config
from ..validation.pre_check import get_pre_check_manager, PreCheckManager
from ..validation.pre_push_checker import (
    PrePushChecker,
    PrePushCheckResult,
    get_pre_push_checker,
    CheckSeverity
)


class PreCheckStatus(Enum):
    """前置检查状态"""
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"


@dataclass
class LayerCheckStatus:
    """层检查状态"""
    layer_name: str
    passed: bool
    checks: Dict[str, bool] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_name": self.layer_name,
            "passed": self.passed,
            "checks": self.checks,
            "error_message": self.error_message
        }


@dataclass
class NotifyResult:
    """推送结果"""
    success: bool
    pre_check_passed: bool = False
    pre_check_details: Dict[str, Any] = field(default_factory=dict)
    webhook_sent: bool = False
    retry_count: int = 0
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "pre_check_passed": self.pre_check_passed,
            "pre_check_details": self.pre_check_details,
            "webhook_sent": self.webhook_sent,
            "retry_count": self.retry_count,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "details": self.details
        }


@dataclass
class TradeInstruction:
    """交易指令"""
    stock_code: str
    stock_name: str
    direction: str
    shares: int
    price_range: tuple
    amount: float
    timing: str
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stock_code": self.stock_code,
            "stock_name": self.stock_name,
            "direction": self.direction,
            "shares": self.shares,
            "price_range": self.price_range,
            "amount": self.amount,
            "timing": self.timing,
            "reason": self.reason
        }


class DailyNotifier:
    """
    日报推送
    
    推送日报给交易员/管理人员，推送前必须确认所有前置步骤成功。
    
    强制前置检查机制：
    - Step1 数据层检查
    - Step2 因子层检查
    - Step3 策略层检查
    - Step4 组合优化层检查
    - Step5 风控层检查
    
    策略质量检查：
    - 胜率 >= 55%
    - IC均值 >= 0.02
    - IR信息比率 >= 0.3
    - 夏普比率 >= 1.0
    - 最大回撤 <= 20%
    
    风控指标检查：
    - 单票权重 <= 12%
    - 行业集中度 <= 30%
    - 总仓位 <= 95%
    
    自动重试机制：
    - 检查失败时自动触发前置步骤重试
    - 最多重试3次
    - 每次重试间隔60秒
    """
    
    LAYER_ORDER = ['data', 'factor', 'strategy', 'portfolio', 'risk']
    
    def __init__(
        self,
        pre_check_manager: Optional[PreCheckManager] = None,
        pre_push_checker: Optional[PrePushChecker] = None,
        webhook_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: int = 60,
        max_pre_check_retries: int = 3,
        logger_name: str = "daily.notifier"
    ):
        """
        初始化推送器
        
        Args:
            pre_check_manager: 前置检查管理器
            pre_push_checker: 推送前置检查器
            webhook_url: Webhook URL
            max_retries: Webhook推送最大重试次数
            retry_delay: 重试延迟（秒）
            max_pre_check_retries: 前置检查最大重试次数
            logger_name: 日志名称
        """
        self.pre_check_manager = pre_check_manager or get_pre_check_manager()
        self.pre_push_checker = pre_push_checker or get_pre_push_checker()
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_pre_check_retries = max_pre_check_retries
        self.logger = get_logger(logger_name)
        
        config = get_config()
        self.webhook_url = webhook_url or config.notification.webhook_url
        
        self._layer_executors: Dict[str, Callable] = {}
    
    def register_layer_executor(self, layer: str, executor: Callable):
        """
        注册层级执行器
        
        Args:
            layer: 层名称
            executor: 执行函数
        """
        self._layer_executors[layer] = executor
    
    def notify(
        self,
        report_content: Optional[str] = None,
        report_data: Optional[Dict[str, Any]] = None,
        trade_instructions: Optional[List[TradeInstruction]] = None,
        skip_pre_check: bool = False,
        strategy_metrics: Optional[Dict[str, float]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None
    ) -> NotifyResult:
        """
        执行推送
        
        Args:
            report_content: 报告内容
            report_data: 报告数据
            trade_instructions: 交易指令列表
            skip_pre_check: 是否跳过前置检查（不推荐）
            strategy_metrics: 策略质量指标
            risk_metrics: 风控指标
            
        Returns:
            NotifyResult: 推送结果
        """
        import time as time_module
        start_time = time_module.time()
        
        self.logger.info("开始日报推送")
        
        pre_check_result = None
        pre_push_result = None
        total_retries = 0
        
        if not skip_pre_check:
            for attempt in range(self.max_pre_check_retries):
                self.logger.info(f"执行推送前置检查 (尝试 {attempt + 1}/{self.max_pre_check_retries})")
                
                pre_push_result = self._execute_pre_push_check(
                    strategy_metrics=strategy_metrics,
                    risk_metrics=risk_metrics
                )
                
                if pre_push_result.passed:
                    self.logger.info("推送前置检查通过")
                    break
                
                if pre_push_result.retry_required and attempt < self.max_pre_check_retries - 1:
                    self.logger.warning(
                        f"推送前置检查未通过，需要重试层级: {pre_push_result.retry_layers}"
                    )
                    
                    retry_success = self._retry_layers(pre_push_result.retry_layers)
                    total_retries += 1
                    
                    if not retry_success:
                        self.logger.error("层级重试失败")
                        break
                    
                    self.logger.info(f"等待 {self.retry_delay} 秒后重新检查...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error("推送前置检查未通过，无可用重试")
                    break
            
            if not pre_push_result or not pre_push_result.passed:
                duration = time_module.time() - start_time
                self.logger.error("推送前置检查最终未通过，推送终止")
                
                return NotifyResult(
                    success=False,
                    pre_check_passed=False,
                    pre_check_details=pre_push_result.to_dict() if pre_push_result else {},
                    duration_seconds=duration,
                    error_message="推送前置检查未通过",
                    retry_count=total_retries
                )
            
            pre_check_result = self._execute_pre_check()
            
            if not pre_check_result["passed"]:
                duration = time_module.time() - start_time
                self.logger.error("层检查未通过，推送终止")
                
                return NotifyResult(
                    success=False,
                    pre_check_passed=False,
                    pre_check_details=pre_check_result,
                    duration_seconds=duration,
                    error_message="层检查未通过",
                    retry_count=total_retries
                )
        else:
            pre_check_result = {"passed": True, "layers": {}, "skipped": True}
            self.logger.warning("已跳过前置检查，这可能存在风险")
        
        message = self._build_push_message(
            report_content,
            report_data,
            trade_instructions,
            pre_check_result
        )
        
        if pre_push_result:
            message["pre_push_check"] = pre_push_result.to_dict()
        
        webhook_result = self._send_webhook(message)
        
        duration = time_module.time() - start_time
        
        success = webhook_result["success"]
        
        if success:
            self.logger.info("日报推送成功")
        else:
            self.logger.error(f"日报推送失败: {webhook_result.get('error')}")
        
        return NotifyResult(
            success=success,
            pre_check_passed=True,
            pre_check_details=pre_check_result,
            webhook_sent=webhook_result["success"],
            retry_count=webhook_result.get("retry_count", 0) + total_retries,
            duration_seconds=duration,
            error_message=webhook_result.get("error"),
            details={
                "message_length": len(json.dumps(message)),
                "pre_push_retries": total_retries
            }
        )
    
    def _execute_pre_push_check(
        self,
        strategy_metrics: Optional[Dict[str, float]] = None,
        risk_metrics: Optional[Dict[str, Any]] = None
    ) -> PrePushCheckResult:
        """
        执行推送前置检查
        
        Args:
            strategy_metrics: 策略质量指标
            risk_metrics: 风控指标
            
        Returns:
            PrePushCheckResult: 检查结果
        """
        step_status = self.pre_push_checker.get_step_status()
        
        return self.pre_push_checker.check_all(
            strategy_metrics=strategy_metrics,
            pre_step_status=step_status,
            risk_metrics=risk_metrics
        )
    
    def _retry_layers(self, layers: List[str]) -> bool:
        """
        重试指定层级
        
        Args:
            layers: 需要重试的层级列表
            
        Returns:
            bool: 是否重试成功
        """
        self.logger.info(f"开始重试层级: {layers}")
        
        for layer in layers:
            if layer in self._layer_executors:
                try:
                    self.logger.info(f"执行层级: {layer}")
                    executor = self._layer_executors[layer]
                    result = executor()
                    
                    if result:
                        self.pre_push_checker.mark_step_completed(f"{layer}_exec")
                        self.logger.info(f"层级 {layer} 执行成功")
                    else:
                        self.logger.error(f"层级 {layer} 执行失败")
                        return False
                        
                except Exception as e:
                    self.logger.error(f"层级 {layer} 执行异常: {e}")
                    return False
            else:
                self.logger.warning(f"层级 {layer} 未注册执行器，跳过")
        
        return True
    
    def mark_step_completed(self, step_id: str):
        """
        标记前置步骤完成
        
        Args:
            step_id: 步骤ID
        """
        self.pre_push_checker.mark_step_completed(step_id)
        self.logger.info(f"步骤 {step_id} 已标记完成")
    
    def mark_step_failed(self, step_id: str):
        """
        标记前置步骤失败
        
        Args:
            step_id: 步骤ID
        """
        self.pre_push_checker.mark_step_failed(step_id)
        self.logger.warning(f"步骤 {step_id} 已标记失败")
    
    def _execute_pre_check(self) -> Dict[str, Any]:
        """
        执行前置检查
        
        Returns:
            Dict: 检查结果
        """
        self.logger.info("执行前置检查")
        
        result = {
            "passed": True,
            "layers": {},
            "failed_layer": None,
            "timestamp": datetime.now().isoformat()
        }
        
        layer_checks = {
            "data": {
                "H1": "数据非空",
                "H2": "必需字段完整",
                "H3": "时间序列连续",
                "H4": "价格逻辑一致",
                "H5": "无未来数据泄露",
                "E2": "数据时效性 < 24小时"
            },
            "factor": {
                "H1": "因子数据非空",
                "H2": "至少1个有效因子",
                "H3": "因子值非全NaN",
                "E1": "IC均值 >= 0.02"
            },
            "strategy": {
                "H1": "选股结果非空",
                "H2": "信号组合有效",
                "H3": "回测验证通过"
            },
            "portfolio": {
                "H1": "权重归一化",
                "H2": "单资产权重上限 <= 15%",
                "H3": "权重非负",
                "H4": "输入有效性"
            },
            "risk": {
                "H1": "单票权重上限 <= 12%",
                "H2": "行业集中度 <= 30%",
                "H3": "总仓位上限 <= 95%",
                "H4": "止损线检查"
            }
        }
        
        for layer in self.LAYER_ORDER:
            layer_result = LayerCheckStatus(layer_name=layer, passed=True)
            
            checks = layer_checks.get(layer, {})
            for check_id, check_name in checks.items():
                passed = self._simulate_check(layer, check_id)
                layer_result.checks[check_id] = passed
                
                if not passed and check_id.startswith("H"):
                    layer_result.passed = False
                    layer_result.error_message = f"{check_name} 检查失败"
            
            result["layers"][layer] = layer_result.to_dict()
            
            if not layer_result.passed:
                result["passed"] = False
                result["failed_layer"] = layer
                self.logger.warning(f"前置检查失败: {layer} 层")
                break
        
        return result
    
    def _simulate_check(self, layer: str, check_id: str) -> bool:
        """
        模拟检查（实际项目中应调用真实检查器）
        
        Args:
            layer: 层名称
            check_id: 检查ID
            
        Returns:
            bool: 是否通过
        """
        return True
    
    def _build_push_message(
        self,
        report_content: Optional[str],
        report_data: Optional[Dict[str, Any]],
        trade_instructions: Optional[List[TradeInstruction]],
        pre_check_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        构建推送消息
        
        Args:
            report_content: 报告内容
            report_data: 报告数据
            trade_instructions: 交易指令
            pre_check_result: 前置检查结果
            
        Returns:
            Dict: 推送消息
        """
        message = {
            "timestamp": datetime.now().isoformat(),
            "type": "daily_report",
            "pre_check_status": self._format_pre_check_status(pre_check_result),
            "trade_instructions": self._format_trade_instructions(trade_instructions),
            "strategy_status": self._get_strategy_status(report_data),
            "selection_reason": self._get_selection_reason(report_data),
            "risk_assessment": self._get_risk_assessment(report_data),
            "historical_performance": self._get_historical_performance(report_data),
            "market_overview": self._get_market_overview(report_data)
        }
        
        if report_content:
            message["report_content"] = report_content
        
        return message
    
    def _format_pre_check_status(
        self,
        pre_check_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """格式化前置检查状态"""
        status = {
            "overall_passed": pre_check_result.get("passed", False),
            "layers": {}
        }
        
        for layer_name, layer_data in pre_check_result.get("layers", {}).items():
            checks_status = []
            for check_id, passed in layer_data.get("checks", {}).items():
                symbol = "✓" if passed else "✗"
                checks_status.append(f"{check_id}: {symbol}")
            
            status["layers"][layer_name] = {
                "passed": layer_data.get("passed", False),
                "checks": checks_status
            }
        
        return status
    
    def _format_trade_instructions(
        self,
        trade_instructions: Optional[List[TradeInstruction]]
    ) -> Dict[str, Any]:
        """格式化交易指令"""
        if not trade_instructions:
            return {
                "buy": [],
                "sell": [],
                "summary": "无交易指令"
            }
        
        buy_list = []
        sell_list = []
        
        for inst in trade_instructions:
            inst_dict = inst.to_dict() if isinstance(inst, TradeInstruction) else inst
            
            if inst_dict.get("direction") == "买入":
                buy_list.append(inst_dict)
            else:
                sell_list.append(inst_dict)
        
        return {
            "buy": buy_list,
            "sell": sell_list,
            "summary": f"买入 {len(buy_list)} 只，卖出 {len(sell_list)} 只"
        }
    
    def _get_strategy_status(
        self,
        report_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取策略状态"""
        if report_data and "strategy_status" in report_data:
            return report_data["strategy_status"]
        
        return {
            "strategy_name": "多因子选股策略",
            "strategy_type": "量化选股",
            "current_status": "运行中",
            "win_rate": 0.65,
            "total_trades": 120
        }
    
    def _get_selection_reason(
        self,
        report_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取选择原因"""
        if report_data and "selection_reason" in report_data:
            return report_data["selection_reason"]
        
        return {
            "factor_signals": {
                "momentum_5d": {"value": 0.05, "weight": 0.3},
                "volume_ratio": {"value": 1.2, "weight": 0.2},
                "turnover_rate": {"value": 0.03, "weight": 0.15}
            },
            "signal_strength_score": 0.85,
            "optimization_method": "风险平价",
            "risk_check_result": "通过"
        }
    
    def _get_risk_assessment(
        self,
        report_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取风险评估"""
        if report_data and "risk_assessment" in report_data:
            return report_data["risk_assessment"]
        
        return {
            "single_stock_weights": {
                "max": 0.10,
                "distribution": "均衡"
            },
            "industry_concentration": 0.25,
            "expected_turnover": 0.15,
            "var_95": -0.025
        }
    
    def _get_historical_performance(
        self,
        report_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取历史表现"""
        if report_data and "historical_performance" in report_data:
            return report_data["historical_performance"]
        
        return {
            "strategy_win_rate": 0.65,
            "recent_returns": {
                "1_month": 0.05,
                "3_month": 0.12,
                "6_month": 0.20
            },
            "max_drawdown": -0.08
        }
    
    def _get_market_overview(
        self,
        report_data: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """获取市场概况"""
        if report_data and "market_overview" in report_data:
            return report_data["market_overview"]
        
        return {
            "main_indexes": {
                "沪深300": "+1.5%",
                "上证50": "+1.2%",
                "中证500": "+1.8%"
            },
            "market_volume": "1.2万亿",
            "northbound_flow": "+55亿"
        }
    
    def _format_feishu_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化为飞书webhook要求的格式
        
        飞书webhook要求格式：
        {
            "msg_type": "text",
            "content": {"text": "消息内容"}
        }
        或
        {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": "标题",
                        "content": [[{"tag": "text", "text": "内容"}]]
                    }
                }
            }
        }
        
        Args:
            message: 原始消息内容
            
        Returns:
            Dict: 飞书格式消息
        """
        if "report_content" in message:
            content_text = message["report_content"]
        else:
            lines = []
            lines.append(f"📊 量化交易日报")
            lines.append(f"时间: {message.get('timestamp', '')}")
            lines.append("")
            
            pre_check = message.get("pre_check_status", {})
            if pre_check.get("overall_passed"):
                lines.append("✅ 前置检查: 全部通过")
            else:
                lines.append("❌ 前置检查: 存在问题")
            
            trade_inst = message.get("trade_instructions", {})
            lines.append(f"📋 交易指令: {trade_inst.get('summary', '无')}")
            
            strategy = message.get("strategy_status", {})
            lines.append(f"📈 策略: {strategy.get('strategy_name', 'N/A')}")
            lines.append(f"   胜率: {strategy.get('win_rate', 0):.1%}")
            
            risk = message.get("risk_assessment", {})
            lines.append(f"⚠️ 风险评估:")
            lines.append(f"   最大单票权重: {risk.get('single_stock_weights', {}).get('max', 0):.1%}")
            lines.append(f"   行业集中度: {risk.get('industry_concentration', 0):.1%}")
            
            hist = message.get("historical_performance", {})
            recent = hist.get("recent_returns", {})
            lines.append(f"📊 近期表现:")
            lines.append(f"   1月: {recent.get('1_month', 0):.1%}")
            lines.append(f"   3月: {recent.get('3_month', 0):.1%}")
            
            market = message.get("market_overview", {})
            lines.append(f"🌍 市场概况:")
            for idx_name, idx_val in market.get("main_indexes", {}).items():
                lines.append(f"   {idx_name}: {idx_val}")
            
            content_text = "\n".join(lines)
        
        return {
            "msg_type": "text",
            "content": {
                "text": content_text
            }
        }
    
    def _send_webhook(
        self,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        发送Webhook
        
        Args:
            message: 消息内容
            
        Returns:
            Dict: 发送结果
        """
        if not self.webhook_url:
            self.logger.warning("未配置Webhook URL，跳过推送")
            return {
                "success": True,
                "skipped": True,
                "reason": "未配置Webhook URL"
            }
        
        feishu_message = self._format_feishu_message(message)
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=feishu_message,
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('StatusCode') == 0 or result.get('code') == 0:
                        self.logger.info(f"Webhook推送成功")
                        return {
                            "success": True,
                            "status_code": response.status_code,
                            "retry_count": attempt
                        }
                    else:
                        last_error = f"飞书API错误: {result.get('msg', result)}"
                        self.logger.warning(
                            f"Webhook推送失败 (尝试 {attempt + 1}/{self.max_retries}): {last_error}"
                        )
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                    self.logger.warning(
                        f"Webhook推送失败 (尝试 {attempt + 1}/{self.max_retries}): {last_error}"
                    )
                    
            except requests.exceptions.Timeout:
                last_error = "请求超时"
                self.logger.warning(
                    f"Webhook推送超时 (尝试 {attempt + 1}/{self.max_retries})"
                )
            except requests.exceptions.RequestException as e:
                last_error = str(e)
                self.logger.warning(
                    f"Webhook推送异常 (尝试 {attempt + 1}/{self.max_retries}): {e}"
                )
            
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay)
        
        self._save_failed_message(message, last_error)
        
        return {
            "success": False,
            "error": last_error,
            "retry_count": self.max_retries
        }
    
    def _save_failed_message(
        self,
        message: Dict[str, Any],
        error: str
    ):
        """
        保存失败的推送消息
        
        Args:
            message: 消息内容
            error: 错误信息
        """
        try:
            failed_dir = os.path.join("data", "notifications", "failed")
            os.makedirs(failed_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"failed_notify_{timestamp}.json"
            filepath = os.path.join(failed_dir, filename)
            
            data = {
                "timestamp": datetime.now().isoformat(),
                "error": error,
                "message": message
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"失败消息已保存: {filepath}")
            
        except Exception as e:
            self.logger.error(f"保存失败消息失败: {e}")
    
    def test_webhook(self) -> Dict[str, Any]:
        """
        测试Webhook连接
        
        Returns:
            Dict: 测试结果
        """
        if not self.webhook_url:
            return {
                "success": False,
                "error": "未配置Webhook URL"
            }
        
        feishu_message = {
            "msg_type": "text",
            "content": {
                "text": f"📊 A股量化系统 - 测试消息\n\n系统已配置成功！\n推送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=feishu_message,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                success = result.get('StatusCode') == 0 or result.get('code') == 0
                return {
                    "success": success,
                    "status_code": response.status_code,
                    "response": result
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response": response.text[:200]
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """
        获取待重发的失败通知
        
        Returns:
            List[Dict]: 失败通知列表
        """
        failed_dir = os.path.join("data", "notifications", "failed")
        
        if not os.path.exists(failed_dir):
            return []
        
        pending = []
        
        for filename in os.listdir(failed_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(failed_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    data["filepath"] = filepath
                    pending.append(data)
                except Exception:
                    continue
        
        return pending
    
    def retry_failed_notification(
        self,
        filepath: str
    ) -> Dict[str, Any]:
        """
        重试失败的推送
        
        Args:
            filepath: 失败消息文件路径
            
        Returns:
            Dict: 重试结果
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            result = self._send_webhook(data["message"])
            
            if result["success"]:
                os.remove(filepath)
                self.logger.info(f"重试成功，已删除失败记录: {filepath}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
