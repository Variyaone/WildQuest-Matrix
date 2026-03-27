"""
监控器模块
实时监控系统状态、策略表现、账户信息
"""

import logging
import time
import threading
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class Alert:
    """告警信息"""
    level: str  # 'info', 'warning', 'error', 'critical'
    message: str
    timestamp: float = field(default_factory=time.time)
    source: str = "monitor"


class Monitor:
    """
    系统监控器
    监控系统状态、策略表现、订单执行等
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化监控器

        Args:
            config: 配置参数
                - alert_max_size: 最大告警数
                - metrics_max_size: 最大指标数
                - heartbeat_interval: 心跳间隔（秒）
        """
        self.config = config or {}
        self.is_running = False
        self.is_initialized = False

        # 告警队列
        self.alert_max_size = self.config.get('alert_max_size', 1000)
        self.alerts: deque = deque(maxlen=self.alert_max_size)

        # 指标缓存
        self.metrics_max_size = self.config.get('metrics_max_size', 10000)
        self.metrics: deque = deque(maxlen=self.metrics_max_size)

        # 统计数据
        self.stats = {
            'signals_generated': 0,
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_failed': 0,
            'errors': 0,
            'warnings': 0,
            'info': 0,
        }

        # 心跳
        self.heartbeat_interval = self.config.get('heartbeat_interval', 30)
        self.last_heartbeat = None

        # 回调函数
        self.on_signal_callbacks: List[Callable] = []
        self.on_order_callbacks: List[Callable] = []
        self.on_error_callbacks: List[Callable] = []

        # 当前状态
        self.current_positions: Dict[str, Any] = {}
        self.current_balance: Dict[str, Any] = {}

        logger.info("监控器初始化完成")

    def initialize(self) -> bool:
        """
        初始化监控器

        Returns:
            是否成功
        """
        self.is_initialized = True
        logger.info("监控器初始化成功")
        return True

    def start(self):
        """启动监控"""
        if not self.is_initialized:
            self.initialize()

        self.is_running = True
        self.last_heartbeat = time.time()
        logger.info("监控器已启动")

    def stop(self):
        """停止监控"""
        self.is_running = False
        logger.info("监控器已停止")

    # ========== 告警管理 ==========

    def alert(self, level: str, message: str, source: str = "monitor"):
        """
        发送告警

        Args:
            level: 告警级别
            message: 告警消息
            source: 来源
        """
        alert = Alert(level=level, message=message, source=source)
        self.alerts.append(alert)

        # 更新统计
        if level in self.stats:
            self.stats[level] += 1

        # 记录日志
        if level == 'critical':
            logger.critical(message)
        elif level == 'error':
            logger.error(message)
        elif level == 'warning':
            logger.warning(message)
        else:
            logger.info(message)

    def get_alerts(
        self,
        level: str = None,
        count: int = 100,
        since: float = None
    ) -> List[Alert]:
        """
        获取告警

        Args:
            level: 告警级别（可选）
            count: 数量
            since: 起始时间

        Returns:
            告警列表
        """
        alerts = list(self.alerts)

        # 过滤
        if level:
            alerts = [a for a in alerts if a.level == level]

        if since:
            alerts = [a for a in alerts if a.timestamp >= since]

        # 限制数量
        alerts = alerts[-count:]

        return alerts

    def clear_alerts(self):
        """清空告警"""
        self.alerts.clear()
        logger.info("告警已清空")

    # ========== 信号监控 ==========

    def on_signal(self, signal: Dict[str, Any]):
        """
        信号回调

        Args:
            signal: 交易信号
        """
        self.stats['signals_generated'] += 1

        # 记录指标
        metric = {
            'type': 'signal',
            'data': signal,
            'timestamp': time.time()
        }
        self.metrics.append(metric)

        # 调用回调
        for callback in self.on_signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                logger.error(f"信号回调执行失败: {e}")

        self.alert('info', f"生成信号: {signal.get('signal_type')} {signal.get('instrument_id')} @ {signal.get('price')}")

    def register_signal_callback(self, callback: Callable):
        """
        注册信号回调

        Args:
            callback: 回调函数
        """
        self.on_signal_callbacks.append(callback)

    # ========== 订单监控 ==========

    def on_order_placed(self, order: Dict[str, Any]):
        """
        订单下单回调

        Args:
            order: 订单信息
        """
        self.stats['orders_placed'] += 1

        metric = {
            'type': 'order_placed',
            'data': order,
            'timestamp': time.time()
        }
        self.metrics.append(metric)

        for callback in self.on_order_callbacks:
            try:
                callback(order)
            except Exception as e:
                logger.error(f"订单回调执行失败: {e}")

    def on_order_filled(self, order: Dict[str, Any]):
        """
        订单成交回调

        Args:
            order: 订单信息
        """
        self.stats['orders_filled'] += 1

        metric = {
            'type': 'order_filled',
            'data': order,
            'timestamp': time.time()
        }
        self.metrics.append(metric)

        self.alert('info', f"订单成交: {order.get('instrument_id')} {order.get('side')} {order.get('filled_amount')} @ {order.get('price')}")

    def on_order_failed(self, error: Exception, order_info: Dict = None):
        """
        订单失败回调

        Args:
            error: 错误
            order_info: 订单信息
        """
        self.stats['orders_failed'] += 1

        self.alert('error', f"订单失败: {error}")

    def register_order_callback(self, callback: Callable):
        """
        注册订单回调

        Args:
            callback: 回调函数
        """
        self.on_order_callbacks.append(callback)

    # ========== 错误监控 ==========

    def on_error(self, error: Exception, context: str = ""):
        """
        错误回调

        Args:
            error: 错误对象
            context: 上下文
        """
        self.stats['errors'] += 1

        self.alert('error', f"{context}: {str(error)}")

    def register_error_callback(self, callback: Callable):
        """
        注册错误回调

        Args:
            callback: 回调函数
        """
        self.on_error_callbacks.append(callback)

    # ========== 状态更新 ==========

    def update_positions(self, positions: Dict[str, Any]):
        """
        更新持仓状态

        Args:
            positions: 持仓字典
        """
        self.current_positions = positions
        metric = {
            'type': 'positions',
            'data': positions,
            'timestamp': time.time()
        }
        self.metrics.append(metric)

    def update_balance(self, balance: Dict[str, Any]):
        """
        更新余额状态

        Args:
            balance: 余额字典
        """
        self.current_balance = balance
        metric = {
            'type': 'balance',
            'data': balance,
            'timestamp': time.time()
        }
        self.metrics.append(metric)

    # ========== 心跳 ==========

    def heartbeat(self):
        """发送心跳"""
        self.last_heartbeat = time.time()
        metric = {
            'type': 'heartbeat',
            'data': {
                'running': self.is_running,
                'stats': self.stats,
                'alerts_count': len(self.alerts),
                'metrics_count': len(self.metrics),
            },
            'timestamp': self.last_heartbeat
        }
        self.metrics.append(metric)

    def check_heartbeat(self, timeout: float = 60) -> bool:
        """
        检查心跳

        Args:
            timeout: 超时时间（秒）

        Returns:
            是否存活
        """
        if not self.last_heartbeat:
            return False

        elapsed = time.time() - self.last_heartbeat
        return elapsed < timeout

    # ========== 统计 ==========

    def get_stats(self) -> Dict:
        """
        获取统计信息

        Returns:
            统计数据
        """
        return {
            **self.stats,
            'alerts_count': len(self.alerts),
            'metrics_count': len(self.metrics),
            'last_heartbeat': self.last_heartbeat,
            'is_running': self.is_running,
        }

    def get_metrics(
        self,
        metric_type: str = None,
        count: int = 1000
    ) -> List[Dict]:
        """
        获取指标

        Args:
            metric_type: 指标类型（可选）
            count: 数量

        Returns:
            指标列表
        """
        metrics = list(self.metrics)

        if metric_type:
            metrics = [m for m in metrics if m.get('type') == metric_type]

        return metrics[-count:]

    def get_summary(self) -> Dict:
        """
        获取系统摘要

        Returns:
            摘要信息
        """
        return {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'running': self.is_running,
            'stats': self.get_stats(),
            'positions': self.current_positions,
            'balance': self.current_balance,
            'recent_alerts': [a.__dict__ for a in list(self.alerts)[-5:]],
        }

    def log_summary(self):
        """打印系统摘要"""
        summary = self.get_summary()
        logger.info(f"\n{'='*50}")
        logger.info(f"系统摘要 - {summary['time']}")
        logger.info(f"运行状态: {'运行中' if summary['running'] else '已停止'}")
        logger.info(f"统计: {summary['stats']}")
        logger.info(f"持仓数: {len(summary['positions'])}")
        logger.info(f"{'='*50}\n")

    def reset(self):
        """重置监控器"""
        self.alerts.clear()
        self.metrics.clear()
        self.stats = {k: 0 for k in self.stats}
        self.last_heartbeat = None
        logger.info("监控器已重置")
