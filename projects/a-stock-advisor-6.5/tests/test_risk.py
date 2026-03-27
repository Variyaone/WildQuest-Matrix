"""
风控系统测试

测试风控系统的各个模块功能。
"""

import pytest
import numpy as np
from datetime import datetime, date, timedelta
from unittest.mock import Mock, patch

from core.risk import (
    RiskLimits,
    HardLimits,
    SoftLimits,
    AlertThresholds,
    StopLossConfig,
    BlacklistConfig,
    RiskLevel,
    LimitType,
    RiskMetricsCalculator,
    RiskMetricsResult,
    calculate_portfolio_concentration,
    calculate_position_usage,
    PreTradeRiskChecker,
    PreTradeCheckResult,
    TradeInstruction,
    PortfolioState,
    create_portfolio_state,
    CheckResult,
    Violation,
    IntradayRiskMonitor,
    IntradayAlert,
    PortfolioRiskSnapshot,
    MonitorStatus,
    AlertAction,
    PostTradeAnalyzer,
    PostTradeAnalysis,
    TradeRecord,
    PositionRecord,
    RiskAlertManager,
    AlertMessage,
    AlertType,
    AlertChannel,
    LogAlertHandler,
    RiskReportGenerator,
    RiskReport,
    ReportFormat,
    ReportType,
    ReportFormatter,
    get_risk_limits,
    set_risk_limits,
    reset_risk_limits
)


class TestRiskLimits:
    """测试风控限制配置"""
    
    def test_hard_limits_default_values(self):
        """测试硬性限制默认值"""
        limits = HardLimits()
        
        assert limits.max_single_stock_weight == 0.12
        assert limits.max_industry_concentration == 0.30
        assert limits.max_total_position == 0.95
        assert limits.max_drawdown == 0.15
        assert limits.min_stock_count == 5
        assert limits.max_stock_count == 20
    
    def test_hard_limits_validation(self):
        """测试硬性限制验证"""
        limits = HardLimits(max_single_stock_weight=1.5)
        errors = limits.validate()
        assert len(errors) > 0
        assert "单票权重上限" in errors[0]
    
    def test_soft_limits_default_values(self):
        """测试弹性限制默认值"""
        limits = SoftLimits()
        
        assert limits.ideal_stock_count_range == (5, 20)
        assert limits.max_turnover_rate == 0.20
        assert limits.min_turnover_amount == 10_000_000.0
    
    def test_blacklist_config(self):
        """测试黑名单配置"""
        config = BlacklistConfig()
        
        config.add_to_blacklist("000001.SZ")
        assert config.is_stock_blocked("000001.SZ")
        assert not config.is_stock_blocked("000002.SZ")
        
        config.remove_from_blacklist("000001.SZ")
        assert not config.is_stock_blocked("000001.SZ")
    
    def test_risk_limits_validation(self):
        """测试完整风控限制验证"""
        limits = RiskLimits()
        errors = limits.validate_all()
        
        assert len(errors) == 0
    
    def test_risk_limits_to_dict(self):
        """测试风控限制序列化"""
        limits = RiskLimits()
        d = limits.to_dict()
        
        assert "hard_limits" in d
        assert "soft_limits" in d
        assert "alert_thresholds" in d
    
    def test_risk_limits_from_dict(self):
        """测试风控限制反序列化"""
        config_dict = {
            "hard_limits": {
                "max_single_stock_weight": 0.10,
                "max_industry_concentration": 0.25
            }
        }
        
        limits = RiskLimits.from_dict(config_dict)
        
        assert limits.hard_limits.max_single_stock_weight == 0.10
        assert limits.hard_limits.max_industry_concentration == 0.25


class TestRiskMetrics:
    """测试风险指标计算"""
    
    def test_calculate_var(self):
        """测试VaR计算"""
        calculator = RiskMetricsCalculator()
        returns = np.array([-0.05, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05])
        
        var_95 = calculator.calculate_var(returns, 0.95)
        var_99 = calculator.calculate_var(returns, 0.99)
        
        assert var_95 > 0
        assert var_99 >= var_95
    
    def test_calculate_cvar(self):
        """测试CVaR计算"""
        calculator = RiskMetricsCalculator()
        returns = np.array([-0.05, -0.03, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03, 0.04, 0.05])
        
        cvar_95 = calculator.calculate_cvar(returns, 0.95)
        
        assert cvar_95 > 0
    
    def test_calculate_max_drawdown(self):
        """测试最大回撤计算"""
        calculator = RiskMetricsCalculator()
        nav_series = np.array([1.0, 1.1, 1.05, 0.95, 0.90, 0.92, 1.0, 1.05])
        
        max_dd, current_dd, start_idx, end_idx = calculator.calculate_max_drawdown(nav_series)
        
        assert max_dd > 0
        assert max_dd <= 1
        assert current_dd >= 0
    
    def test_calculate_volatility(self):
        """测试波动率计算"""
        calculator = RiskMetricsCalculator()
        returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01])
        
        vol = calculator.calculate_volatility(returns, annualize=False)
        annualized_vol = calculator.calculate_volatility(returns, annualize=True)
        
        assert vol > 0
        assert annualized_vol > vol
    
    def test_calculate_beta(self):
        """测试Beta计算"""
        calculator = RiskMetricsCalculator()
        portfolio_returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.02, -0.01])
        
        beta = calculator.calculate_beta(portfolio_returns, benchmark_returns)
        
        assert isinstance(beta, float)
    
    def test_calculate_sharpe_ratio(self):
        """测试夏普比率计算"""
        calculator = RiskMetricsCalculator()
        returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01])
        
        sharpe = calculator.calculate_sharpe_ratio(returns)
        
        assert isinstance(sharpe, float)
    
    def test_calculate_all_metrics(self):
        """测试计算所有指标"""
        calculator = RiskMetricsCalculator()
        returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01])
        nav_series = np.array([1.0, 1.01, 1.03, 1.02, 1.05, 1.03, 1.04, 1.06, 1.05])
        
        result = calculator.calculate_all_metrics(returns, nav_series)
        
        assert isinstance(result, RiskMetricsResult)
        assert result.var_95 > 0
        assert result.max_drawdown >= 0
        assert result.volatility > 0
    
    def test_calculate_portfolio_concentration(self):
        """测试组合集中度计算"""
        weights = {"000001.SZ": 0.15, "000002.SZ": 0.12, "600000.SH": 0.10}
        industry_mapping = {"000001.SZ": "银行", "000002.SZ": "房地产", "600000.SH": "银行"}
        
        result = calculate_portfolio_concentration(weights, industry_mapping)
        
        assert result["max_single_weight"] == 0.15
        assert "银行" in result["industry_concentration"]
        assert result["industry_concentration"]["银行"] == 0.25
        assert result["effective_stocks"] > 0
    
    def test_calculate_position_usage(self):
        """测试仓位使用计算"""
        positions = {"000001.SZ": 150000, "000002.SZ": 120000}
        total_capital = 1000000
        
        result = calculate_position_usage(positions, total_capital)
        
        assert result["total_position"] == 270000
        assert result["position_ratio"] == 0.27
        assert result["cash_ratio"] == 0.73


class TestPreTradeRisk:
    """测试事前风控"""
    
    def test_create_portfolio_state(self):
        """测试创建组合状态"""
        positions = {"000001.SZ": 150000, "000002.SZ": 120000}
        industry_mapping = {"000001.SZ": "银行", "000002.SZ": "房地产"}
        
        state = create_portfolio_state(
            total_capital=1000000,
            positions=positions,
            industry_mapping=industry_mapping
        )
        
        assert state.total_capital == 1000000
        assert len(state.positions) == 2
        assert state.weights["000001.SZ"] == 0.15
    
    def test_pre_trade_check_pass(self):
        """测试事前检查通过"""
        checker = PreTradeRiskChecker()
        
        positions = {
            "000001.SZ": 100000,
            "000002.SZ": 100000,
            "000003.SZ": 100000,
            "000004.SZ": 100000,
            "000005.SZ": 100000
        }
        industry_mapping = {
            "000001.SZ": "银行",
            "000002.SZ": "房地产",
            "000003.SZ": "医药",
            "000004.SZ": "科技",
            "000005.SZ": "消费"
        }
        
        portfolio_state = create_portfolio_state(
            total_capital=1000000,
            positions=positions,
            industry_mapping=industry_mapping
        )
        
        instruction = TradeInstruction(
            stock_code="600000.SH",
            direction="buy",
            quantity=1000,
            price=10.0,
            amount=10000
        )
        
        result = checker.check([instruction], portfolio_state)
        
        assert result.passed
        assert result.result == CheckResult.PASS
        assert len(result.violations) == 0
    
    def test_pre_trade_check_reject_single_weight(self):
        """测试事前检查拒绝 - 单票权重超限"""
        checker = PreTradeRiskChecker()
        
        positions = {"000001.SZ": 50000}
        industry_mapping = {"000001.SZ": "银行"}
        
        portfolio_state = create_portfolio_state(
            total_capital=100000,
            positions=positions,
            industry_mapping=industry_mapping
        )
        
        instruction = TradeInstruction(
            stock_code="000001.SZ",
            direction="buy",
            quantity=10000,
            price=10.0,
            amount=100000
        )
        
        result = checker.check([instruction], portfolio_state)
        
        assert not result.passed
        assert result.result == CheckResult.REJECT
        assert len(result.violations) > 0
    
    def test_pre_trade_check_blacklist(self):
        """测试黑名单检查"""
        limits = RiskLimits()
        limits.blacklist.add_to_blacklist("000001.SZ")
        checker = PreTradeRiskChecker(limits)
        
        positions = {}
        industry_mapping = {}
        
        portfolio_state = create_portfolio_state(
            total_capital=1000000,
            positions=positions,
            industry_mapping=industry_mapping
        )
        
        instruction = TradeInstruction(
            stock_code="000001.SZ",
            direction="buy",
            quantity=1000,
            price=10.0,
            amount=10000
        )
        
        result = checker.check([instruction], portfolio_state)
        
        assert not result.passed
        assert any(v.rule_id == "H5" for v in result.violations)
    
    def test_quick_check(self):
        """测试快速检查"""
        checker = PreTradeRiskChecker()
        
        positions = {"000001.SZ": 100000}
        industry_mapping = {"000001.SZ": "银行"}
        
        portfolio_state = create_portfolio_state(
            total_capital=1000000,
            positions=positions,
            industry_mapping=industry_mapping
        )
        
        passed, message = checker.quick_check(
            stock_code="000002.SZ",
            direction="buy",
            amount=100000,
            portfolio_state=portfolio_state
        )
        
        assert isinstance(passed, bool)
        assert isinstance(message, str)


class TestIntradayRisk:
    """测试事中风控"""
    
    def test_intraday_monitor_update(self):
        """测试盘中监控更新"""
        monitor = IntradayRiskMonitor()
        
        positions = {
            "000001.SZ": {"quantity": 1000, "cost_price": 10.0, "day_cost": 10.0}
        }
        prices = {"000001.SZ": 10.5}
        industry_mapping = {"000001.SZ": "银行"}
        
        snapshot = monitor.update(
            positions=positions,
            prices=prices,
            total_capital=100000,
            industry_mapping=industry_mapping
        )
        
        assert isinstance(snapshot, PortfolioRiskSnapshot)
        assert snapshot.total_capital == 100000
        assert len(snapshot.position_risks) == 1
        assert "000001.SZ" in snapshot.position_risks
    
    def test_intraday_alert_generation(self):
        """测试盘中预警生成"""
        limits = RiskLimits()
        limits.alert_thresholds.drawdown_warning = 0.05
        monitor = IntradayRiskMonitor(limits)
        
        positions = {
            "000001.SZ": {"quantity": 1000, "cost_price": 10.0, "day_cost": 10.0}
        }
        prices = {"000001.SZ": 9.0}
        
        historical_returns = np.array([-0.05, -0.03, -0.02, -0.01, 0.0])
        historical_nav = np.array([1.0, 0.95, 0.92, 0.90, 0.88, 0.85])
        
        snapshot = monitor.update(
            positions=positions,
            prices=prices,
            total_capital=100000,
            historical_returns=historical_returns,
            historical_nav=historical_nav
        )
        
        alerts = monitor.get_active_alerts()
        
        assert isinstance(alerts, list)
    
    def test_stop_loss_check(self):
        """测试止损检查"""
        limits = RiskLimits()
        limits.stop_loss.enabled = True
        limits.stop_loss.individual_stop_loss = 0.08
        monitor = IntradayRiskMonitor(limits)
        
        positions = {
            "000001.SZ": {"quantity": 1000, "cost_price": 10.0}
        }
        prices = {"000001.SZ": 9.0}
        
        triggers = monitor.check_stop_loss(positions, prices)
        
        assert isinstance(triggers, list)
    
    def test_get_summary(self):
        """测试获取监控摘要"""
        monitor = IntradayRiskMonitor()
        
        summary = monitor.get_summary()
        
        assert "status" in summary
        assert "total_alerts" in summary


class TestPostTradeRisk:
    """测试事后风控"""
    
    def test_post_trade_analysis(self):
        """测试事后分析"""
        analyzer = PostTradeAnalyzer()
        
        nav_series = np.array([1.0, 1.01, 1.03, 1.02, 1.05, 1.03, 1.04, 1.06, 1.05, 1.07])
        returns = np.array([0.01, 0.02, -0.01, 0.03, -0.02, 0.01, 0.02, -0.01, 0.02])
        benchmark_returns = np.array([0.005, 0.015, -0.005, 0.02, -0.01, 0.005, 0.015, -0.005, 0.015])
        
        analysis = analyzer.analyze(
            nav_series=nav_series,
            returns=returns,
            benchmark_returns=benchmark_returns
        )
        
        assert isinstance(analysis, PostTradeAnalysis)
        assert analysis.total_return > 0
        assert analysis.risk_metrics is not None
    
    def test_generate_summary_report(self):
        """测试生成摘要报告"""
        analyzer = PostTradeAnalyzer()
        
        nav_series = np.array([1.0, 1.01, 1.03, 1.02, 1.05])
        returns = np.array([0.01, 0.02, -0.01, 0.03])
        
        analysis = analyzer.analyze(nav_series=nav_series, returns=returns)
        
        report = analyzer.generate_summary_report(analysis)
        
        assert isinstance(report, str)
        assert "事后风控分析报告" in report


class TestRiskAlert:
    """测试风险预警"""
    
    def test_create_alert(self):
        """测试创建预警"""
        manager = RiskAlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.DRAWDOWN,
            risk_level=RiskLevel.HIGH,
            title="回撤预警",
            message="当前回撤达到10%"
        )
        
        assert isinstance(alert, AlertMessage)
        assert alert.alert_type == AlertType.DRAWDOWN
        assert alert.risk_level == RiskLevel.HIGH
    
    def test_send_alert(self):
        """测试发送预警"""
        manager = RiskAlertManager(handlers=[LogAlertHandler()])
        
        alert = manager.create_alert(
            alert_type=AlertType.DRAWDOWN,
            risk_level=RiskLevel.HIGH,
            title="测试预警",
            message="测试消息"
        )
        
        result = manager.send_alert(alert)
        
        assert result is True
    
    def test_acknowledge_alert(self):
        """测试确认预警"""
        manager = RiskAlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.DRAWDOWN,
            risk_level=RiskLevel.HIGH,
            title="测试预警",
            message="测试消息"
        )
        
        manager.send_alert(alert)
        
        result = manager.acknowledge_alert(alert.alert_id, "test_user")
        
        assert result is True
        assert alert.acknowledged
        assert alert.acknowledged_by == "test_user"
    
    def test_check_and_alert(self):
        """测试检查并生成预警"""
        manager = RiskAlertManager()
        
        alerts = manager.check_and_alert(
            current_drawdown=0.12,
            industry_concentration={"银行": 0.28},
            single_stock_weights={"000001.SZ": 0.11}
        )
        
        assert isinstance(alerts, list)
    
    def test_get_alert_summary(self):
        """测试获取预警摘要"""
        manager = RiskAlertManager()
        
        alert = manager.create_alert(
            alert_type=AlertType.DRAWDOWN,
            risk_level=RiskLevel.HIGH,
            title="测试预警",
            message="测试消息"
        )
        manager.send_alert(alert)
        
        summary = manager.get_alert_summary()
        
        assert "total_alerts" in summary
        assert "unacknowledged" in summary
        assert "by_level" in summary


class TestRiskReport:
    """测试风险报告"""
    
    def test_generate_daily_report(self):
        """测试生成日报"""
        generator = RiskReportGenerator()
        
        report = generator.generate_daily_report()
        
        assert isinstance(report, RiskReport)
        assert report.report_type == ReportType.DAILY
        assert len(report.sections) > 0
    
    def test_generate_daily_report_with_data(self):
        """测试生成带数据的日报"""
        generator = RiskReportGenerator()
        
        risk_metrics = RiskMetricsResult(
            max_drawdown=0.10,
            current_drawdown=0.05,
            annualized_volatility=0.15,
            var_95=0.02,
            sharpe_ratio=1.5
        )
        
        report = generator.generate_daily_report(risk_metrics=risk_metrics)
        
        assert "风险指标" in report.sections
        assert report.risk_metrics is not None
    
    def test_generate_incident_report(self):
        """测试生成事件报告"""
        generator = RiskReportGenerator()
        
        report = generator.generate_incident_report(
            incident_type="stop_loss",
            incident_description="触发止损",
            affected_stocks=["000001.SZ"]
        )
        
        assert isinstance(report, RiskReport)
        assert report.report_type == ReportType.INCIDENT
        assert "事件信息" in report.sections
    
    def test_report_formatter_text(self):
        """测试报告文本格式化"""
        generator = RiskReportGenerator()
        report = generator.generate_daily_report()
        
        text = ReportFormatter.to_text(report)
        
        assert isinstance(text, str)
        assert "风险日报" in text
    
    def test_report_formatter_json(self):
        """测试报告JSON格式化"""
        generator = RiskReportGenerator()
        report = generator.generate_daily_report()
        
        json_str = ReportFormatter.to_json(report)
        
        assert isinstance(json_str, str)
        assert "report_id" in json_str
    
    def test_report_formatter_markdown(self):
        """测试报告Markdown格式化"""
        generator = RiskReportGenerator()
        report = generator.generate_daily_report()
        
        md = ReportFormatter.to_markdown(report)
        
        assert isinstance(md, str)
        assert "# " in md
    
    def test_report_formatter_html(self):
        """测试报告HTML格式化"""
        generator = RiskReportGenerator()
        report = generator.generate_daily_report()
        
        html = ReportFormatter.to_html(report)
        
        assert isinstance(html, str)
        assert "<!DOCTYPE html>" in html


class TestGlobalFunctions:
    """测试全局函数"""
    
    def test_get_set_risk_limits(self):
        """测试获取和设置风控限制"""
        reset_risk_limits()
        
        limits1 = get_risk_limits()
        assert isinstance(limits1, RiskLimits)
        
        new_limits = RiskLimits()
        new_limits.hard_limits.max_single_stock_weight = 0.15
        set_risk_limits(new_limits)
        
        limits2 = get_risk_limits()
        assert limits2.hard_limits.max_single_stock_weight == 0.15
        
        reset_risk_limits()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
