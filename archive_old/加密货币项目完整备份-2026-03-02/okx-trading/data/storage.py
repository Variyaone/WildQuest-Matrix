"""
数据存储模块
使用SQLite存储历史K线数据和订单记录
"""

import sqlite3
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class Storage:
    """
    数据存储管理类
    使用SQLite数据库存储K线数据和订单记录
    """

    def __init__(self, db_path: str = 'data/okx_trading.db'):
        """
        初始化存储

        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)

        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化数据库
        self._init_db()

    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建K线数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candlesticks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_id TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                open REAL NOT NULL,
                high REAL NOT NULL,
                low REAL NOT NULL,
                close REAL NOT NULL,
                volume REAL NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now')),
                UNIQUE(instrument_id, timeframe, timestamp)
            )
        ''')

        # 创建订单记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id TEXT UNIQUE NOT NULL,
                instrument_id TEXT NOT NULL,
                side TEXT NOT NULL,
                order_type TEXT NOT NULL,
                price REAL,
                amount REAL NOT NULL,
                filled_amount REAL DEFAULT 0,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER DEFAULT (strftime('%s', 'now')),
                raw_data TEXT
            )
        ''')

        # 创建仓位记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_id TEXT NOT NULL UNIQUE,
                position_side TEXT NOT NULL,
                size REAL NOT NULL,
                entry_price REAL,
                unrealized_pnl REAL DEFAULT 0,
                margin REAL DEFAULT 0,
                updated_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')

        # 创建交易日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument_id TEXT NOT NULL,
                side TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                trade_id TEXT,
                trade_time INTEGER NOT NULL,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')

        # 创建策略信号表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                instrument_id TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                price REAL NOT NULL,
                amount REAL,
                reason TEXT,
                created_at INTEGER DEFAULT (strftime('%s', 'now'))
            )
        ''')

        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_candlesticks_inst_time ON candlesticks(instrument_id, timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_inst_time ON orders(instrument_id, created_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(created_at)')

        conn.commit()
        conn.close()

        logger.info(f"数据库初始化完成: {self.db_path}")

    # ========== K线数据 ==========

    def insert_candlestick(
        self,
        instrument_id: str,
        timeframe: str,
        timestamp: int,
        open_price: float,
        high: float,
        low: float,
        close: float,
        volume: float
    ) -> bool:
        """
        插入K线数据

        Args:
            instrument_id: 交易对
            timeframe: 时间周期
            timestamp: 时间戳
            open_price: 开盘价
            high: 最高价
            low: 最低价
            close: 收盘价
            volume: 成交量

        Returns:
            是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO candlesticks
                (instrument_id, timeframe, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (instrument_id, timeframe, timestamp, open_price, high, low, close, volume))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"插入K线数据失败: {e}")
            return False

    def insert_candlesticks_batch(self, klines: List[Dict]) -> int:
        """
        批量插入K线数据

        Args:
            klines: K线数据列表，每条包含 instrument_id, timeframe, timestamp, open, high, low, close, volume

        Returns:
            成功插入的数量
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            inserted = 0
            for kline in klines:
                cursor.execute('''
                    INSERT OR REPLACE INTO candlesticks
                    (instrument_id, timeframe, timestamp, open, high, low, close, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    kline['instrument_id'],
                    kline['timeframe'],
                    kline['timestamp'],
                    kline['open'],
                    kline['high'],
                    kline['low'],
                    kline['close'],
                    kline['volume']
                ))
                inserted += 1

            conn.commit()
            conn.close()

            logger.info(f"批量插入K线数据: {inserted} 条")
            return inserted

        except Exception as e:
            logger.error(f"批量插入K线数据失败: {e}")
            return 0

    def get_candlesticks(
        self,
        instrument_id: str,
        timeframe: str,
        limit: int = 100,
        before: int = None
    ) -> List[Dict]:
        """
        获取K线数据

        Args:
            instrument_id: 交易对
            timeframe: 时间周期
            limit: 数量限制
            before: 获取指定时间之前的数据

        Returns:
            K线数据列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            sql = '''
                SELECT timestamp, open, high, low, close, volume
                FROM candlesticks
                WHERE instrument_id = ? AND timeframe = ?
            '''
            params = [instrument_id, timeframe]

            if before:
                sql += ' AND timestamp < ?'
                params.append(before)

            sql += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)

            cursor.execute(sql, params)

            results = []
            for row in cursor.fetchall():
                results.append({
                    'timestamp': row['timestamp'],
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                })

            conn.close()

            # 按时间正序返回
            results.reverse()
            return results

        except Exception as e:
            logger.error(f"获取K线数据失败: {e}")
            return []

    # ========== 订单记录 ==========

    def insert_order(
        self,
        order_id: str,
        instrument_id: str,
        side: str,
        order_type: str,
        price: Optional[float],
        amount: float,
        status: str,
        created_at: int,
        raw_data: Dict = None
    ) -> bool:
        """
        插入订单记录

        Args:
            order_id: 订单ID
            instrument_id: 交易对
            side: 买卖方向
            order_type: 订单类型
            price: 价格
            amount: 数量
            status: 状态
            created_at: 创建时间
            raw_data: 原始数据

        Returns:
            是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            raw_json = json.dumps(raw_data) if raw_data else None

            cursor.execute('''
                INSERT OR REPLACE INTO orders
                (order_id, instrument_id, side, order_type, price, amount, status, created_at, raw_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (order_id, instrument_id, side, order_type, price, amount, status, created_at, raw_json))

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"插入订单记录失败: {e}")
            return False

    def update_order_status(self, order_id: str, status: str, filled_amount: float = None):
        """
        更新订单状态

        Args:
            order_id: 订单ID
            status: 新状态
            filled_amount: 成交数量
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if filled_amount is not None:
                cursor.execute('''
                    UPDATE orders
                    SET status = ?, filled_amount = ?, updated_at = strftime('%s', 'now')
                    WHERE order_id = ?
                ''', (status, filled_amount, order_id))
            else:
                cursor.execute('''
                    UPDATE orders
                    SET status = ?, updated_at = strftime('%s', 'now')
                    WHERE order_id = ?
                ''', (status, order_id))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新订单状态失败: {e}")

    def get_orders(
        self,
        instrument_id: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取订单记录

        Args:
            instrument_id: 交易对（可选）
            status: 状态（可选）
            limit: 数量限制

        Returns:
            订单列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            sql = 'SELECT * FROM orders WHERE 1=1'
            params = []

            if instrument_id:
                sql += ' AND instrument_id = ?'
                params.append(instrument_id)

            if status:
                sql += ' AND status = ?'
                params.append(status)

            sql += ' ORDER BY created_at DESC LIMIT ?'
            params.append(limit)

            cursor.execute(sql, params)

            results = []
            for row in cursor.fetchall():
                results.append(dict(row))

            conn.close()
            return results

        except Exception as e:
            logger.error(f"获取订单记录失败: {e}")
            return []

    # ========== 仓位记录 ==========

    def update_position(
        self,
        instrument_id: str,
        position_side: str,
        size: float,
        entry_price: float = None,
        unrealized_pnl: float = 0,
        margin: float = 0
    ):
        """
        更新仓位记录

        Args:
            instrument_id: 交易对
            position_side: 仓位方向
            size: 仓位大小
            entry_price: 入场价格
            unrealized_pnl: 未实现盈亏
            margin: 保证金
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO positions
                (instrument_id, position_side, size, entry_price, unrealized_pnl, margin, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, strftime('%s', 'now'))
            ''', (instrument_id, position_side, size, entry_price, unrealized_pnl, margin))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"更新仓位记录失败: {e}")

    def get_positions(self, instrument_id: str = None) -> List[Dict]:
        """
        获取仓位记录

        Args:
            instrument_id: 交易对（可选）

        Returns:
            仓位列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if instrument_id:
                cursor.execute('SELECT * FROM positions WHERE instrument_id = ?', (instrument_id,))
            else:
                cursor.execute('SELECT * FROM positions')

            results = []
            for row in cursor.fetchall():
                results.append(dict(row))

            conn.close()
            return results

        except Exception as e:
            logger.error(f"获取仓位记录失败: {e}")
            return []

    # ========== 交易日志 ==========

    def insert_trade_log(
        self,
        instrument_id: str,
        side: str,
        price: float,
        amount: float,
        trade_id: str = None,
        trade_time: int = None
    ):
        """
        插入交易日志

        Args:
            instrument_id: 交易对
            side: 买卖方向
            price: 成交价格
            amount: 成交数量
            trade_id: 成交ID
            trade_time: 成交时间
        """
        try:
            if trade_time is None:
                trade_time = int(datetime.now().timestamp())

            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO trade_logs
                (instrument_id, side, price, amount, trade_id, trade_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (instrument_id, side, price, amount, trade_id, trade_time))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"插入交易日志失败: {e}")

    # ========== 策略信号 ==========

    def insert_signal(
        self,
        strategy_name: str,
        instrument_id: str,
        signal_type: str,
        price: float,
        amount: float = None,
        reason: str = None
    ):
        """
        记录策略信号

        Args:
            strategy_name: 策略名称
            instrument_id: 交易对
            signal_type: 信号类型 (buy/sell/close)
            price: 价格
            amount: 数量
            reason: 原因
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO signals
                (strategy_name, instrument_id, signal_type, price, amount, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (strategy_name, instrument_id, signal_type, price, amount, reason))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"记录策略信号失败: {e}")

    def get_signals(
        self,
        strategy_name: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        获取策略信号

        Args:
            strategy_name: 策略名称（可选）
            limit: 数量限制

        Returns:
            信号列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if strategy_name:
                cursor.execute('''
                    SELECT * FROM signals
                    WHERE strategy_name = ?
                    ORDER BY created_at DESC LIMIT ?
                ''', (strategy_name, limit))
            else:
                cursor.execute('''
                    SELECT * FROM signals
                    ORDER BY created_at DESC LIMIT ?
                ''', (limit,))

            results = []
            for row in cursor.fetchall():
                results.append(dict(row))

            conn.close()
            return results

        except Exception as e:
            logger.error(f"获取策略信号失败: {e}")
            return []

    # ========== 清理 ==========

    def cleanup_old_data(self, days: int = 30):
        """
        清理旧数据

        Args:
            days: 保留天数
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cutoff_time = int((datetime.now().timestamp() - days * 86400)) * 1000  # 转换为毫秒

            # 清理K线数据
            cursor.execute('DELETE FROM candlesticks WHERE timestamp < ?', (cutoff_time,))
            klines_deleted = cursor.rowcount

            # 清理交易日志
            cursor.execute('DELETE FROM trade_logs WHERE trade_time < ? / 1000', (cutoff_time,))
            trades_deleted = cursor.rowcount

            conn.commit()
            conn.close()

            logger.info(f"清理完成: K线数据 {klines_deleted} 条, 交易日志 {trades_deleted} 条")

        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
