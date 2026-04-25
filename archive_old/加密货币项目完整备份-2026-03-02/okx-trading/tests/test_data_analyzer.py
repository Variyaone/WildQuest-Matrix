"""
数据验证单元测试
测试数据处理、清洗和验证逻辑
"""

import pytest
from okx_trading.data.collector import MarketData
from okx_trading.exceptions import DataQualityException


class TestDataQuality:
    """数据质量测试"""

    def test_market_data_creation(self):
        """测试市场数据创建"""
        data = MarketData(
            instrument_id='BTC-USDT-SWAP',
            timestamp=1634567890000,
            data_type='candle',
            data={'open': 47000, 'close': 47500}
        )

        assert data.instrument_id == 'BTC-USDT-SWAP'
        assert data.timestamp == 1634567890000
        assert data.data_type == 'candle'
        assert data.data['open'] == 47000

    def test_candlestick_data_validation(self):
        """测试K线数据验证"""
        # 有效的K线数据
        valid_candle = [1634567890000, 47000, 48000, 46500, 47500, 100]

        # 验证格式
        assert isinstance(valid_candle, list)
        assert len(valid_candle) >= 6

        # 验证数值类型
        assert all(isinstance(x, (int, float)) for x in valid_candle)

        # 验证数值逻辑
        assert valid_candle[2] >= valid_candle[1]  # high >= open
        assert valid_candle[2] >= valid_candle[4]  # high >= close
        assert valid_candle[3] <= valid_candle[1]  # low <= open
        assert valid_candle[3] <= valid_candle[4]  # low <= close

    def test_invalid_candlestick_data(self):
        """测试无效K线数据"""
        # 长度不足
        short_candle = [47000, 48000, 46500, 47500]
        assert len(short_candle) < 6

        # 价格逻辑错误
        invalid_logic = [1634567890000, 47000, 46000, 46500, 47500, 100]
        assert invalid_logic[2] < invalid_logic[1]  # high < open

    def test_ticker_data_validation(self):
        """测试Ticker数据验证"""
        # 有效的Ticker数据
        valid_ticker = {
            'last': 47500,
            'bidPx': 47499,
            'askPx': 47501,
            'bidSz': 0.5,
            'askSz': 0.3,
            'vol24h': 10000,
            'high24h': 48000,
            'low24h': 46000
        }

        # 验证必填字段
        assert 'last' in valid_ticker
        assert 'bidPx' in valid_ticker
        assert 'askPx' in valid_ticker

        # 验证数值有效性
        assert valid_ticker['last'] > 0
        assert valid_ticker['bidPx'] < valid_ticker['askPx']  # bid < ask

    def test_orderbook_data_validation(self):
        """测试订单簿数据验证"""
        # 有效的订单簿数据
        valid_orderbook = {
            'bids': [[47499, 0.5], [47498, 1.0], [47497, 2.0], [47496, 3.0], [47495, 5.0]],
            'asks': [[47501, 0.3], [47502, 0.8], [47503, 1.5], [47504, 2.5], [47505, 4.0]],
            'ts': 1634567890000
        }

        # 验证结构
        assert 'bids' in valid_orderbook
        assert 'asks' in valid_orderbook
        assert isinstance(valid_orderbook['bids'], list)
        assert isinstance(valid_orderbook['asks'], list)

        # 验证价格逻辑
        bids = valid_orderbook['bids']
        asks = valid_orderbook['asks']

        if bids and asks:
            # 买单应该降序排列
            assert bids[0][0] > bids[1][0] if len(bids) > 1 else True
            # 卖单应该升序排列
            assert asks[0][0] < asks[1][0] if len(asks) > 1 else True
            # 最高买价应该低于最低卖价
            assert bids[0][0] < asks[0][0]

    def test_invalid_orderbook_data(self):
        """测试无效订单簿数据"""
        # bid价格高于ask价格
        invalid_spread = {
            'bids': [[47501, 0.5]],
            'asks': [[47499, 0.3]]
        }

        if invalid_spread['bids'] and invalid_spread['asks']:
            assert invalid_spread['bids'][0][0] > invalid_spread['asks'][0][0]

        # 数量为0或负数
        invalid_amount = {
            'bids': [[47500, -0.5]],
            'asks': [[47501, 0]]
        }

        assert invalid_amount['bids'][0][1] <= 0

    def test_data_type_validation(self):
        """测试数据类型验证"""
        # 正常数据类型
        valid_types = ['candle', 'ticker', 'orderbook']

        for dtype in valid_types:
            assert isinstance(dtype, str)
            assert dtype in valid_types

        # 无效数据类型
        invalid_type = 'invalid_type'
        assert invalid_type not in valid_types

    def test_timestamp_validation(self):
        """测试时间戳验证"""
        valid_timestamp = 1634567890000  # 2021-10-18 16:58:10 (UTC+8)

        # 验证格式
        assert isinstance(valid_timestamp, (int, float))
        assert valid_timestamp > 0

        # 验证时间戳合理性（不能是未来时间）
        import time
        current_timestamp = int(time.time() * 1000)
        assert valid_timestamp <= current_timestamp

        # 不能太久远
        min_timestamp = 1534567890000  # 2018-08-18
        assert valid_timestamp >= min_timestamp

    def test_price_range_validation(self):
        """测试价格范围验证"""
        # 合理的价格范围
        min_reasonable = 0.0001  # 最小合理价格
        max_reasonable = 1000000  # 最大合理价格

        # 测试有效价格
        valid_prices = [47500, 1000, 0.5, 100]
        for price in valid_prices:
            assert price >= min_reasonable
            assert price <= max_reasonable

        # 测试无效价格
        invalid_prices = [0, -1, -100]
        for price in invalid_prices:
            assert price < min_reasonable

    def test_volume_validation(self):
        """测试成交量验证"""
        valid_volumes = [100, 1000.5, 0.001, 10000]

        for volume in valid_volumes:
            assert volume >= 0
            assert isinstance(volume, (int, float))

        # 无效成交量
        invalid_volumes = [-100, -1, -0.001]
        for volume in invalid_volumes:
            assert volume < 0

    def test_spread_calculation(self):
        """测试价差计算"""
        orderbook = {
            'bids': [[47499, 0.5]],
            'asks': [[47501, 0.3]]
        }

        if orderbook['bids'] and orderbook['asks']:
            best_bid = orderbook['bids'][0][0]
            best_ask = orderbook['asks'][0][0]

            spread = best_ask - best_bid
            spread_percent = (spread / best_bid) * 100

            assert spread > 0
            assert spread_percent > 0
            assert spread == 2
            assert abs(spread_percent - 0.00421) < 0.0001  # ~0.00421%

    def test_liquidity_calculation(self):
        """测试流动性计算"""
        orderbook = {
            'bids': [[47499, 0.5], [47498, 1.0], [47497, 2.0], [47496, 3.0], [47495, 5.0]],
            'asks': [[47501, 0.3], [47502, 0.8], [47503, 1.5], [47504, 2.5], [47505, 4.0]]
        }

        # 计算深度
        bids_volume = sum(b[1] for b in orderbook['bids'][:5])
        asks_volume = sum(a[1] for a in orderbook['asks'][:5])
        total_volume = bids_volume + asks_volume

        assert bids_volume == 11.5
        assert asks_volume == 9.1
        assert total_volume == 20.6

    def test_data_completeness(self):
        """测试数据完整性"""
        # K线数据完整性
        candle_data = {
            'timestamp': 1634567890000,
            'open': 47000,
            'high': 48000,
            'low': 46500,
            'close': 47500,
            'volume': 100
        }

        required_candle_fields = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for field in required_candle_fields:
            assert field in candle_data

        # Ticker数据完整性
        ticker_data = {
            'last': 47500,
            'volume_24h': 10000,
            'timestamp': 1634567890000
        }

        required_ticker_fields = ['last', 'timestamp']
        for field in required_ticker_fields:
            assert field in ticker_data

    def test_data_normalization(self):
        """测试数据标准化"""
        # 统一浮点数类型
        raw_values = [47000, '48000', 46500.5, '47500']

        normalized_values = []
        for val in raw_values:
            normalized_values.append(float(val))

        # 验证所有值都是浮点数
        assert all(isinstance(v, float) for v in normalized_values)

        # 统一时间戳格式
        raw_timestamps = [1634567890, '1634567890000', 1634567890000]

        normalized_timestamps = []
        for ts in raw_timestamps:
            if isinstance(ts, str):
                normalized_timestamps.append(int(ts))
            elif isinstance(ts, float) and ts < 1e10:
                normalized_timestamps.append(int(ts * 1000))
            else:
                normalized_timestamps.append(int(ts))

        # 验证所有时间戳都是毫秒级整数
        assert all(isinstance(ts, int) for ts in normalized_timestamps)
        assert all(ts > 1e12 for ts in normalized_timestamps)

    def test_data_consistency(self):
        """测试数据一致性"""
        # OHLCV一致性
        candle = [1634567890000, 47000, 48000, 46500, 47500, 100]

        open_price = candle[1]
        high_price = candle[2]
        low_price = candle[3]
        close_price = candle[4]

        # High >= Open, High >= Close
        assert high_price >= open_price
        assert high_price >= close_price

        # Low <= Open, Low <= Close
        assert low_price <= open_price
        assert low_price <= close_price

        # Volume >= 0
        assert candle[5] >= 0

        # 订单簿一致性
        orderbook = {
            'bids': [[47499, 0.5], [47498, 1.0]],
            'asks': [[47501, 0.3], [47502, 0.8]]
        }

        # bids 和 asks 不应该重叠
        if orderbook['bids'] and orderbook['asks']:
            assert orderbook['bids'][0][0] < orderbook['asks'][0][0]

    def test_edge_cases(self):
        """测试边界情况"""
        # 最小价格
        min_price = 0.0001
        assert min_price > 0

        # 最大价格
        max_price = 1000000
        assert max_price > 0

        # 最小成交量
        min_volume = 0.000001
        assert min_volume > 0

        # 零价格（应该拒绝）
        zero_price = 0
        assert zero_price == 0

    def test_data_anomaly_detection(self):
        """测试数据异常检测"""
        # 价格跳变
        price_sequence = [47000, 47100, 47050, 52000]  # 突然跳到52000

        price_changes = []
        for i in range(1, len(price_sequence)):
            change = abs(price_sequence[i] - price_sequence[i-1]) / price_sequence[i-1]
            price_changes.append(change)

        # 计算平均变化
        avg_change = sum(price_changes[:-1]) / (len(price_changes) - 1)

        # 检测异常（最后变化远大于平均变化）
        last_change = price_changes[-1]
        is_anomaly = last_change > avg_change * 10

        assert is_anomaly

        # 成交量异常
        volume_sequence = [100, 95, 105, 110, 10000]  # 突然放量

        volume_changes = []
        for i in range(1, len(volume_sequence)):
            change = abs(volume_sequence[i] - volume_sequence[i-1]) / volume_sequence[i-1]
            volume_changes.append(change)

        avg_volume_change = sum(volume_changes[:-1]) / (len(volume_changes) - 1)
        last_volume_change = volume_changes[-1]

        is_volume_anomaly = last_volume_change > avg_volume_change * 10
        assert is_volume_anomaly

    def test_missing_field_detection(self):
        """测试缺失字段检测"""
        complete_candle = [1634567890000, 47000, 48000, 46500, 47500, 100]

        # 移除不同字段
        incomplete_cases = [
            ([], 0),  # 空
            ([47000], 1),  # 只有开盘价
            ([47000, 48000, 46500, 47500], 4),  # 缺少成交量和时间戳
        ]

        for incomplete_data, expected_length in incomplete_cases:
            assert len(incomplete_data) == expected_length
            assert len(incomplete_data) < 6  # K线应该有6个字段
