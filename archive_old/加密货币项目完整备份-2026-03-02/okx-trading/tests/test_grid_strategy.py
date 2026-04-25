"""
网格策略单元测试
测试网格策略的核心逻辑、价格突破检测和区间扩展
"""

import pytest
import time
from okx_trading.strategy.grid import GridStrategy
from okx_trading.strategy.base import Signal


class TestGridStrategy:
    """网格策略测试"""

    @pytest.fixture
    def grid_config(self):
        """网格策略配置"""
        return {
            'instrument_id': 'BTC-USDT-SWAP',
            'upper_price': 50000,
            'lower_price': 45000,
            'grid_count': 10,
            'grid_amount': 100,
            'position_side': 'long',
            'breakout_threshold': 10.0,
            'expand_percent': 5.0,
            'extreme_breakdown_threshold': 15.0
        }

    @pytest.fixture
    def strategy(self, grid_config):
        """创建策略实例"""
        strategy = GridStrategy('test_grid', grid_config)
        strategy.initialize()
        return strategy

    def test_initialization(self, strategy, grid_config):
        """测试策略初始化"""
        assert strategy.is_initialized
        assert strategy.instrument_id == grid_config['instrument_id']
        assert strategy.upper_price == grid_config['upper_price']
        assert strategy.lower_price == grid_config['lower_price']
        assert strategy.grid_count == grid_config['grid_count']
        assert strategy.current_size == 0.0
        assert strategy.realized_pnl == 0.0

    def test_grid_levels_calculation(self, strategy):
        """测试网格层级计算"""
        assert len(strategy.grid_levels) == strategy.grid_count + 1

        # 检查第一个网格
        first_level = strategy.grid_levels[0]
        assert first_level['index'] == 0
        assert first_level['price'] == strategy.lower_price
        assert first_level['amount'] > 0

        # 检查最后一个网格
        last_level = strategy.grid_levels[-1]
        assert last_level['index'] == strategy.grid_count
        assert last_level['price'] == strategy.upper_price

        # 检查网格间距
        expected_size = (strategy.upper_price - strategy.lower_price) / strategy.grid_count
        assert abs(strategy.grid_size - expected_size) < 0.01

    def test_price_extraction(self, strategy):
        """测试价格提取"""
        # 测试从price字段提取
        data1 = {'price': 47500}
        assert strategy._extract_price(data1) == 47500

        # 测试从last字段提取
        data2 = {'last': 48000}
        assert strategy._extract_price(data2) == 48000

        # 测试从candle数组提取
        data3 = {'candle': [1634567890000, 47000, 48000, 46500, 47500, 100]}
        assert strategy._extract_price(data3) == 47500

        # 测试从candle字典提取
        data4 = {'candle': {'close': 47550}}
        assert strategy._extract_price(data4) == 47550

        # 测试无效数据
        data5 = {'invalid': 'data'}
        assert strategy._extract_price(data5) is None

    def test_long_grid_buy_signal(self, strategy):
        """测试做多网格买入信号"""
        # 价格跌到网格线
        current_price = 45500
        strategy.grid_orders.clear()

        signal = strategy._check_long_grid(current_price)

        assert signal is not None
        assert signal.signal_type == 'buy'
        assert signal.amount > 0
        assert '跌破网格' in signal.reason

        # 网格订单应该被记录
        assert len(strategy.grid_orders) > 0

    def test_long_grid_sell_signal(self, strategy):
        """测试做多网格卖出信号"""
        # 先添加一个买入订单
        strategy.grid_orders[0] = {
            'type': 'buy',
            'price': 45000,
            'amount': 0.002,
            'timestamp': int(time.time())
        }

        # 价格涨到下一个网格
        current_price = 45500
        signal = strategy._check_long_grid(current_price)

        assert signal is not None
        assert signal.signal_type == 'sell'
        assert '涨破网格' in signal.reason

        # 买入订单应该被移除
        assert 0 not in strategy.grid_orders

    def test_price_breakout_detection(self, strategy, grid_config):
        """测试价格突破检测"""
        # 测试向上突破（未达到极端阈值）
        upper_breakout_price = strategy.initial_upper * 1.12  # 突破12%
        signal = strategy._check_price_breakout(upper_breakout_price)

        # 应该触发扩展信号
        assert signal is not None
        assert signal.signal_type == 'info'
        assert 'range_expansion' in signal.metadata.get('type', '')

        # 检查区间是否扩展
        assert strategy.upper_price > strategy.initial_upper
        assert strategy.breakout_count > 0

    def test_extreme_breakdown_stop_loss(self, strategy, grid_config):
        """测试极端突破止损"""
        # 设置持仓
        strategy.current_size = 0.001

        # 测试极端向下突破
        extreme_breakdown_price = strategy.initial_lower * 0.85  # 突破15%
        signal = strategy._check_price_breakout(extreme_breakdown_price)

        # 应该触发止损信号
        assert signal is not None
        assert signal.signal_type == 'sell'
        assert 'extreme_breakout_stop_loss' in signal.metadata.get('type', '')
        assert '止损' in signal.reason

    def test_range_expansion(self, strategy):
        """测试区间扩展"""
        old_upper = strategy.upper_price
        old_lower = strategy.lower_price

        # 向上扩展
        current_time = int(time.time()) - 4000  # 确保不在冷却中
        signal = strategy._expand_range('up', old_upper * 1.12)

        assert signal is not None
        assert strategy.upper_price > old_upper
        assert strategy.lower_price == old_lower
        assert strategy.breakout_count > 0

        # 向下扩展
        time.sleep(1)  # 确保不在冷却中
        strategy.last_expand_time = 0
        signal = strategy._expand_range('down', strategy.lower_price * 0.9)

        assert signal is not None
        assert strategy.lower_price < old_lower
        assert strategy.breakout_count > 1

        # 测试扩展限制
        strategy.breakout_count = strategy.max_expand_count + 1
        signal = strategy._expand_range('up', strategy.upper_price * 1.2)
        assert signal is None  # 达到最大扩展次数

    def test_expand_cooldown(self, strategy):
        """测试扩展冷却"""
        # 刚扩展过
        strategy.last_expand_time = int(time.time())
        strategy.breakout_count = 1

        # 在冷却期内不应该扩展
        signal = strategy._check_price_breakout(strategy.initial_upper * 1.12)
        assert signal is None or signal.signal_type != 'info'

    def test_order_filled_update(self, strategy):
        """测试订单成交更新"""
        initial_size = strategy.current_size
        initial_value = strategy.current_value

        # 买入成交
        order = {
            'instrument_id': strategy.instrument_id,
            'side': 'buy',
            'filled_amount': 0.001,
            'price': 47000
        }
        strategy.on_order_filled(order)

        assert strategy.current_size > initial_size
        assert strategy.current_value > initial_value

        # 卖出成交
        order = {
            'instrument_id': strategy.instrument_id,
            'side': 'sell',
            'filled_amount': 0.0005,
            'price': 47500
        }
        strategy.on_order_filled(order)

        assert strategy.current_size < initial_size + 0.001

    def test_out_of_range_price(self, strategy):
        """测试区间外价格处理"""
        # 价格高于上轨
        high_price = strategy.upper_price * 1.1
        signal = strategy._check_grid_triggers(high_price)
        assert signal is None

        # 价格低于下轨
        low_price = strategy.lower_price * 0.9
        signal = strategy._check_grid_triggers(low_price)
        assert signal is None

    def test_shortcode_grid(self, grid_config):
        """测试做空网格策略"""
        grid_config['position_side'] = 'short'
        strategy = GridStrategy('test_short_grid', grid_config)
        strategy.initialize()

        # 价格涨到网格线（卖出开空）
        high_price = 48000
        signal = strategy._check_short_grid(high_price)
        assert signal is not None
        assert signal.signal_type == 'sell'
        assert '开空单' in signal.reason

        # 设置空仓
        strategy.current_size = -0.001
        strategy.grid_orders[8] = {
            'type': 'sell',
            'price': 49000,
            'amount': 0.001,
            'timestamp': int(time.time())
        }

        # 价格跌到网格线（买入平空）
        low_price = 48500
        signal = strategy._check_short_grid(low_price)
        assert signal is not None
        assert signal.signal_type == 'buy'
        assert '平空单' in signal.reason

    def test_get_stats(self, strategy):
        """测试获取统计信息"""
        strategy.realized_pnl = 100.5
        stats = strategy.get_stats()

        assert 'grid_count' in stats
        assert 'grid_profit_percent' in stats
        assert 'realized_pnl' in stats
        assert 'price_range' in stats
        assert 'breakout_count' in stats

        assert stats['realized_pnl'] == 100.5
        assert 'initial_range' in stats

    def test_reset(self, strategy):
        """测试重置策略"""
        strategy.current_size = 0.001
        strategy.realized_pnl = 100.0
        strategy.breakout_count = 2
        strategy.grid_orders[0] = {'type': 'buy', 'price': 45000, 'amount': 0.002}

        strategy.reset()

        assert strategy.current_size == 0.0
        assert strategy.current_value == 0.0
        assert strategy.realized_pnl == 0.0
        assert strategy.breakout_count == 0
        assert len(strategy.grid_orders) == 0
        assert strategy.upper_price == strategy.initial_upper

    def test_on_data_flow(self, strategy):
        """测试on_data完整流程"""
        # 模拟K线数据
        data = {
            'candle': [1634567890000, 47000, 48000, 46500, 47500, 100],
            'instrument_id': 'BTC-USDT-SWAP'
        }

        strategy.grid_orders.clear()

        # 处理数据
        signal = strategy.on_data(data)

        # 数据应该被缓存
        assert len(strategy.data_cache) > 0

        # 可能生成买入信号（基于价格）
        if signal:
            assert signal.signal_type in ['buy', 'sell', 'info', None]

    def test_validation_config(self, strategy):
        """测试配置验证"""
        # 测试无效配置
        invalid_config = {
            'instrument_id': 'BTC-USDT-SWAP',
            'upper_price': 45000,  # 低于下轨
            'lower_price': 50000,
            'grid_count': 10,
            'grid_amount': 100
        }
        invalid_strategy = GridStrategy('invalid', invalid_config)
        assert not invalid_strategy.initialize()

        # 测试网格数量不足
        invalid_config2 = {
            'instrument_id': 'BTC-USDT-SWAP',
            'upper_price': 50000,
            'lower_price': 45000,
            'grid_count': 1,  # 小于2
            'grid_amount': 100
        }
        invalid_strategy2 = GridStrategy('invalid2', invalid_config2)
        assert not invalid_strategy2.initialize()
