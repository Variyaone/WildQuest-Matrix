"""
数据采集器模块
通过WebSocket实时获取K线数据、Ticker和Orderbook
基于ccxt库实现，包含完整的异常处理、重连机制和数据清洗
"""

import json
import time
import logging
import threading
import hashlib
import hmac
import base64
from typing import Dict, Callable, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass
import ccxt

from ..exceptions import (
    APIException,
    WebSocketException,
    DataQualityException,
    handle_exceptions,
    retry_on_exception
)

logger = logging.getLogger(__name__)


@dataclass
class MarketData:
    """市场数据结构"""
    instrument_id: str
    timestamp: int
    data_type: str  # 'candle', 'ticker', 'orderbook'
    data: Dict[str, Any]


class DataCollector:
    """
    数据采集器
    管理WebSocket连接，订阅K线数据，处理重连机制
    """

    def __init__(
        self,
        api_key: str = None,
        secret: str = None,
        passphrase: str = None,
        config: Dict[str, Any] = None
    ):
        """
        初始化数据采集器

        Args:
            api_key: OKX API密钥
            secret: API密钥Secret
            passphrase: API密钥Passphrase
            config: 额外配置参数
        """
        self.api_key = api_key
        self.secret = secret
        self.passphrase = passphrase
        self.config = config or {}

        # CCXT交易所实例（用于REST API）
        self.exchange = None
        self._init_exchange()

        # WebSocket连接
        self.ws = None
        self.ws_url = self.config.get('ws_url', "wss://ws.okx.com:8443/ws/v5/public")

        # 连接状态
        self.is_connected = False
        self.is_running = False
        self.subscriptions: Dict[str, Dict] = {}  # {channel_key: channel_info}

        # 回调函数
        self.on_data_callbacks: List[Callable[[MarketData], None]] = []
        self.on_error_callbacks: List[Callable[[Exception], None]] = []

        # 重连机制（指数退避）
        self.reconnect_enabled = True
        self.max_reconnect_attempts = self.config.get('max_reconnect_attempts', 10)
        self.reconnect_count = 0
        self.reconnect_delay_base = self.config.get('reconnect_delay_base', 2)

        # 心跳监控（周期30秒）
        self.last_ping = time.time()
        self.last_pong = time.time()
        self.ping_interval = self.config.get('ping_interval', 30)
        self.heartbeat_timeout = self.config.get('heartbeat_timeout', 90)

        # 线程控制
        self._lock = threading.Lock()
        self._ws_thread = None
        self._heartbeat_thread = None

        # 数据统计
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'reconnects': 0
        }

        logger.info("数据采集器初始化完成")

    def _init_exchange(self):
        """初始化CCXT交易所实例"""
        try:
            self.exchange = ccxt.okx({
                'apiKey': self.api_key,
                'secret': self.secret,
                'password': self.passphrase,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'swap',
                }
            })

            logger.info("CCXT交易所实例初始化成功")

        except Exception as e:
            logger.error(f"CCXT交易所初始化失败: {e}")
            raise APIException(f"Failed to initialize exchange: {e}")

    def _generate_signature(self, timestamp: str, method: str, request_path: str, body: str = '') -> str:
        """
        生成API签名（私有频道）

        Args:
            timestamp: 时间戳
            method: HTTP方法
            request_path: 请求路径
            body: 请求体

        Returns:
            Base64签名字符串
        """
        if not self.secret:
            return ""

        if body:
            message = timestamp + method + request_path + body
        else:
            message = timestamp + method + request_path

        mac = hmac.new(
            bytes(self.secret, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()

    # ========== WebSocket回调函数 ==========

    def _on_open(self, ws):
        """WebSocket连接打开回调"""
        logger.info("WebSocket连接已建立")
        self.is_connected = True
        self.reconnect_count = 0
        self.last_pong = time.time()

        # 重新订阅之前的频道
        try:
            for channel_key, channel_info in self.subscriptions.items():
                self._subscribe(channel_info)
                logger.info(f"重新订阅频道: {channel_key}")
        except Exception as e:
            logger.error(f"重订阅失败: {e}")

    def _on_message(self, ws, message):
        """WebSocket消息回调"""
        try:
            data = json.loads(message)
            self.stats['messages_received'] += 1

            # 处理心跳消息
            if data.get('event') == 'ping':
                self._send_pong()
                return

            if data.get('event') == 'pong':
                self.last_pong = time.time()
                return

            # 处理数据消息
            if 'data' in data:
                self._process_data(data)
            # 处理成功响应
            elif data.get('code') == '0':
                logger.debug(f"操作成功: {data.get('msg', '')}")
            # 处理错误
            else:
                logger.warning(f"WebSocket错误: {data}")
                self.stats['errors'] += 1

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            self.stats['errors'] += 1

    def _on_error(self, ws, error):
        """WebSocket错误回调"""
        logger.error(f"WebSocket错误: {error}")

        # 异常回调
        exc = WebSocketException(
            f"WebSocket error occurred",
            original_error=error if isinstance(error, Exception) else Exception(str(error))
        )
        self.stats['errors'] += 1

        for callback in self.on_error_callbacks:
            try:
                callback(exc)
            except Exception as e:
                logger.error(f"错误回调执行失败: {e}")

    def _on_close(self, ws, close_status_code, close_msg):
        """WebSocket连接关闭回调"""
        logger.info(f"WebSocket连接已关闭: {close_status_code} - {close_msg}")
        self.is_connected = False

        # 停止心跳线程
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=1)

        # 自动重连
        if self.reconnect_enabled and self.is_running:
            self._reconnect()

    # ========== 数据处理 ==========

    def _process_data(self, data: Dict):
        """
        处理接收到的数据并清洗标准化

        Args:
            data: WebSocket数据
        """
        try:
            arg = data.get('arg', {})
            channel = arg.get('channel', '')
            inst_id = arg.get('instId', '')
            data_list = data.get('data', [])

            if not data_list:
                return

            self.stats['messages_processed'] += 1

            # 根据频道类型处理数据
            if 'candle' in channel:
                self._process_candlestick(inst_id, channel, data_list)
            elif channel == 'ticker':
                self._process_ticker(inst_id, data_list)
            elif channel == 'books':
                self._process_orderbook(inst_id, data_list)
            elif channel == 'books5':
                self._process_orderbook(inst_id, data_list, depth=5)
            else:
                logger.debug(f"未知频道: {channel}")

        except Exception as e:
            logger.error(f"数据处理失败: {e}")
            raise DataQualityException(f"Failed to process data: {e}")

    def _process_candlestick(self, inst_id: str, channel: str, data_list: List):
        """处理K线数据"""
        for candle in data_list:
            try:
                # OKX K线格式: [timestamp, open, high, low, close, volume, volume_ccy, volume_ccy_quote]
                if not isinstance(candle, list) or len(candle) < 6:
                    raise DataQualityException("Invalid candlestick data format", field='candle', value=candle)

                market_data = MarketData(
                    instrument_id=inst_id,
                    timestamp=int(candle[0]),
                    data_type='candle',
                    data={
                        'open': float(candle[1]),
                        'high': float(candle[2]),
                        'low': float(candle[3]),
                        'close': float(candle[4]),
                        'volume': float(candle[5]),
                        'channel': channel
                    }
                )

                self._dispatch_data(market_data)

            except (ValueError, IndexError) as e:
                logger.warning(f"K线数据解析失败: {e}, 数据: {candle}")

    def _process_ticker(self, inst_id: str, data_list: List):
        """处理Ticker数据"""
        for ticker in data_list:
            try:
                market_data = MarketData(
                    instrument_id=inst_id,
                    timestamp=int(ticker.get('ts', 0)),
                    data_type='ticker',
                    data={
                        'last': float(ticker.get('last', 0)),
                        'bid': float(ticker.get('bidPx', 0)),
                        'ask': float(ticker.get('askPx', 0)),
                        'bid_size': float(ticker.get('bidSz', 0)),
                        'ask_size': float(ticker.get('askSz', 0)),
                        'volume_24h': float(ticker.get('vol24h', 0)),
                        'high_24h': float(ticker.get('high24h', 0)),
                        'low_24h': float(ticker.get('low24h', 0)),
                    }
                )

                self._dispatch_data(market_data)

            except (ValueError, KeyError) as e:
                logger.warning(f"Ticker数据解析失败: {e}, 数据: {ticker}")

    def _process_orderbook(self, inst_id: str, data_list: List, depth: int = 20):
        """处理订单簿数据"""
        for orderbook in data_list:
            try:
                asks = [[float(p), float(s)] for p, s in orderbook.get('asks', [])[:depth]]
                bids = [[float(p), float(s)] for p, s in orderbook.get('bids', [])[:depth]]

                market_data = MarketData(
                    instrument_id=inst_id,
                    timestamp=int(orderbook.get('ts', 0)),
                    data_type='orderbook',
                    data={
                        'bids': bids,
                        'asks': asks,
                        'depth': depth,
                        'best_bid': bids[0] if bids else [0, 0],
                        'best_ask': asks[0] if asks else [0, 0],
                        'spread': (asks[0][0] - bids[0][0]) if asks and bids else 0
                    }
                )

                self._dispatch_data(market_data)

            except (ValueError, KeyError, IndexError) as e:
                logger.warning(f"订单簿数据解析失败: {e}, 数据: {orderbook}")

    def _dispatch_data(self, market_data: MarketData):
        """分发数据到回调函数"""
        for callback in self.on_data_callbacks:
            try:
                callback(market_data)
            except Exception as e:
                logger.error(f"数据回调执行失败: {e}")

    # ========== 心跳机制 ==========

    def _send_ping(self):
        """发送ping消息"""
        if self.ws and self.is_connected:
            try:
                ping_msg = json.dumps({"op": "ping"})
                self.ws.send(ping_msg)
                self.last_ping = time.time()
                logger.debug("发送心跳ping")
            except Exception as e:
                logger.error(f"发送ping失败: {e}")

    def _send_pong(self):
        """发送pong响应"""
        if self.ws and self.is_connected:
            try:
                pong_msg = json.dumps({"op": "pong"})
                self.ws.send(pong_msg)
                self.last_pong = time.time()
            except Exception as e:
                logger.error(f"发送pong失败: {e}")

    def _heartbeat_loop(self):
        """心跳监控循环"""
        while self.is_running:
            try:
                time.sleep(self.ping_interval)

                if not self.is_connected:
                    continue

                # 检查心跳超时
                if time.time() - self.last_pong > self.heartbeat_timeout:
                    logger.warning("心跳超时，触发重连")
                    self._reconnect()
                    break

                # 发送ping
                self._send_ping()

            except Exception as e:
                logger.error(f"心跳线程错误: {e}")

    # ========== WebSocket操作 ==========

    def _subscribe(self, channel_info: Dict):
        """
        订阅频道

        Args:
            channel_info: 频道信息
        """
        if not self.is_connected:
            raise WebSocketException("WebSocket未连接，无法订阅")

        try:
            msg = {
                "op": "subscribe",
                "args": [channel_info]
            }
            self.ws.send(json.dumps(msg))
            logger.info(f"订阅频道: {channel_info}")

        except Exception as e:
            raise WebSocketException(f"订阅频道失败: {e}")

    def _unsubscribe(self, channel_info: Dict):
        """
        取消订阅频道

        Args:
            channel_info: 频道信息
        """
        if not self.is_connected:
            return

        try:
            msg = {
                "op": "unsubscribe",
                "args": [channel_info]
            }
            self.ws.send(json.dumps(msg))
            logger.info(f"取消订阅: {channel_info}")

        except Exception as e:
            logger.error(f"取消订阅失败: {e}")

    def _reconnect(self):
        """重连逻辑（指数退避）"""
        if not self.reconnect_enabled:
            logger.info("重连已禁用")
            return

        if self.reconnect_count >= self.max_reconnect_attempts:
            error_msg = f"达到最大重连次数 ({self.max_reconnect_attempts})，停止重连"
            logger.error(error_msg)
            self.is_running = False
            raise WebSocketException(error_msg)

        with self._lock:
            if not self.is_running:
                return

            self.reconnect_count += 1
            # 指数退避
            delay = self.reconnect_delay_base * (2 ** (self.reconnect_count - 1))
            delay = min(delay, 60)  # 最大延迟60秒

            logger.info(f"将在 {delay} 秒后尝试第 {self.reconnect_count} 次重连...")
            time.sleep(delay)

            try:
                if self.ws:
                    self.ws.close()

                import websocket
                self._connect_websocket()
                self.stats['reconnects'] += 1

            except Exception as e:
                logger.error(f"重连失败: {e}")
                self._reconnect()

    def _connect_websocket(self):
        """建立WebSocket连接"""
        import websocket

        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )

        # 启动WebSocket循环
        self._ws_thread = threading.Thread(
            target=self.ws.run_forever,
            kwargs={'ping_interval': self.ping_interval}
        )
        self._ws_thread.daemon = True
        self._ws_thread.start()

        # 启动心跳线程
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        self._heartbeat_thread.daemon = True
        self._heartbeat_thread.start()

        logger.info("WebSocket连接线程已启动")

    # ========== 公共接口 ==========

    @handle_exceptions(context="DataCollector.connect")
    def connect(self):
        """建立WebSocket连接"""
        self.is_running = True
        self._connect_websocket()

        # 等待连接建立
        timeout = 10
        start = time.time()
        while not self.is_connected and time.time() - start < timeout:
            time.sleep(0.1)

        if not self.is_connected:
            raise WebSocketException("WebSocket连接超时")

        logger.info("数据采集器已连接")

    @handle_exceptions(context="DataCollector.disconnect")
    def disconnect(self):
        """断开连接"""
        self.is_running = False
        self.reconnect_enabled = False

        if self.ws:
            self.ws.close()

        logger.info("数据采集器已断开")

    def subscribe_candlesticks(self, inst_id: str, bar: str = '1H'):
        """
        订阅K线数据

        Args:
            inst_id: 交易对，如 'BTC-USDT-SWAP'
            bar: 时间周期，如 '1m', '5m', '15m', '1H', '4H', '1D'
        """
        channel_info = {
            "channel": f"candle{bar}",
            "instId": inst_id
        }
        channel_key = f"{channel_info['channel']}:{inst_id}"
        self.subscriptions[channel_key] = channel_info

        if self.is_connected:
            self._subscribe(channel_info)

        logger.info(f"已订阅K线频道: {inst_id}, {bar}")

    def subscribe_ticker(self, inst_id: str):
        """
        订阅24H行情

        Args:
            inst_id: 交易对
        """
        channel_info = {
            "channel": "ticker",
            "instId": inst_id
        }
        channel_key = f"ticker:{inst_id}"
        self.subscriptions[channel_key] = channel_info

        if self.is_connected:
            self._subscribe(channel_info)

        logger.info(f"已订阅行情频道: {inst_id}")

    def subscribe_orderbook(self, inst_id: str, depth: int = 20):
        """
        订阅订单簿

        Args:
            inst_id: 交易对
            depth: 深度（5或20）
        """
        channel_name = "books" if depth == 20 else "books5"
        channel_info = {
            "channel": channel_name,
            "instId": inst_id
        }
        channel_key = f"{channel_name}:{inst_id}"
        self.subscriptions[channel_key] = channel_info

        if self.is_connected:
            self._subscribe(channel_info)

        logger.info(f"已订阅订单簿频道: {inst_id}, 深度: {depth}")

    def unsubscribe(self, channel: str, inst_id: str):
        """
        取消订阅

        Args:
            channel: 频道名称
            inst_id: 交易对
        """
        channel_key = f"{channel}:{inst_id}"
        if channel_key in self.subscriptions:
            self._unsubscribe(self.subscriptions[channel_key])
            del self.subscriptions[channel_key]

    @retry_on_exception(exceptions=(APIException,), max_retries=3, context="DataCollector.fetch_historical")
    def fetch_historical_ohlcv(
        self,
        symbol: str,
        timeframe: str = '1h',
        limit: int = 100,
        since: int = None
    ) -> List[List]:
        """
        获取历史K线数据（通过REST API）

        Args:
            symbol: 交易对（CCXT格式，如 'BTC/USDT:USDT'）
            timeframe: 时间周期
            limit: 数量限制
            since: 起始时间戳

        Returns:
            K线数据列表
        """
        if not self.exchange:
            raise APIException("Exchange not initialized")

        try:
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            logger.info(f"获取历史K线成功: {symbol}, {timeframe}, {len(ohlcv)} 条")
            return ohlcv

        except Exception as e:
            logger.error(f"获取历史K线失败: {e}")
            raise APIException(f"Failed to fetch historical OHLCV: {e}")

    @retry_on_exception(exceptions=(APIException,), max_retries=3, context="DataCollector.fetch_ticker")
    def fetch_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取当前行情（通过REST API）

        Args:
            symbol: 交易对

        Returns:
            Ticker信息
        """
        if not self.exchange:
            raise APIException("Exchange not initialized")

        try:
            ticker = self.exchange.fetch_ticker(symbol)
            logger.info(f"获取行情成功: {symbol}")
            return ticker

        except Exception as e:
            logger.error(f"获取行情失败: {e}")
            raise APIException(f"Failed to fetch ticker: {e}")

    @retry_on_exception(exceptions=(APIException,), max_retries=3, context="DataCollector.fetch_orderbook")
    def fetch_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        获取订单簿（通过REST API）

        Args:
            symbol: 交易对
            limit: 深度

        Returns:
            订单簿数据
        """
        if not self.exchange:
            raise APIException("Exchange not initialized")

        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=limit)
            logger.info(f"获取订单簿成功: {symbol}")
            return orderbook

        except Exception as e:
            logger.error(f"获取订单簿失败: {e}")
            raise APIException(f"Failed to fetch orderbook: {e}")

    # ========== 回调注册 ==========

    def register_data_callback(self, callback: Callable[[MarketData], None]):
        """
        注册数据回调函数

        Args:
            callback: 回调函数
        """
        self.on_data_callbacks.append(callback)
        logger.debug("数据回调已注册")

    def register_error_callback(self, callback: Callable[[Exception], None]):
        """
        注册错误回调函数

        Args:
            callback: 回调函数
        """
        self.on_error_callbacks.append(callback)
        logger.debug("错误回调已注册")

    # ========== 统计信息 ==========

    def get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'subscriptions': len(self.subscriptions),
            'reconnect_count': self.reconnect_count,
            'last_pong_age': time.time() - self.last_pong if self.last_pong else 0,
            **self.stats
        }

    def reset_stats(self):
        """重置统计"""
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'errors': 0,
            'reconnects': 0
        }
