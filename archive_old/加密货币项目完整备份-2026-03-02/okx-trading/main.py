#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX交易系统 - 主程序入口
整合所有模块，启动交易系统
"""

import sys
import time
import signal
import logging
import argparse
from pathlib import Path
from typing import Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 使用相对导入（在模块作为包的一部分时工作正常）
from .config.settings import Settings, get_settings
from .data.collector import DataCollector
from .data.storage import Storage
from .strategy.base import BaseStrategy, Signal
from .strategy.grid import GridStrategy
from .strategy.base import DummyStrategy
from .execution.order_executor import OKXOrderExecutor, MockExecutor
from .execution.risk_manager import RiskManager
from .monitor.monitor import Monitor

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('okx_trading.log')
    ]
)
logger = logging.getLogger(__name__)


class OKXTradingSystem:
    """
    OKX交易系统主类
    整合各个模块，协调运行
    """

    def __init__(self, config_path: str = None, simulated: bool = True):
        """
        初始化交易系统

        Args:
            config_path: 配置文件路径
            simulated: 是否使用模拟模式
        """
        self.config_path = config_path
        self.simulated = simulated
        self.is_running = False

        # 加载配置
        self.settings = Settings(config_path=config_path)

        # 初始化组件
        self.data_collector = None
        self.storage = None
        self.strategy = None
        self.executor = None
        self.risk_manager = None
        self.monitor = None

        logger.info(f"OKX交易系统初始化 - 模拟模式: {simulated}")

    def initialize(self, strategy_config: Dict[str, Any] = None) -> bool:
        """
        初始化系统

        Args:
            strategy_config: 策略配置

        Returns:
            是否成功
        """
        try:
            logger.info("开始初始化系统...")

            # 1. 初始化数据存储
            self.storage = Storage(db_path='data/okx_trading.db')
            logger.info("✓ 数据存储初始化完成")

            # 2. 初始化订单执行器
            if self.simulated:
                self.executor = MockExecutor()
                logger.info("✓ 模拟订单执行器初始化完成")
            else:
                self.executor = OKXOrderExecutor(config_path=self.config_path)
                logger.info("✓ OKX订单执行器初始化完成")

            # 3. 初始化风险管理器
            risk_config = {
                'max_position_value': 500,
                'max_total_value': 2000,
                'stop_loss_percent': 2.0,
                'take_profit_percent': 5.0,
                'max_leverage': 5,
                'margin_usage_threshold': 0.8,
            }
            self.risk_manager = RiskManager(config=risk_config)
            logger.info("✓ 风险管理器初始化完成")

            # 4. 初始化监控器
            self.monitor = Monitor()
            self.monitor.initialize()
            logger.info("✓ 监控器初始化完成")

            # 5. 初始化策略
            if strategy_config:
                strategy_name = strategy_config.get('name', 'grid')
                if strategy_name == 'grid':
                    self.strategy = GridStrategy(name='GridStrategy', config=strategy_config)
                else:
                    self.strategy = DummyStrategy(name='DummyStrategy', config=strategy_config)
            else:
                # 默认网格策略
                self.strategy = GridStrategy(
                    name='GridStrategy',
                    config={
                        'instrument_id': 'BTC-USDT-SWAP',
                        'upper_price': 50000,
                        'lower_price': 45000,
                        'grid_count': 10,
                        'grid_amount': 100,
                        'position_side': 'long'
                    }
                )

            if not self.strategy.initialize():
                logger.error("策略初始化失败")
                return False
            logger.info("✓ 策略初始化完成")

            # 6. 初始化数据采集器
            self.data_collector = DataCollector()
            logger.info("✓ 数据采集器初始化完成")

            # 7. 注册回调
            self._register_callbacks()

            logger.info("系统初始化完成")
            return True

        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _register_callbacks(self):
        """注册各种回调"""
        # 数据采集器回调
        self.data_collector.register_data_callback(self._on_market_data)
        self.data_collector.register_error_callback(self._on_data_error)

        # 监控器回调
        self.monitor.register_signal_callback(self._on_signal_from_monitor)
        self.monitor.register_order_callback(self._on_order_from_monitor)
        self.monitor.register_error_callback(self._on_error_from_monitor)

        # 策略错误回调
        self.strategy.on_error = self._on_strategy_error

    def _on_market_data(self, data: Dict):
        """
        处理市场数据

        Args:
            data: 市场数据
        """
        try:
            # 1. 存储数据
            self._store_market_data(data)

            # 2. 传递给策略
            signal = self.strategy.on_data(data)

            # 3. 处理信号
            if signal:
                self._handle_signal(signal)

        except Exception as e:
            logger.error(f"处理市场数据失败: {e}")
            self.monitor.on_error(e, "market_data")

    def _store_market_data(self, data: Dict):
        """
        存储市场数据

        Args:
            data: 市场数据
        """
        try:
            # 检查是否为K线数据
            if 'data' in data and isinstance(data['data'], list):
                for candle in data['data']:
                    # OKX WebSocket K线格式
                    if len(candle) >= 6:
                        self.storage.insert_candlestick(
                            instrument_id=data.get('arg', {}).get('instId', ''),
                            timeframe=data.get('arg', {}).get('channel', '').replace('candle', ''),
                            timestamp=int(candle[0]),
                            open_price=float(candle[1]),
                            high=float(candle[2]),
                            low=float(candle[3]),
                            close=float(candle[4]),
                            volume=float(candle[5])
                        )
        except Exception as e:
            logger.error(f"存储K线数据失败: {e}")

    def _handle_signal(self, signal: Signal):
        """
        处理交易信号

        Args:
            signal: 交易信号
        """
        try:
            # 1. 记录信号
            self.monitor.on_signal(signal.__dict__)
            self.storage.insert_signal(
                strategy_name=self.strategy.name,
                instrument_id=signal.instrument_id,
                signal_type=signal.signal_type,
                price=signal.price,
                amount=signal.amount,
                reason=signal.reason
            )

            # 2. 风险检查
            # 计算订单价值
            order_value = signal.amount * signal.price if signal.amount else 0

            # 获取当前持仓
            positions = self.risk_manager.positions
            risk_result = self.risk_manager.check_order(
                symbol=signal.instrument_id,
                side=signal.signal_type,
                order_value=order_value,
                current_positions=positions
            )

            if not risk_result.passed:
                self.monitor.alert('warning', f"订单被拒绝: {risk_result.message}")
                return

            # 3. 执行订单
            self._execute_order(signal)

        except Exception as e:
            logger.error(f"处理信号失败: {e}")
            self.monitor.on_error(e, "handle_signal")

    def _execute_order(self, signal: Signal):
        """
        执行订单

        Args:
            signal: 交易信号
        """
        try:
            # 转换交易对格式
            symbol = signal.instrument_id.replace('-', '/')
            if ':USDT' not in symbol:
                symbol += ':USDT'

            # 下单
            order = self.executor.place_order(
                symbol=symbol,
                side=signal.signal_type,
                order_type='limit',
                price=signal.price,
                amount=signal.amount
            )

            self.monitor.on_order_placed(order)

            # 记录订单到数据库
            self.storage.insert_order(
                order_id=order.get('id'),
                instrument_id=signal.instrument_id,
                side=signal.signal_type,
                order_type='limit',
                price=signal.price,
                amount=signal.amount,
                status=order.get('status', 'open'),
                created_at=int(time.time()),
                raw_data=order
            )

            logger.info(f"订单已执行: {order['id']}")

        except Exception as e:
            logger.error(f"执行订单失败: {e}")
            self.monitor.on_order_failed(e, signal.__dict__)

    def _on_data_error(self, error):
        """数据采集器错误回调"""
        self.monitor.on_error(error, "data_collector")

    def _on_strategy_error(self, error: Exception):
        """策略错误回调"""
        self.monitor.on_error(error, "strategy")

    # 监控器回调（占位）
    def _on_signal_from_monitor(self, signal):
        pass

    def _on_order_from_monitor(self, order):
        pass

    def _on_error_from_monitor(self, error):
        pass

    def start(self):
        """启动系统"""
        if self.is_running:
            logger.warning("系统已在运行")
            return

        try:
            logger.info("正在启动系统...")

            # 启动策略
            self.strategy.start()

            # 启动监控器
            self.monitor.start()

            # 启动数据采集器
            self.data_collector.connect()

            # 订阅数据（假设使用BTC-USDT-SWAP）
            self.data_collector.subscribe_candlesticks('BTC-USDT-SWAP', bar='1H')

            self.is_running = True
            logger.info("系统已启动")

        except Exception as e:
            logger.error(f"启动系统失败: {e}")
            self.is_running = False
            raise

    def stop(self):
        """停止系统"""
        if not self.is_running:
            return

        logger.info("正在停止系统...")

        self.is_running = False

        # 停止各个组件
        if self.data_collector:
            self.data_collector.stop()

        if self.strategy:
            self.strategy.stop()

        if self.monitor:
            self.monitor.stop()

        if self.executor:
            self.executor.close()

        logger.info("系统已停止")

    def run(self):
        """运行系统（阻塞）"""
        self.start()

        # 注册信号处理
        def signal_handler(signum, frame):
            logger.info(f"收到信号 {signum}，准备退出...")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # 主循环
        try:
            while self.is_running:
                time.sleep(1)

                # 定期心跳
                if int(time.time()) % 30 == 0:
                    self.monitor.heartbeat()

                    # 定期打印摘要
                    if int(time.time()) % 300 == 0:
                        self.monitor.log_summary()

                        # 打印策略统计
                        stats = self.strategy.get_stats()
                        logger.info(f"策略统计: {stats}")

                        # 打印风险统计
                        risk_stats = self.risk_manager.get_stats()
                        logger.info(f"风险统计: {risk_stats}")

        except KeyboardInterrupt:
            logger.info("收到中断信号")
            self.stop()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='OKX交易系统')
    parser.add_argument('--config', '-c', default='.commander/okx_config.json',
                       help='配置文件路径')
    parser.add_argument('--simulated', '-s', action='store_true',
                       help='使用模拟模式')
    parser.add_argument('--live', action='store_true',
                       help='使用实盘模式（需要有效的API配置）')

    args = parser.parse_args()

    # 确定模式
    simulated = not args.live

    print(f"\n{'='*50}")
    print(f"OKX交易系统")
    print(f"模式: {'模拟' if simulated else '实盘'}")
    print(f"配置: {args.config}")
    print(f"{'='*50}\n")

    # 创建系统实例
    system = OKXTradingSystem(
        config_path=args.config,
        simulated=simulated
    )

    # 初始化系统
    if not system.initialize():
        logger.error("系统初始化失败，退出")
        sys.exit(1)

    # 运行系统
    system.run()


if __name__ == '__main__':
    main()
