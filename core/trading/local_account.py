"""
本地账户追踪器

功能:
- 整合 PositionManager 持仓管理
- 记录每日净值曲线
- 计算真实收益指标
- 支持交易反馈机制
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

from core.trading.position import PositionManager
from core.infrastructure.config import get_data_paths

logger = logging.getLogger(__name__)


@dataclass
class EquityPoint:
    """净值数据点"""
    date: str
    total_value: float
    cash: float
    position_value: float
    daily_return: float = 0.0
    cumulative_return: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass 
class TradeFeedback:
    """交易反馈记录"""
    trade_id: str
    signal_id: str
    stock_code: str
    stock_name: str
    side: str
    requested_quantity: int
    requested_price: float
    executed_quantity: int = 0
    executed_price: float = 0.0
    status: str = "pending"
    feedback_time: str = ""
    notes: str = ""
    
    def to_dict(self) -> Dict:
        return asdict(self)


class LocalAccountTracker:
    """
    本地账户追踪器
    
    核心逻辑:
    1. 管线生成交易建议 → 记录待确认订单
    2. 交易员反馈成交 → 更新持仓
    3. 未反馈的订单 → 视为未执行
    4. 每日收盘 → 记录净值快照
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        
        self.data_dir = Path(self.path_config.data_root) / "trading"
        self.equity_file = self.data_dir / "equity_curve.json"
        self.pending_orders_file = self.data_dir / "pending_orders.json"
        self.feedback_file = self.data_dir / "trade_feedback.json"
        
        self.position_manager = PositionManager(config)
        
        self.equity_curve: List[EquityPoint] = []
        self.pending_orders: List[Dict] = []
        self.trade_feedbacks: List[TradeFeedback] = []
        
        self._ensure_directories()
        self._load_data()
    
    def _ensure_directories(self):
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self):
        if self.equity_file.exists():
            try:
                with open(self.equity_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.equity_curve = [EquityPoint(**p) for p in data]
            except Exception as e:
                logger.warning(f"加载净值曲线失败: {e}")
        
        if self.pending_orders_file.exists():
            try:
                with open(self.pending_orders_file, 'r', encoding='utf-8') as f:
                    self.pending_orders = json.load(f)
            except Exception as e:
                logger.warning(f"加载待确认订单失败: {e}")
        
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trade_feedbacks = [TradeFeedback(**f) for f in data]
            except Exception as e:
                logger.warning(f"加载交易反馈失败: {e}")
    
    def _save_equity_curve(self):
        with open(self.equity_file, 'w', encoding='utf-8') as f:
            json.dump([p.to_dict() for p in self.equity_curve], f, ensure_ascii=False, indent=2)
    
    def _save_pending_orders(self):
        with open(self.pending_orders_file, 'w', encoding='utf-8') as f:
            json.dump(self.pending_orders, f, ensure_ascii=False, indent=2)
    
    def _save_trade_feedbacks(self):
        with open(self.feedback_file, 'w', encoding='utf-8') as f:
            json.dump([f.to_dict() for f in self.trade_feedbacks], f, ensure_ascii=False, indent=2)
    
    def record_pending_order(
        self,
        stock_code: str,
        stock_name: str,
        side: str,
        quantity: int,
        price: float,
        reason: str = "",
        signal_id: str = ""
    ) -> str:
        """
        记录待确认订单（管线生成）
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            side: buy/sell
            quantity: 数量
            price: 价格
            reason: 原因
            signal_id: 关联信号ID
            
        Returns:
            订单ID
        """
        trade_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{stock_code}"
        
        order = {
            'trade_id': trade_id,
            'signal_id': signal_id,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'side': side,
            'quantity': quantity,
            'price': price,
            'reason': reason,
            'status': 'pending',
            'created_at': datetime.now().isoformat(),
            'expires_at': (datetime.now() + timedelta(days=1)).isoformat()
        }
        
        self.pending_orders.append(order)
        self._save_pending_orders()
        
        logger.info(f"记录待确认订单: {trade_id} {side} {stock_code}")
        return trade_id
    
    def submit_trade_feedback(
        self,
        trade_id: str,
        executed_quantity: int,
        executed_price: float,
        notes: str = ""
    ) -> bool:
        """
        提交交易反馈（交易员反馈）
        
        Args:
            trade_id: 订单ID
            executed_quantity: 实际成交数量
            executed_price: 实际成交价格
            notes: 备注
            
        Returns:
            是否成功
        """
        order = None
        for o in self.pending_orders:
            if o['trade_id'] == trade_id:
                order = o
                break
        
        if not order:
            logger.warning(f"订单不存在: {trade_id}")
            return False
        
        if executed_quantity <= 0:
            feedback = TradeFeedback(
                trade_id=trade_id,
                signal_id=order.get('signal_id', ''),
                stock_code=order['stock_code'],
                stock_name=order['stock_name'],
                side=order['side'],
                requested_quantity=order['quantity'],
                requested_price=order['price'],
                executed_quantity=0,
                executed_price=0,
                status='cancelled',
                feedback_time=datetime.now().isoformat(),
                notes=notes or "交易员取消"
            )
            self.trade_feedbacks.append(feedback)
            self.pending_orders.remove(order)
            self._save_trade_feedbacks()
            self._save_pending_orders()
            logger.info(f"订单取消: {trade_id}")
            return True
        
        success = self.position_manager.update_position_from_trade(
            stock_code=order['stock_code'],
            stock_name=order['stock_name'],
            side=order['side'],
            quantity=executed_quantity,
            price=executed_price,
            notes=notes
        )
        
        if success:
            feedback = TradeFeedback(
                trade_id=trade_id,
                signal_id=order.get('signal_id', ''),
                stock_code=order['stock_code'],
                stock_name=order['stock_name'],
                side=order['side'],
                requested_quantity=order['quantity'],
                requested_price=order['price'],
                executed_quantity=executed_quantity,
                executed_price=executed_price,
                status='executed',
                feedback_time=datetime.now().isoformat(),
                notes=notes
            )
            self.trade_feedbacks.append(feedback)
            self.pending_orders.remove(order)
            self._save_trade_feedbacks()
            self._save_pending_orders()
            logger.info(f"订单执行: {trade_id} 成交{executed_quantity}股@{executed_price}")
            return True
        
        return False
    
    def expire_pending_orders(self) -> int:
        """
        过期未反馈的订单（视为未交易）
        
        Returns:
            过期订单数量
        """
        now = datetime.now()
        expired_count = 0
        
        remaining_orders = []
        for order in self.pending_orders:
            expires_at = datetime.fromisoformat(order['expires_at'])
            if now > expires_at:
                feedback = TradeFeedback(
                    trade_id=order['trade_id'],
                    signal_id=order.get('signal_id', ''),
                    stock_code=order['stock_code'],
                    stock_name=order['stock_name'],
                    side=order['side'],
                    requested_quantity=order['quantity'],
                    requested_price=order['price'],
                    executed_quantity=0,
                    executed_price=0,
                    status='expired',
                    feedback_time=datetime.now().isoformat(),
                    notes="未反馈，自动过期"
                )
                self.trade_feedbacks.append(feedback)
                expired_count += 1
            else:
                remaining_orders.append(order)
        
        self.pending_orders = remaining_orders
        self._save_pending_orders()
        self._save_trade_feedbacks()
        
        if expired_count > 0:
            logger.info(f"过期订单: {expired_count} 笔")
        
        return expired_count
    
    def record_equity_snapshot(self, prices: Dict[str, float] = None) -> EquityPoint:
        """
        记录净值快照
        
        Args:
            prices: 最新价格字典 {stock_code: price}
            
        Returns:
            净值数据点
        """
        if prices:
            self.position_manager.update_prices(prices)
        
        summary = self.position_manager.get_portfolio_summary()
        today = datetime.now().strftime('%Y-%m-%d')
        
        prev_value = self.equity_curve[-1].total_value if self.equity_curve else summary['total_value']
        
        daily_return = (summary['total_value'] - prev_value) / prev_value if prev_value > 0 else 0
        
        initial_capital = self.position_manager.initial_capital
        cumulative_return = (summary['total_value'] - initial_capital) / initial_capital if initial_capital > 0 else 0
        
        point = EquityPoint(
            date=today,
            total_value=summary['total_value'],
            cash=summary['cash'],
            position_value=summary['position_value'],
            daily_return=daily_return,
            cumulative_return=cumulative_return
        )
        
        if self.equity_curve and self.equity_curve[-1].date == today:
            self.equity_curve[-1] = point
        else:
            self.equity_curve.append(point)
        
        self._save_equity_curve()
        
        logger.info(f"记录净值: {today} ¥{summary['total_value']:,.2f} ({daily_return*100:.2f}%)")
        return point
    
    def get_performance_metrics(self, days: int = 60) -> Dict:
        """
        计算绩效指标
        
        Args:
            days: 计算天数
            
        Returns:
            绩效指标字典
        """
        if len(self.equity_curve) < 2:
            return {
                'total_return': 0,
                'annual_return': 0,
                'daily_return_avg': 0,
                'volatility': 0,
                'sharpe_ratio': 0,
                'max_drawdown': 0,
                'win_rate': 0,
                'profit_factor': 0
            }
        
        recent_curve = self.equity_curve[-days:] if len(self.equity_curve) > days else self.equity_curve
        
        returns = [p.daily_return for p in recent_curve]
        
        total_return = recent_curve[-1].cumulative_return if recent_curve else 0
        
        trading_days = len(recent_curve)
        annual_return = total_return * (252 / trading_days) if trading_days > 0 else 0
        
        daily_return_avg = sum(returns) / len(returns) if returns else 0
        
        if len(returns) > 1:
            mean_ret = daily_return_avg
            variance = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            volatility = (variance ** 0.5) * (252 ** 0.5)
        else:
            volatility = 0
        
        sharpe_ratio = annual_return / volatility if volatility > 0 else 0
        
        values = [p.total_value for p in recent_curve]
        peak = values[0]
        max_drawdown = 0
        
        for v in values:
            if v > peak:
                peak = v
            drawdown = (peak - v) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)
        
        positive_days = sum(1 for r in returns if r > 0)
        negative_days = sum(1 for r in returns if r < 0)
        win_rate = positive_days / len(returns) if returns else 0
        
        total_profit = sum(r for r in returns if r > 0)
        total_loss = abs(sum(r for r in returns if r < 0))
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0
        
        return {
            'total_return': round(total_return * 100, 2),
            'annual_return': round(annual_return * 100, 2),
            'daily_return_avg': round(daily_return_avg * 100, 4),
            'volatility': round(volatility * 100, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'max_drawdown': round(max_drawdown * 100, 2),
            'win_rate': round(win_rate * 100, 2),
            'profit_factor': round(profit_factor, 2),
            'trading_days': trading_days
        }
    
    def get_account_summary(self) -> Dict:
        """获取账户摘要"""
        summary = self.position_manager.get_portfolio_summary()
        risk = self.position_manager.calculate_risk_metrics()
        performance = self.get_performance_metrics()
        
        return {
            'account': {
                'total_value': summary['total_value'],
                'cash': summary['cash'],
                'cash_ratio': summary['cash_ratio'],
                'position_count': summary['position_count'],
                'position_value': summary['position_value'],
                'total_pnl': summary['total_pnl'],
                'total_pnl_pct': summary['total_pnl_pct']
            },
            'positions': summary['positions'],
            'weights': summary['weights'],
            'risk': {
                'concentration': risk['concentration'],
                'herfindahl_index': risk['herfindahl_index'],
                'effective_num_positions': risk['effective_num_positions'],
                'industry_concentration': risk.get('industry_concentration', 0)
            },
            'performance': performance,
            'pending_orders': len(self.pending_orders),
            'last_updated': datetime.now().isoformat()
        }
    
    def get_equity_curve(self, days: int = 60) -> List[Dict]:
        """获取净值曲线"""
        recent = self.equity_curve[-days:] if len(self.equity_curve) > days else self.equity_curve
        return [p.to_dict() for p in recent]
    
    def get_pending_orders(self) -> List[Dict]:
        """获取待确认订单"""
        return self.pending_orders.copy()
    
    def get_trade_history(self, days: int = 30) -> List[Dict]:
        """获取交易历史"""
        return self.position_manager.get_trade_history(days)


_local_account_tracker: Optional[LocalAccountTracker] = None


def get_local_account_tracker(config: Dict = None) -> LocalAccountTracker:
    """获取本地账户追踪器单例"""
    global _local_account_tracker
    if _local_account_tracker is None:
        _local_account_tracker = LocalAccountTracker(config)
    return _local_account_tracker


__all__ = [
    'LocalAccountTracker',
    'EquityPoint',
    'TradeFeedback',
    'get_local_account_tracker'
]
