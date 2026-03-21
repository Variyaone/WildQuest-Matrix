#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OKX模拟盘资金费套利测试脚本

功能：
1. 连接OKX模拟盘（sandbox mode）
2. 实时获取资金费率
3. 自动执行资金费套利策略
4. 记录详细日志和统计数据
5. 风控验证（仓位、杠杆、异常检测）

作者：架构师 🏗️
日期：2026-02-27
"""

import ccxt
import pandas as pd
import numpy as np
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import List, Optional, Any
from enum import Enum
import json
import os
import time
import logging
from logging.handlers import RotatingFileHandler


# ==================== 配置 ====================

# 路径配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORKSPACE_DIR = os.path.dirname(SCRIPT_DIR)
LOGS_DIR = os.path.join(WORKSPACE_DIR, 'results', 'simulation_logs')

# 从.env文件加载配置
def load_env_file(env_file: str = '.env') -> Dict[str, str]:
    """加载.env文件"""
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

# 加载.env文件
env_vars = load_env_file(os.path.join(SCRIPT_DIR, '.env'))
os.environ.update(env_vars)

# OKX模拟盘配置
OKX_API_KEY = os.environ.get('OKX_SIMULATION_API_KEY', env_vars.get('OKX_SIMULATION_API_KEY', ''))
OKX_SECRET_KEY = os.environ.get('OKX_SIMULATION_SECRET_KEY', env_vars.get('OKX_SIMULATION_SECRET_KEY', ''))
OKX_PASSPHRASE = os.environ.get('OKX_SIMULATION_PASSPHRASE', env_vars.get('OKX_SIMULATION_PASSPHRASE', ''))

# 策略参数
CONFIG = {
    'symbols': ['BTC/USDT:USDT', 'ETH/USDT:USDT'],  # 永续合约
    'entry_threshold': 0.001,      # 0.1% 入场阈值
    'exit_threshold': 0.0005,      # 0.05% 出场阈值
    'position_ratio': 0.20,        # 单币种仓位20%
    'max_leverage': 2,             # 最大杠杆2倍
    'max_drawdown': 0.10,          # 最大回撤10%
    'basis_alert_threshold': 0.01, # 1% 基差告警
    'funding_check_interval': 300, # 5分钟检查一次
    'funding_settlement_interval': 28800,  # 8小时结算周期
}


# ==================== 日志配置 ====================

def setup_logger(name: str, log_file: str) -> logging.Logger:
    """配置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # 清除现有处理器
    logger.handlers.clear()

    # 文件处理器 - 详细日志
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    # 控制台处理器 - 重要信息
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


# ==================== 数据类型定义 ====================

class PositionSide(Enum):
    """持仓方向"""
    LONG = 'long'
    SHORT = 'short'
    CLOSE = 'close'


@dataclass
class ArbitragePosition:
    """套利持仓"""
    symbol: str
    spot_side: PositionSide
    spot_size: float
    spot_entry_price: float
    futures_side: PositionSide
    futures_size: float
    futures_entry_price: float
    entry_time: datetime
    entry_funding_rate: float
    funding_income: float = 0.0
    settlement_count: int = 0

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['entry_time'] = self.entry_time.isoformat()
        data['spot_side'] = self.spot_side.value
        data['futures_side'] = self.futures_side.value
        return data


@dataclass
class TradingLog:
    """交易日志"""
    timestamp: datetime
    symbol: str
    action: str  # 'OPEN', 'CLOSE', 'ALERT'
    spot_side: Optional[str] = None
    spot_size: Optional[float] = None
    spot_price: Optional[float] = None
    futures_side: Optional[str] = None
    futures_size: Optional[float] = None
    futures_price: Optional[float] = None
    funding_rate: Optional[float] = None
    funding_income: Optional[float] = None
    pnl: Optional[float] = None
    reason: Optional[str] = None

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class StrategyMetrics:
    """策略指标"""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_equity: float = 0.0
    current_equity: float = 0.0
    total_funding_income: float = 0.0
    total_pnl_spot: float = 0.0
    total_pnl_futures: float = 0.0

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def drawdown_pct(self) -> float:
        """回撤百分比"""
        if self.peak_equity == 0:
            return 0.0
        return (self.peak_equity - self.current_equity) / self.peak_equity

    def to_dict(self) -> Dict:
        """转换为字典"""
        return asdict(self)


# ==================== OKX模拟盘连接 ====================

class OKXSimulationTrader:
    """OKX模拟盘交易"""

    def __init__(self, api_key: str, secret_key: str, passphrase: str, sandbox: bool = True):
        self.sandbox = sandbox
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret_key,
            'password': passphrase,
            'sandbox': sandbox,
            'enableRateLimit': True,
        })
        self.logger = setup_logger('OKXTrader', os.path.join(LOGS_DIR, 'okx_trader.log'))
        self.logger.info(f"✅ OKX连接初始化完成 (模拟盘: {sandbox})")

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            balance = self.exchange.fetch_balance(params={'instType': 'SPOT'})
            self.logger.info(f"✅ 连接成功，账户余额: {balance.get('USDT', {}).get('total', 0)} USDT")
            return True
        except Exception as e:
            self.logger.error(f"❌ 连接失败: {e}")
            return False

    def get_account_balance(self) -> float:
        """获取账户余额"""
        try:
            balance = self.exchange.fetch_balance()
            return balance.get('USDT', {}).get('total', 0)
        except Exception as e:
            self.logger.error(f"获取余额失败: {e}")
            return 0.0

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """获取资金费率"""
        try:
            markets = self.exchange.load_markets()
            if symbol not in markets:
                self.logger.warning(f"市场 {symbol} 不存在")
                return None

            ticker = self.exchange.fetch_funding_rate(symbol)
            funding_rate = ticker.get('fundingRate', 0.0)
            self.logger.debug(f"{symbol} 资金费率: {funding_rate:.6f}")
            return funding_rate
        except Exception as e:
            self.logger.error(f"获取 {symbol} 资金费率失败: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        """获取当前价格"""
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return ticker.get('last', 0.0)
        except Exception as e:
            self.logger.error(f"获取 {symbol} 价格失败: {e}")
            return None

    def get_ticker_for_futures_and_spot(self, symbol: str) -> Dict[str, float]:
        """获取合约和现货价格"""
        try:
            futures_price = self.get_current_price(symbol)
            if futures_price is None:
                return {}

            spot_symbol = symbol.replace(':USDT', '').replace('/USDT:USDT', '/USDT')
            spot_price = self.get_current_price(spot_symbol)

            if spot_price is None:
                self.logger.warning(f"无法获取 {spot_symbol} 现货价格")
                return {'futures_price': futures_price}

            return {
                'futures_price': futures_price,
                'spot_price': spot_price
            }
        except Exception as e:
            self.logger.error(f"获取价格失败: {e}")
            return {}

    def place_order(self, symbol: str, side: str, amount: float, order_type: str = 'market', leverage: Optional[int] = None) -> Optional[str]:
        """下单"""
        try:
            params = {}

            if leverage is not None and leverage > 1:
                try:
                    self.exchange.set_leverage(leverage, symbol)
                    self.logger.info(f"设置杠杆 {leverage}x: {symbol}")
                except Exception as e:
                    self.logger.warning(f"设置杠杆失败: {e}")

            order = self.exchange.create_order(
                symbol=symbol, type=order_type, side=side, amount=amount, params=params
            )

            order_id = order.get('id', '')
            self.logger.info(f"✅ 下单成功: {side} {amount:.6f} {symbol} | 订单ID: {order_id}")
            return order_id
        except Exception as e:
            self.logger.error(f"❌ 下单失败: {e}")
            return None

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """获取持仓"""
        try:
            positions = self.exchange.fetch_positions([symbol] if symbol else None)
            active_positions = [p for p in positions if float(p.get('contracts', 0)) != 0]
            return active_positions
        except Exception as e:
            self.logger.error(f"获取持仓失败: {e}")
            return []

    def close_position(self, symbol: str) -> bool:
        """平仓"""
        try:
            positions = self.get_positions(symbol)
            for position in positions:
                side = position.get('side', '')
                amount = float(position.get('contracts', 0))
                if amount == 0:
                    continue
                close_side = 'sell' if side == 'long' else 'buy'
                self.place_order(symbol, close_side, amount)
            self.logger.info(f"✅ 平仓成功: {symbol}")
            return True
        except Exception as e:
            self.logger.error(f"❌ 平仓失败: {e}")
            return False


# ==================== 资金费套利策略（实时版） ====================

class FundingRateArbitrageSimulation:
    """资金费套利策略 - 模拟盘测试"""

    def __init__(self, trader: OKXSimulationTrader, config: Dict[str, Any]):
        self.trader = trader
        self.symbols = config.get('symbols', CONFIG['symbols'])
        self.entry_threshold = config.get('entry_threshold', CONFIG['entry_threshold'])
        self.exit_threshold = config.get('exit_threshold', CONFIG['exit_threshold'])
        self.position_ratio = config.get('position_ratio', CONFIG['position_ratio'])
        self.max_leverage = config.get('max_leverage', CONFIG['max_leverage'])
        self.max_drawdown = config.get('max_drawdown', CONFIG['max_drawdown'])
        self.basis_alert_threshold = config.get('basis_alert_threshold', CONFIG['basis_alert_threshold'])
        self.funding_check_interval = config.get('funding_check_interval', CONFIG['funding_check_interval'])
        self.funding_settlement_interval = config.get('funding_settlement_interval', CONFIG['funding_settlement_interval'])

        self.logger = setup_logger('ArbitrageStrategy', os.path.join(LOGS_DIR, 'strategy.log'))

        self.positions: Dict[str, ArbitragePosition] = {}
        self.trade_history: List[TradingLog] = []
        self.funding_history: List[Dict] = []
        self.equity_curve: List[Dict] = []
        self.metrics = StrategyMetrics()

        self.initial_capital = self.trader.get_account_balance()
        self.metrics.current_equity = self.initial_capital
        self.metrics.peak_equity = self.initial_capital
        self.last_settlement_time: Optional[datetime] = None

        self.logger.info("="*60)
        self.logger.info("资金费套利策略初始化完成")
        self.logger.info(f"   交易对: {self.symbols}")
        self.logger.info(f"   入场阈值: {self.entry_threshold*100:.2f}%")
        self.logger.info(f"   出场阈值: {self.exit_threshold*100:.2f}%")
        self.logger.info(f"   单币种仓位: {self.position_ratio*100:.0f}%")
        self.logger.info(f"   最大杠杆: {self.max_leverage}x")
        self.logger.info(f"   最大回撤: {self.max_drawdown*100:.0f}%")
        self.logger.info(f"   初始资金: ${self.initial_capital:,.2f}")
        self.logger.info("="*60)

    def run(self, duration_hours: int = 72):
        """运行策略"""
        end_time = datetime.now() + timedelta(hours=duration_hours)
        self.logger.info(f"\n开始运行策略，预计运行 {duration_hours} 小时")
        self.logger.info(f"结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")

        try:
            while datetime.now() < end_time:
                self._run_one_iteration()
                self._save_state()
                time.sleep(self.funding_check_interval)
        except KeyboardInterrupt:
            self.logger.info("\n⚠️ 用户中断，停止策略")
        finally:
            self._cleanup()
            self._generate_report()

    def _run_one_iteration(self):
        """执行一次迭代"""
        current_time = datetime.now()
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"[{current_time.strftime('%Y-%m-%d %H:%M:%S')}] 执行检查")
        self.logger.info(f"{'='*60}")

        self._update_equity()
        self._check_funding_settlement(current_time)
        self._process_trading_signals(current_time)
        self._check_drawdown()
        self._check_basis_risk(current_time)
        self._print_status()

    def _update_equity(self):
        """更新资金"""
        current_equity = self.trader.get_account_balance()
        self.metrics.current_equity = current_equity
        self.metrics.peak_equity = max(self.metrics.peak_equity, current_equity)
        self.metrics.max_drawdown = max(self.metrics.max_drawdown, self.metrics.drawdown_pct)

        self.equity_curve.append({
            'timestamp': datetime.now().isoformat(),
            'equity': current_equity,
            'realized_pnl': self.metrics.total_pnl,
            'drawdown': self.metrics.drawdown_pct
        })

    def _check_funding_settlement(self, current_time: datetime):
        """检查并结算资金费"""
        if self.last_settlement_time is None:
            self.last_settlement_time = current_time
            return

        time_since_last = (current_time - self.last_settlement_time).total_seconds()

        if time_since_last >= self.funding_settlement_interval:
            self.logger.info("执行资金费结算...")

            for symbol, position in self.positions.items():
                funding_rate = self.trader.get_funding_rate(symbol)
                if funding_rate is None:
                    continue

                nominal_value = position.futures_size * position.futures_entry_price

                if position.futures_side == PositionSide.SHORT:
                    funding_income = nominal_value * funding_rate * (time_since_last / self.funding_settlement_interval)
                else:
                    funding_income = -nominal_value * funding_rate * (time_since_last / self.funding_settlement_interval)

                position.funding_income += funding_income
                position.settlement_count += 1

                self.funding_history.append({
                    'timestamp': current_time.isoformat(),
                    'symbol': symbol,
                    'funding_rate': funding_rate,
                    'funding_income': funding_income,
                    'total_funding': position.funding_income
                })

                self.logger.info(f"  {symbol} 资金费结算: ${funding_income:.2f} | 累计: ${position.funding_income:.2f}")

            self.metrics.total_funding_income += sum(p.funding_income for p in self.positions.values())
            self.last_settlement_time = current_time

    def _process_trading_signals(self, current_time: datetime):
        """处理交易信号"""
        for symbol in self.symbols:
            funding_rate = self.trader.get_funding_rate(symbol)
            if funding_rate is None:
                continue

            has_position = symbol in self.positions

            if not has_position:
                if abs(funding_rate) > self.entry_threshold:
                    self._open_position(symbol, funding_rate, current_time)
            else:
                if abs(funding_rate) < self.exit_threshold:
                    self._close_position(symbol, current_time, reason="费率低于阈值")

    def _open_position(self, symbol: str, funding_rate: float, current_time: datetime):
        """开仓套利对"""
        prices = self.trader.get_ticker_for_futures_and_spot(symbol)
        if 'futures_price' not in prices:
            self.logger.warning(f"无法获取 {symbol} 价格，跳过开仓")
            return

        futures_price = prices['futures_price']
        spot_price = prices.get('spot_price', futures_price)

        available_capital = self.metrics.current_equity
        position_value = available_capital * self.position_ratio
        leveraged_position = position_value * min(self.max_leverage, 2)
        contract_size = leveraged_position / futures_price

        if funding_rate > 0:
            side = 'sell'
            position_side = PositionSide.SHORT
        else:
            self.logger.info(f"{symbol} 费率为负 ({funding_rate:.6f})，跳过开仓")
            return

        order_id = self.trader.place_order(
            symbol=symbol,
            side=side,
            amount=contract_size,
            leverage=min(self.max_leverage, 2)
        )

        if order_id is None:
            self.logger.error(f"开仓失败: {symbol}")
            return

        position = ArbitragePosition(
            symbol=symbol,
            spot_side=PositionSide.CLOSE,
            spot_size=0.0,
            spot_entry_price=spot_price,
            futures_side=position_side,
            futures_size=contract_size,
            futures_entry_price=futures_price,
            entry_time=current_time,
            entry_funding_rate=funding_rate
        )

        self.positions[symbol] = position

        log = TradingLog(
            timestamp=current_time,
            symbol=symbol,
            action='OPEN',
            futures_side=position_side.value,
            futures_size=contract_size,
            futures_price=futures_price,
            funding_rate=funding_rate
        )
        self.trade_history.append(log)

        self.logger.info(f"  [开仓] {symbol}")
        self.logger.info(f"    费率: {funding_rate:.4f} ({funding_rate*100:.2f}%)")
        self.logger.info(f"    方向: {position_side.value}")
        self.logger.info(f"    仓位: {contract_size:.6f} @ ${futures_price:.2f}")
        self.logger.info(f"    价值: ${leveraged_position:,.2f}")

    def _close_position(self, symbol: str, current_time: datetime, reason: str):
        """平仓套利对"""
        if symbol not in self.positions:
            return

        position = self.positions[symbol]

        prices = self.trader.get_ticker_for_futures_and_spot(symbol)
        if 'futures_price' not in prices:
            self.logger.warning(f"无法获取 {symbol} 价格，跳过平仓")
            return

        current_futures_price = prices['futures_price']
        current_spot_price = prices.get('spot_price', current_futures_price)

        contract_size = position.futures_size
        entry_price = position.futures_entry_price

        if position.futures_side == PositionSide.SHORT:
            futures_pnl = (entry_price - current_futures_price) * contract_size
        else:
            futures_pnl = (current_futures_price - entry_price) * contract_size

        total_pnl = futures_pnl + position.funding_income

        self.metrics.total_trades += 1
        if total_pnl > 0:
            self.metrics.winning_trades += 1
        else:
            self.metrics.losing_trades += 1

        self.metrics.total_pnl += total_pnl
        self.metrics.total_pnl_futures += futures_pnl
        self.metrics.total_funding_income += position.funding_income

        log = TradingLog(
            timestamp=current_time,
            symbol=symbol,
            action='CLOSE',
            futures_side=position.futures_side.value,
            futures_size=contract_size,
            futures_price=current_futures_price,
            funding_rate=None,
            funding_income=position.funding_income,
            pnl=total_pnl,
            reason=reason
        )
        self.trade_history.append(log)

        success = self.trader.close_position(symbol)

        del self.positions[symbol]

        self.logger.info(f"  [平仓] {symbol}")
        self.logger.info(f"    原因: {reason}")
        self.logger.info(f"    入场价: ${entry_price:.2f}")
        self.logger.info(f"    平仓价: ${current_futures_price:.2f}")
        self.logger.info(f"    价格盈亏: ${futures_pnl:,.2f}")
        self.logger.info(f"    资金费收益: ${position.funding_income:.2f}")
        self.logger.info(f"    总盈亏: ${total_pnl:,.2f}")
        self.logger.info(f"    结算次数: {position.settlement_count}")

    def _check_drawdown(self):
        """检查回撤"""
        if self.metrics.drawdown_pct > self.max_drawdown:
            self.logger.warning(f"⚠️  回撤 {self.metrics.drawdown_pct*100:.2f}% 超过最大值 {self.max_drawdown*100:.0f}%")
            for symbol in list(self.positions.keys()):
                self._close_position(symbol, datetime.now(), reason="回撤超限，强制平仓")

    def _check_basis_risk(self, current_time: datetime):
        """检查基差风险"""
        for symbol, position in self.positions.items():
            prices = self.trader.get_ticker_for_futures_and_spot(symbol)
            if 'futures_price' not in prices or 'spot_price' not in prices:
                continue

            current_futures_price = prices['futures_price']
            current_spot_price = prices['spot_price']

            current_basis = (current_futures_price - current_spot_price) / current_spot_price
            entry_basis = (position.futures_entry_price - position.spot_entry_price) / position.spot_entry_price
            basis_change = current_basis - entry_basis

            if abs(basis_change) > self.basis_alert_threshold:
                self.logger.warning(f"⚠️  {symbol} 基差变化 {basis_change*100:.2f}% 超过阈值 {self.basis_alert_threshold*100:.0f}%")
                log = TradingLog(
                    timestamp=current_time,
                    symbol=symbol,
                    action='ALERT',
                    pnl=None,
                    reason=f"基差风险: {basis_change*100:.2f}%"
                )
                self.trade_history.append(log)

    def _print_status(self):
        """打印当前状态"""
        self.logger.info(f"\n------ 当前状态 ------")
        self.logger.info(f"账户资金: ${self.metrics.current_equity:,.2f}")
        self.logger.info(f"总盈亏: ${self.metrics.total_pnl:,.2f}")
        self.logger.info(f"资金费收益: ${self.metrics.total_funding_income:,.2f}")
        self.logger.info(f"回撤: {self.metrics.drawdown_pct*100:.2f}%")
        self.logger.info(f"交易次数: {self.metrics.total_trades}")
        self.logger.info(f"当前持仓: {len(self.positions)}")

        for symbol, position in self.positions.items():
            self.logger.info(f"  {symbol}: {position.futures_side.value} {position.futures_size:.6f}")
            self.logger.info(f"    入场费率: {position.entry_funding_rate:.4f}")
            self.logger.info(f"    资金费收益: ${position.funding_income:.2f}")
            self.logger.info(f"    持仓时长: {(datetime.now() - position.entry_time).total_seconds() / 3600:.1f}h")

    def _save_state(self):
        """保存状态到文件"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        trades_file = os.path.join(LOGS_DIR, f'trades_{timestamp}.json')
        with open(trades_file, 'w', encoding='utf-8') as f:
            json.dump([log.to_dict() for log in self.trade_history], f, indent=2, ensure_ascii=False)

        funding_file = os.path.join(LOGS_DIR, f'funding_{timestamp}.json')
        with open(funding_file, 'w', encoding='utf-8') as f:
            json.dump(self.funding_history, f, indent=2, ensure_ascii=False)

        equity_file = os.path.join(LOGS_DIR, f'equity_{timestamp}.json')
        with open(equity_file, 'w', encoding='utf-8') as f:
            json.dump(self.equity_curve, f, indent=2, ensure_ascii=False)

        positions_file = os.path.join(LOGS_DIR, f'positions_{timestamp}.json')
        with open(positions_file, 'w', encoding='utf-8') as f:
            json.dump({symbol: pos.to_dict() for symbol, pos in self.positions.items()}, f, indent=2, ensure_ascii=False)

    def _cleanup(self):
        """清理：平仓所有持仓"""
        self.logger.info("\n执行清理...")
        for symbol in list(self.positions.keys()):
            self._close_position(symbol, datetime.now(), reason="策略停止")
        self.logger.info("✅ 清理完成")

    def _generate_report(self):
        """生成测试报告"""
        report_file = os.path.join(WORKSPACE_DIR, '.commander', 'simulation_test_report.md')

        # 计算统计指标
        duration_hours = 0
        if len(self.equity_curve) > 0:
            start_time = datetime.fromisoformat(self.equity_curve[0]['timestamp'])
            duration_hours = (datetime.now() - start_time).total_seconds() / 3600

        total_return = (self.metrics.current_equity - self.initial_capital) / self.initial_capital if self.initial_capital > 0 else 0
        annual_return = (1 + total_return) ** (8760 / max(duration_hours, 1)) - 1 if duration_hours > 0 else 0

        # 计算夏普比率
        sharpe_ratio = 0
        if len(self.equity_curve) > 1:
            equity_df = pd.DataFrame(self.equity_curve)
            equity_df['returns'] = equity_df['equity'].pct_change()
            equity_df['returns'] = equity_df['returns'].replace([np.inf, -np.inf], np.nan)
            mean_return = equity_df['returns'].mean()
            std_return = equity_df['returns'].std()
            if std_return > 0:
                sharpe_ratio = mean_return / std_return

        # 计算平均持仓时长
        avg_duration = 0
        if len(self.trade_history) > 0:
            open_logs = [log for log in self.trade_history if log.action == 'OPEN']
            close_logs = [log for log in self.trade_history if log.action == 'CLOSE']

            if len(open_logs) == len(close_logs) and len(open_logs) > 0:
                durations = []
                for open_log in open_logs:
                    matching_close = next(
                        (c for c in close_logs if c.symbol == open_log.symbol and c.timestamp > open_log.timestamp),
                        None
                    )
                    if matching_close:
                        duration = (matching_close.timestamp - open_log.timestamp).total_seconds() / 3600
                        durations.append(duration)

                if durations:
                    avg_duration = sum(durations) / len(durations)

        # 生成报告
        report = f"""# OKX模拟盘资金费套利测试报告

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**测试时长**: {duration_hours:.1f} 小时

---

## 一、测试概况

- 测试环境: OKX模拟盘 (Sandbox)
- 交易对: {', '.join(self.symbols)}
- 入场阈值: {self.entry_threshold*100:.2f}%
- 出场阈值: {self.exit_threshold*100:.2f}%
- 单币种仓位: {self.position_ratio*100:.0f}%
- 最大杠杆: {self.max_leverage}x

---

## 二、收益指标

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 初始资金 | ${self.initial_capital:,.2f} | - | - |
| 最终资金 | ${self.metrics.current_equity:,.2f} | - | - |
| 总收益 | ${self.metrics.total_pnl:,.2f} | - | - |
| 总收益率 | {total_return*100:.2f}% | - | - |
| 年化收益率 | {annual_return*100:.2f}% | >20% | {'✅' if annual_return > 0.20 else '❌'} |
| 资金费收益 | ${self.metrics.total_funding_income:,.2f} | - | - |
| 资金费占比 | {(self.metrics.total_funding_income / self.metrics.total_pnl * 100 if self.metrics.total_pnl != 0 else 0):.1f}% | - | - |

---

## 三、风险指标

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 最大回撤 | {self.metrics.max_drawdown*100:.2f}% | <10% | {'✅' if self.metrics.max_drawdown < 0.10 else '❌'} |
| 夏普比率 | {sharpe_ratio:.2f} | >1.5 | {'✅' if sharpe_ratio > 1.5 else '❌'} |

---

## 四、交易指标

| 指标 | 数值 | 目标 | 状态 |
|------|------|------|------|
| 总交易次数 | {self.metrics.total_trades} | - | - |
| 盈利次数 | {self.metrics.winning_trades} | - | - |
| 亏损次数 | {self.metrics.losing_trades} | - | - |
| 胜率 | {self.metrics.win_rate*100:.1f}% | >70% | {'✅' if self.metrics.win_rate > 0.70 else '❌'} |
| 平均持仓时长 | {avg_duration:.1f}h | - | - |

---

## 五、持仓记录

**当前持仓数量**: {len(self.positions)}

"""

        if self.positions:
            report += "\n### 持仓详情\n\n"
            for symbol, position in self.positions.items():
                duration_hours_held = (datetime.now() - position.entry_time).total_seconds() / 3600
                report += f"- **{symbol}**\n"
                report += f"  - 方向: {position.futures_side.value}\n"
                report += f"  - 数量: {position.futures_size:.6f}\n"
                report += f"  - 入场价: ${position.futures_entry_price:.2f}\n"
                report += f"  - 入场费率: {position.entry_funding_rate:.4f}\n"
                report += f"  - 资金费收益: ${position.funding_income:.2f}\n"
                report += f"  - 持仓时长: {duration_hours_held:.1f}h\n"
                report += f"  - 结算次数: {position.settlement_count}\n"
        else:
            report += "\n当前无持仓\n"

        # 六、交易历史（最近10笔）
        report += "\n\n## 六、交易历史（最近10笔）\n\n"

        recent_trades = self.trade_history[-10:] if self.trade_history else []
        if recent_trades:
            report += "| 时间 | 交易对 | 操作 | 方向 | 价格 | 数量 | 资金费 | 盈亏 | 原因 |\n"
            report += "|------|--------|------|------|------|------|--------|------|------|\n"
            for trade in recent_trades:
                time_str = trade.timestamp.strftime('%H:%M:%S')
                action_emj = "🟢 开仓" if trade.action == 'OPEN' else "🔴 平仓" if trade.action == 'CLOSE' else "⚠️ 告警"
                price_str = f"${trade.futures_price:.2f}" if trade.futures_price else "-"
                size_str = f"{trade.futures_size:.6f}" if trade.futures_size else "-"
                funding_str = f"${trade.funding_income:.2f}" if trade.funding_income else "-"
                pnl_str = f"${trade.pnl:.2f}" if trade.pnl else "-"
                report += f"| {time_str} | {trade.symbol} | {action_emj} | {trade.futures_side or '-'} | {price_str} | {size_str} | {funding_str} | {pnl_str} | {trade.reason or '-'} |\n"
        else:
            report += "暂无交易记录\n"

        # 七、结论
        report += "\n\n## 七、总结\n\n"

        if total_return > 0:
            report += f"✅ 测试期间策略盈利 ${self.metrics.total_pnl:,.2f}，收益率 {total_return*100:.2f}%。"
        else:
            report += f"❌ 测试期间策略亏损 ${abs(self.metrics.total_pnl):,.2f}，收益率 {total_return*100:.2f}%。"

        if annual_return > 0.20 and self.metrics.win_rate > 0.70 and self.metrics.max_drawdown < 0.10:
            report += "\n\n✅ 策略表现良好，达到预期目标，可以考虑实盘测试。"
        else:
            report += "\n\n⚠️ 策略表现未达到预期目标，需要进一步优化。"

        report += "\n\n---\n\n**报告由模拟盘测试脚本自动生成**"

        # 保存报告
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        self.logger.info(f"\n✅ 测试报告已生成: {report_file}")


# ==================== 主函数 ====================

def main():
    """主函数"""
    print("\n" + "="*60)
    print("OKX模拟盘资金费套利测试")
    print("="*60 + "\n")

    # 检查API密钥
    if not OKX_API_KEY or not OKX_SECRET_KEY or not OKX_PASSPHRASE:
        print("⚠️  错误：未配置OKX API密钥")
        print("\n请设置以下环境变量：")
        print("  export OKX_SIMULATION_API_KEY='your-api-key'")
        print("  export OKX_SIMULATION_SECRET_KEY='your-secret-key'")
        print("  export OKX_SIMULATION_PASSPHRASE='your-passphrase'")
        print("\n或在OKX官网申请模拟盘API密钥：")
        print("  https://www.okx.com/account/my-api")
        return

    # 创建OKX交易实例
    trader = OKXSimulationTrader(
        api_key=OKX_API_KEY,
        secret_key=OKX_SECRET_KEY,
        passphrase=OKX_PASSPHRASE,
        sandbox=True  # 使用模拟盘
    )

    # 测试连接
    if not trader.test_connection():
        print("❌ 连接OKX模拟盘失败，请检查API密钥")
        return
    # 创建策略实例
    strategy = FundingRateArbitrageSimulation(trader, CONFIG)

    # 运行策略（测试48小时）
    duration_hours = 48
    print(f"\n开始运行测试（{duration_hours}小时）...")
    print("按 Ctrl+C 可随时停止\n")

    strategy.run(duration_hours=duration_hours)

    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == "__main__":
    main()
