"""
风险管理模块
仓位控制、止损止盈、保证金监控
包含基于真实API数据的市场风险评估
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import ccxt

from ..exceptions import APIException, RiskException, DataQualityException, retry_on_exception

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskCheckResult:
    """风险检查结果"""
    passed: bool
    level: RiskLevel
    message: str
    details: Dict[str, Any] = None


class RiskManager:
    """
    风险管理器
    控制仓位大小、执行止损止盈、监控保证金
    包含基于真实API的市场数据获取和分析
    """

    def __init__(self, config: Dict[str, Any], exchange: ccxt.Exchange = None):
        """
        初始化风险管理器

        Args:
            config: 风险配置
                - max_position_value: 单仓最大价值
                - max_total_value: 总持仓最大价值
                - stop_loss_percent: 止损百分比
                - take_profit_percent: 止盈百分比
                - max_leverage: 最大杠杆倍数
                - margin_usage_threshold: 保证金使用率阈值
            exchange: CCXT交易所实例（用于获取真实市场数据）
        """
        self.config = config
        self.exchange = exchange
        self.positions: Dict[str, Dict] = {}

        # 风险参数
        self.max_position_value = config.get('max_position_value', 1000)  # 单仓最大价值（USDT）
        self.max_total_value = config.get('max_total_value', 5000)  # 总持仓最大价值
        self.stop_loss_percent = config.get('stop_loss_percent', 2.0)  # 止损百分比
        self.take_profit_percent = config.get('take_profit_percent', 5.0)  # 止盈百分比
        self.max_leverage = config.get('max_leverage', 10)  # 最大杠杆
        self.margin_usage_threshold = config.get('margin_usage_threshold', 0.8)  # 保证金使用率阈值

        # 市场数据缓存
        self._market_data_cache: Dict[str, Dict] = {}
        self._cache_timeout = 30  # 缓存超时（秒）

        # 统计
        self.total_risk_checks = 0
        self.rejected_orders = 0
        self.stop_loss_triggered = 0
        self.take_profit_triggered = 0

        logger.info("风险管理器初始化完成")
        logger.info(f"单仓限制: {self.max_position_value} USDT")
        logger.info(f"总仓限制: {self.max_total_value} USDT")
        logger.info(f"止损: {self.stop_loss_percent}%, 止盈: {self.take_profit_percent}%")

    def _get_or_fetch_market_data(self, symbol: str) -> Dict:
        """
        获取或获取市场数据（带缓存）

        Args:
            symbol: 交易对

        Returns:
            市场数据
        """
        import time

        current_time = time.time()
        cache_key = symbol

        # 检查缓存
        if cache_key in self._market_data_cache:
            cached_data = self._market_data_cache[cache_key]
            if current_time - cached_data['timestamp'] < self._cache_timeout:
                return cached_data['data']

        # 从交易所获取新数据
        try:
            if not self.exchange:
                raise APIException("Exchange not initialized")

            # 获取ticker和订单簿
            ticker = self.exchange.fetch_ticker(symbol)
            orderbook = self.exchange.fetch_order_book(symbol, limit=20)

            market_data = {
                'ticker': ticker,
                'orderbook': orderbook,
                'timestamp': current_time
            }

            # 缓存数据
            self._market_data_cache[cache_key] = {
                'data': market_data,
                'timestamp': current_time
            }

            return market_data

        except Exception as e:
            logger.error(f"获取市场数据失败: {e}")
            raise APIException(f"Failed to fetch market data for {symbol}: {e}")

    def _get_liquidity(self, symbol: str, depth: int = 10) -> float:
        """
        获取市场流动性（24h交易量和订单簿深度）

        Args:
            symbol: 交易对
            depth: 订单簿深度

        Returns:
            流动性指标 (0-1之间，越高流动性越好)
        """
        try:
            market_data = self._get_or_fetch_market_data(symbol)
            ticker = market_data['ticker']
            orderbook = market_data['orderbook']

            # 24h交易量
            volume_24h = float(ticker.get('baseVolume', ticker.get('quoteVolume', 0)))

            # 订单簿深度（前n档）
            bids = orderbook.get('bids', [])[:depth]
            asks = orderbook.get('asks', [])[:depth]

            bid_depth = sum(float(b[1]) for b in bids)
            ask_depth = sum(float(a[1]) for a in asks)

            # 流动性评分 (归一化)
            # 交易量权重: 0.6, 订单簿深度权重: 0.4
            score = 0.0

            # 交易量评分 (假设10000为满分)
            volume_score = min(volume_24h / 10000, 1.0)

            # 订单簿深度评分 (假设1000 USDT为满分)
            depth_score = min((bid_depth + ask_depth) / 1000, 1.0)

            score = 0.6 * volume_score + 0.4 * depth_score

            logger.debug(
                f"{symbol} 流动性: {score:.3f} "
                f"(24h交易量: {volume_24h:.2f}, 订单簿深度: {bid_depth:.2f}/{ask_depth:.2f})"
            )

            return score

        except Exception as e:
            logger.error(f"计算流动性失败: {e}")
            raise RiskException(f"Failed to calculate liquidity: {e}")

    def _get_volatility(self, symbol: str, timeframe: str = '1h', period: int = 24) -> float:
        """
        计算市场波动率（基于ATR和标准差）

        Args:
            symbol: 交易对
            timeframe: 时间周期
            period: 计算周期

        Returns:
            波动率 (百分比)
        """
        try:
            if not self.exchange:
                raise APIException("Exchange not initialized")

            # 获取历史K线
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=period + 1
            )

            if len(ohlcv) < period:
                raise DataQualityException(f"Insufficient data: got {len(ohlcv)}, need {period}")

            # 提取价格数据
            closes = [float(candle[4]) for candle in ohlcv]
            highs = [float(candle[2]) for candle in ohlcv]
            lows = [float(candle[3]) for candle in ohlcv]

            # 计算ATR (Average True Range)
            tr_values = []
            for i in range(1, len(closes)):
                high = highs[i]
                low = lows[i]
                prev_close = closes[i - 1]

                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                tr_values.append(tr)

            atr = sum(tr_values) / len(tr_values) if tr_values else 0

            # 计算平均价格
            avg_price = sum(closes) / len(closes)

            # ATR百分比
            atr_percent = (atr / avg_price) * 100 if avg_price > 0 else 0

            # 计算标准差
            import math
            mean_price = sum(closes) / len(closes)
            variance = sum((x - mean_price) ** 2 for x in closes) / len(closes)
            std_dev = math.sqrt(variance)
            std_percent = (std_dev / mean_price) * 100 if mean_price > 0 else 0

            # 综合波动率 (ATR和标准差的平均值)
            volatility = (atr_percent + std_percent) / 2

            logger.debug(
                f"{symbol} 波动率: {volatility:.3f}% "
                f"(ATR: {atr_percent:.3f}%, Std: {std_percent:.3f}%)"
            )

            return volatility

        except Exception as e:
            logger.error(f"计算波动率失败: {e}")
            raise RiskException(f"Failed to calculate volatility: {e}")

    def _get_orderbook_depth(self, symbol: str, depth: int = 20) -> Dict[str, float]:
        """
        获取订单簿深度

        Args:
            symbol: 交易对
            depth: 深度

        Returns:
            订单簿深度信息
        """
        try:
            market_data = self._get_or_fetch_market_data(symbol)
            orderbook = market_data['orderbook']

            bids = orderbook.get('bids', [])[:depth]
            asks = orderbook.get('asks', [])[:depth]

            bid_volume = sum(float(b[1]) for b in bids)
            ask_volume = sum(float(a[1]) for a in asks)

            spread = 0.0
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                spread = best_ask - best_bid
                spread_percent = (spread / best_bid) * 100 if best_bid > 0 else 0
            else:
                spread_percent = 0.0

            result = {
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'total_volume': bid_volume + ask_volume,
                'best_bid': float(bids[0][0]) if bids else 0,
                'best_ask': float(asks[0][0]) if asks else 0,
                'spread': spread,
                'spread_percent': spread_percent,
                'depth_levels': len(bids) + len(asks),
            }

            logger.debug(
                f"{symbol} 订单簿深度: 买 {bid_volume:.2f}, "
                f"卖 {ask_volume:.2f}, 价差 {spread_percent:.4f}%"
            )

            return result

        except Exception as e:
            logger.error(f"获取订单簿深度失败: {e}")
            raise RiskException(f"Failed to get orderbook depth: {e}")

    def get_market_risk_metrics(self, symbol: str) -> Dict[str, Any]:
        """
        获取完整的市場风险指标

        Args:
            symbol: 交易对

        Returns:
            风险指标字典
        """
        try:
            return {
                'liquidity': self._get_liquidity(symbol),
                'volatility': self._get_volatility(symbol),
                'orderbook_depth': self._get_orderbook_depth(symbol)
            }
        except Exception as e:
            logger.error(f"获取市場风险指标失败: {e}")
            raise RiskException(f"Failed to get market risk metrics: {e}")

    @retry_on_exception(exceptions=(RiskException,), max_retries=3)
    def check_order(
        self,
        symbol: str,
        side: str,
        order_value: float,
        current_positions: Dict[str, Any] = None
    ) -> RiskCheckResult:
        """
        检查订单风险

        Args:
            symbol: 交易对
            side: 买卖方向
            order_value: 订单价值（USDT）
            current_positions: 当前持仓列表

        Returns:
            风险检查结果
        """
        self.total_risk_checks += 1

        if current_positions is None:
            current_positions = {}

        # 1. 检查单仓价值限制
        if order_value > self.max_position_value:
            self.rejected_orders += 1
            return RiskCheckResult(
                passed=False,
                level=RiskLevel.HIGH,
                message=f"单仓价值超限: {order_value:.2f} > {self.max_position_value} USDT",
                details={
                    'order_value': order_value,
                    'max_position_value': self.max_position_value
                }
            )

        # 2. 检查总持仓价值
        current_total = sum(pos.get('value', 0) for pos in current_positions.values())
        positions = current_positions.get(symbol, {'size': 0, 'value': 0})

        # 计算新持仓价值
        if side == 'buy':
            # 买入增加持仓
            new_position_value = positions.get('value', 0) + order_value
        else:
            # 卖出/做空
            new_position_value = abs(positions.get('value', 0) - order_value)

        new_total = current_total - positions.get('value', 0) + new_position_value

        if new_total > self.max_total_value:
            self.rejected_orders += 1
            return RiskCheckResult(
                passed=False,
                level=RiskLevel.HIGH,
                message=f"总持仓价值超限: {new_total:.2f} > {self.max_total_value} USDT",
                details={
                    'new_total': new_total,
                    'max_total_value': self.max_total_value
                }
            )

        # 3. 检查市场流动性
        try:
            liquidity = self._get_liquidity(symbol)
            if liquidity < 0.2:
                return RiskCheckResult(
                    passed=False,
                    level=RiskLevel.HIGH,
                    message=f"市场流动性不足: {liquidity:.3f}",
                    details={'liquidity': liquidity}
                )
            elif liquidity < 0.5:
                logger.warning(f"{symbol} 流动性较低: {liquidity:.3f}")
        except Exception as e:
            logger.warning(f"流动性检查失败，跳过: {e}")

        # 风险通过
        logger.debug(f"订单风险检查通过: {symbol} {side} {order_value:.2f} USDT")
        return RiskCheckResult(
            passed=True,
            level=RiskLevel.LOW,
            message="订单风险检查通过",
            details={
                'order_value': order_value,
                'new_position_value': new_position_value,
                'new_total': new_total
            }
        )

    def check_stop_loss(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        side: str = 'long'
    ) -> Optional[Dict]:
        """
        检查止损条件

        Args:
            symbol: 交易对
            entry_price: 入场价格
            current_price: 当前价格
            side: 仓位方向

        Returns:
            止损信号，如果未触发则返回None
        """
        if side == 'long':
            # 做多止损：价格跌破止损线
            stop_loss_price = entry_price * (1 - self.stop_loss_percent / 100)
            if current_price <= stop_loss_price:
                self.stop_loss_triggered += 1
                logger.warning(f"{symbol} 触发止损: {current_price:.2f} < {stop_loss_price:.2f}")
                return {
                    'type': 'stop_loss',
                    'symbol': symbol,
                    'current_price': current_price,
                    'trigger_price': stop_loss_price,
                    'entry_price': entry_price,
                    'pnl_percent': (current_price - entry_price) / entry_price * 100
                }
        else:  # short
            # 做空止损：价格涨破止损线
            stop_loss_price = entry_price * (1 + self.stop_loss_percent / 100)
            if current_price >= stop_loss_price:
                self.stop_loss_triggered += 1
                logger.warning(f"{symbol} 触发止损: {current_price:.2f} > {stop_loss_price:.2f}")
                return {
                    'type': 'stop_loss',
                    'symbol': symbol,
                    'current_price': current_price,
                    'trigger_price': stop_loss_price,
                    'entry_price': entry_price,
                    'pnl_percent': (entry_price - current_price) / entry_price * 100
                }

        return None

    def check_take_profit(
        self,
        symbol: str,
        entry_price: float,
        current_price: float,
        side: str = 'long'
    ) -> Optional[Dict]:
        """
        检查止盈条件

        Args:
            symbol: 交易对
            entry_price: 入场价格
            current_price: 当前价格
            side: 仓位方向

        Returns:
            止盈信号，如果未触发则返回None
        """
        if side == 'long':
            # 做多止盈：价格涨破止盈线
            take_profit_price = entry_price * (1 + self.take_profit_percent / 100)
            if current_price >= take_profit_price:
                self.take_profit_triggered += 1
                logger.info(f"{symbol} 触发止盈: {current_price:.2f} >= {take_profit_price:.2f}")
                return {
                    'type': 'take_profit',
                    'symbol': symbol,
                    'current_price': current_price,
                    'trigger_price': take_profit_price,
                    'entry_price': entry_price,
                    'pnl_percent': (current_price - entry_price) / entry_price * 100
                }
        else:  # short
            # 做空止盈：价格跌破止盈线
            take_profit_price = entry_price * (1 - self.take_profit_percent / 100)
            if current_price <= take_profit_price:
                self.take_profit_triggered += 1
                logger.info(f"{symbol} 触发止盈: {current_price:.2f} <= {take_profit_price:.2f}")
                return {
                    'type': 'take_profit',
                    'symbol': symbol,
                    'current_price': current_price,
                    'trigger_price': take_profit_price,
                    'entry_price': entry_price,
                    'pnl_percent': (entry_price - current_price) / entry_price * 100
                }

        return None

    def check_margin_usage(
        self,
        margin_used: float,
        margin_available: float
    ) -> RiskCheckResult:
        """
        检查保证金使用率

        Args:
            margin_used: 已用保证金
            margin_available: 可用保证金

        Returns:
            风险检查结果
        """
        if margin_available <= 0:
            return RiskCheckResult(
                passed=False,
                level=RiskLevel.CRITICAL,
                message="可用保证金不足",
                details={'margin_used': margin_used, 'margin_available': margin_available}
            )

        margin_ratio = margin_used / (margin_used + margin_available)

        if margin_ratio >= self.margin_usage_threshold:
            return RiskCheckResult(
                passed=False,
                level=RiskLevel.CRITICAL,
                message=f"保证金使用率过高: {margin_ratio*100:.2f}% >= {self.margin_usage_threshold*100}%",
                details={
                    'margin_ratio': margin_ratio,
                    'threshold': self.margin_usage_threshold
                }
            )

        if margin_ratio >= self.margin_usage_threshold * 0.8:
            return RiskCheckResult(
                passed=True,
                level=RiskLevel.HIGH,
                message=f"保证金使用率较高: {margin_ratio*100:.2f}%",
                details={'margin_ratio': margin_ratio}
            )

        return RiskCheckResult(
            passed=True,
            level=RiskLevel.LOW,
            message="保证金使用率正常",
            details={'margin_ratio': margin_ratio}
        )

    def calculate_position_size(
        self,
        account_balance: float,
        risk_percent: float = 1.0,
        leverage: int = 1
    ) -> float:
        """
        计算建议仓位大小（基于风险百分比）

        Args:
            account_balance: 账户余额（USDT）
            risk_percent: 风险百分比（单次交易最大亏损占比）
            leverage: 杠杆倍数

        Returns:
            建议仓位价值（USDT）
        """
        risk_amount = account_balance * (risk_percent / 100)
        position_value = risk_amount * leverage

        # 不超过单仓限制
        position_value = min(position_value, self.max_position_value)

        logger.debug(
            f"仓位计算: 余额 {account_balance:.2f}, 风险 {risk_percent}%, "
            f"杠杆 {leverage}x -> {position_value:.2f} USDT"
        )
        return position_value

    def update_position(self, symbol: str, position: Dict):
        """
        更新持仓信息

        Args:
            symbol: 交易对
            position: 持仓信息
        """
        self.positions[symbol] = position
        logger.debug(f"持仓已更新: {symbol} - {position}")

    def remove_position(self, symbol: str):
        """
        移除持仓

        Args:
            symbol: 交易对
        """
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"持仓已移除: {symbol}")

    def get_stats(self) -> Dict:
        """
        获取风险管理统计

        Returns:
            统计信息
        """
        return {
            'total_risk_checks': self.total_risk_checks,
            'rejected_orders': self.rejected_orders,
            'rejection_rate': self.rejected_orders / self.total_risk_checks if self.total_risk_checks > 0 else 0,
            'stop_loss_triggered': self.stop_loss_triggered,
            'take_profit_triggered': self.take_profit_triggered,
            'max_position_value': self.max_position_value,
            'max_total_value': self.max_total_value,
            'stop_loss_percent': self.stop_loss_percent,
            'take_profit_percent': self.take_profit_percent,
        }

    def reset(self):
        """重置统计"""
        self.total_risk_checks = 0
        self.rejected_orders = 0
        self.stop_loss_triggered = 0
        self.take_profit_triggered = 0
        self._market_data_cache.clear()
        logger.info("风险管理统计已重置")
