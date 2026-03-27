#!/usr/bin/env python3
"""
交易系统测试

测试交易系统的核心功能:
- 订单管理
- 持仓管理
- 交易报告生成
- 手动成交录入
- 交易员确认
- 状态跟踪
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import unittest
from datetime import datetime
from core.trading.order import (
    OrderManager,
    OrderStatus,
    OrderSide,
    OrderType,
    TradeOrder,
)
from core.trading.position import (
    PositionManager,
    Position,
)
from core.trading.report import (
    TradeReportGenerator,
    ReportFormat,
    TradeReport,
)
from core.trading.manual_entry import (
    ManualEntry,
    TradeEntry,
)
from core.trading.confirmation import (
    TraderConfirmation,
    ConfirmationType,
    ConfirmationStatus,
)
from core.trading.status_tracker import (
    TradeStatusTracker,
    TradeStatus,
)
from core.trading.notifier import (
    TradeNotifier,
    NotificationChannel,
)


class TestOrderManager(unittest.TestCase):
    """订单管理测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = OrderManager({'data_root': self.temp_dir})
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_order(self):
        context = {'available_cash': 100000, 'available_quantity': 0}
        order = self.manager.create_order(
            stock_code='600519.SH',
            stock_name='贵州茅台',
            side=OrderSide.BUY,
            quantity=100,
            price=1800.0,
            order_type=OrderType.LIMIT,
            reason='测试订单',
            context=context
        )
        
        self.assertIsNotNone(order)
        self.assertEqual(order.stock_code, '600519.SH')
        self.assertEqual(order.quantity, 100)
        self.assertEqual(order.price, 1800.0)
        self.assertEqual(order.side, OrderSide.BUY)
    
    def test_fill_order(self):
        context = {'available_cash': 100000, 'available_quantity': 0}
        order = self.manager.create_order(
            stock_code='000001.SZ',
            stock_name='平安银行',
            side=OrderSide.BUY,
            quantity=1000,
            price=10.0,
            context=context
        )
        
        success = self.manager.fill_order(
            order_id=order.order_id,
            filled_quantity=1000,
            filled_price=10.05,
            commission=5.0,
            stamp_tax=0,
            transfer_fee=0.2
        )
        
        self.assertTrue(success)
        
        updated_order = self.manager.get_order(order.order_id)
        self.assertEqual(updated_order.status, OrderStatus.FILLED)
        self.assertEqual(updated_order.filled_quantity, 1000)
        self.assertEqual(updated_order.filled_price, 10.05)
    
    def test_cancel_order(self):
        context = {'available_cash': 100000, 'available_quantity': 1000}
        order = self.manager.create_order(
            stock_code='000002.SZ',
            stock_name='万科A',
            side=OrderSide.SELL,
            quantity=500,
            price=15.0,
            context=context
        )
        
        success = self.manager.cancel_order(order.order_id, '测试取消')
        
        self.assertTrue(success)
        
        updated_order = self.manager.get_order(order.order_id)
        self.assertEqual(updated_order.status, OrderStatus.CANCELLED)
    
    def test_get_active_orders(self):
        context = {'available_cash': 100000, 'available_quantity': 0}
        self.manager.create_order(
            stock_code='600000.SH',
            stock_name='浦发银行',
            side=OrderSide.BUY,
            quantity=100,
            price=10.0,
            context=context
        )
        
        active = self.manager.get_active_orders()
        self.assertGreater(len(active), 0)


class TestPositionManager(unittest.TestCase):
    """持仓管理测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.manager = PositionManager({'data_root': self.temp_dir, 'initial_capital': 1000000})
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_update_position_buy(self):
        success = self.manager.update_position_from_trade(
            stock_code='600519.SH',
            stock_name='贵州茅台',
            side='buy',
            quantity=100,
            price=1800.0,
            commission=54.0
        )
        
        self.assertTrue(success)
        
        position = self.manager.get_position('600519.SH')
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 100)
    
    def test_update_position_sell(self):
        self.manager.update_position_from_trade(
            stock_code='000001.SZ',
            stock_name='平安银行',
            side='buy',
            quantity=1000,
            price=10.0
        )
        
        success = self.manager.update_position_from_trade(
            stock_code='000001.SZ',
            stock_name='平安银行',
            side='sell',
            quantity=500,
            price=10.5,
            commission=5.0,
            stamp_tax=5.25
        )
        
        self.assertTrue(success)
        
        position = self.manager.get_position('000001.SZ')
        self.assertIsNotNone(position)
        self.assertEqual(position.quantity, 500)
    
    def test_get_portfolio_summary(self):
        self.manager.update_position_from_trade(
            stock_code='600519.SH',
            stock_name='贵州茅台',
            side='buy',
            quantity=100,
            price=1800.0
        )
        
        self.manager.update_prices({'600519.SH': 1850.0})
        
        summary = self.manager.get_portfolio_summary()
        
        self.assertIn('total_value', summary)
        self.assertIn('cash', summary)
        self.assertIn('position_count', summary)


class TestTradeReportGenerator(unittest.TestCase):
    """交易报告生成器测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = TradeReportGenerator({'data_root': self.temp_dir})
        self.order_manager = OrderManager({'data_root': self.temp_dir})
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_generate_report(self):
        context = {'available_cash': 1000000, 'available_quantity': 0}
        orders = [
            self.order_manager.create_order(
                stock_code='600519.SH',
                stock_name='贵州茅台',
                side=OrderSide.BUY,
                quantity=100,
                price=1800.0,
                signal_strength=0.85,
                confidence=0.9,
                reason='多因子信号',
                factors=['momentum', 'value'],
                context=context
            )
        ]
        
        portfolio_summary = {
            'total_value': 1000000,
            'cash': 500000,
            'weights': {}
        }
        
        report = self.generator.generate_report(
            orders=orders,
            portfolio_summary=portfolio_summary,
            strategy_name='测试策略'
        )
        
        self.assertIsNotNone(report)
        self.assertEqual(len(report.orders), 1)
        self.assertEqual(report.strategy_name, '测试策略')


class TestManualEntry(unittest.TestCase):
    """手动成交录入测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.entry_manager = ManualEntry({'data_root': self.temp_dir})
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_entry(self):
        entry = self.entry_manager.create_entry(
            stock_code='600519.SH',
            stock_name='贵州茅台',
            side='buy',
            quantity=100,
            price=1800.0,
            auto_calculate_fees=True
        )
        
        self.assertIsNotNone(entry)
        self.assertEqual(entry.stock_code, '600519.SH')
        self.assertEqual(entry.quantity, 100)
        self.assertEqual(entry.price, 1800.0)
        self.assertTrue(entry.validated)
    
    def test_get_entry_summary(self):
        self.entry_manager.create_entry(
            stock_code='000001.SZ',
            stock_name='平安银行',
            side='buy',
            quantity=1000,
            price=10.0
        )
        
        summary = self.entry_manager.get_entry_summary()
        
        self.assertIn('total_entries', summary)
        self.assertIn('total_buy_amount', summary)


class TestTraderConfirmation(unittest.TestCase):
    """交易员确认机制测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.confirmation_manager = TraderConfirmation({'data_root': self.temp_dir})
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_confirmation(self):
        confirmation = self.confirmation_manager.create_confirmation(
            report_id='TR-20240101-001',
            order_ids=['ORD-001', 'ORD-002'],
            timeout_minutes=30
        )
        
        self.assertIsNotNone(confirmation)
        self.assertEqual(confirmation.status, ConfirmationStatus.PENDING)
        self.assertEqual(len(confirmation.order_ids), 2)
    
    def test_confirm(self):
        confirmation = self.confirmation_manager.create_confirmation(
            report_id='TR-20240101-002',
            order_ids=['ORD-003']
        )
        
        result = self.confirmation_manager.confirm(
            confirmation_id=confirmation.confirmation_id,
            confirmation_type=ConfirmationType.EXECUTED,
            trader_id='trader_001',
            notes='已执行'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result.status, ConfirmationStatus.CONFIRMED)
        self.assertEqual(result.confirmation_type, ConfirmationType.EXECUTED)


class TestTradeStatusTracker(unittest.TestCase):
    """交易状态跟踪测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.tracker = TradeStatusTracker({'data_root': self.temp_dir})
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_start_tracking(self):
        info = self.tracker.start_tracking(
            order_id='ORD-TEST-001',
            stock_code='600519.SH',
            stock_name='贵州茅台',
            side='buy',
            quantity=100,
            price=1800.0
        )
        
        self.assertIsNotNone(info)
        self.assertEqual(info.current_status, TradeStatus.PENDING_PUSH)
    
    def test_update_status(self):
        self.tracker.start_tracking(
            order_id='ORD-TEST-002',
            stock_code='000001.SZ',
            stock_name='平安银行',
            side='sell',
            quantity=500
        )
        
        info = self.tracker.update_status(
            order_id='ORD-TEST-002',
            new_status=TradeStatus.PUSHED,
            changed_by='system'
        )
        
        self.assertIsNotNone(info)
        self.assertEqual(info.current_status, TradeStatus.PUSHED)
        self.assertIsNotNone(info.pushed_at)
    
    def test_get_execution_statistics(self):
        stats = self.tracker.get_execution_statistics()
        
        self.assertIn('total_orders', stats)
        self.assertIn('status_distribution', stats)
        self.assertIn('fill_rate', stats)


class TestTradeNotifier(unittest.TestCase):
    """交易报告推送测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.notifier = TradeNotifier({
            'data_root': self.temp_dir,
            'email': {'enabled': True, 'simulate': True, 'recipients': ['test@example.com']},
            'dingtalk': {'enabled': True, 'simulate': True}
        })
    
    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_push_report(self):
        report = TradeReport(
            report_id='TR-TEST-001',
            report_date='2024-01-01',
            generated_at=datetime.now().isoformat(),
            strategy_name='测试策略',
            account_info={'account_name': '测试账户'},
            orders=[],
            decision_basis={},
            risk_assessment={},
            historical_performance={},
            recommendations=['测试建议']
        )
        
        results = self.notifier.push_report(
            report=report,
            channels=[NotificationChannel.EMAIL],
            recipients={'email': ['test@example.com']}
        )
        
        self.assertIn('email', results)
        self.assertTrue(results['email'].success)
    
    def test_push_trade_alert(self):
        results = self.notifier.push_trade_alert(
            title='测试警报',
            message='这是一个测试警报',
            level='warning',
            channels=[NotificationChannel.EMAIL]
        )
        
        self.assertIn('email', results)
        self.assertTrue(results['email'].success)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestOrderManager))
    suite.addTests(loader.loadTestsFromTestCase(TestPositionManager))
    suite.addTests(loader.loadTestsFromTestCase(TestTradeReportGenerator))
    suite.addTests(loader.loadTestsFromTestCase(TestManualEntry))
    suite.addTests(loader.loadTestsFromTestCase(TestTraderConfirmation))
    suite.addTests(loader.loadTestsFromTestCase(TestTradeStatusTracker))
    suite.addTests(loader.loadTestsFromTestCase(TestTradeNotifier))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
