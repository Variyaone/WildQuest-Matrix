"""
持仓管理模块

功能:
- 持仓记录: 记录每只股票的持仓数量和成本
- 持仓更新: 根据手动录入的成交更新持仓
- 持仓查询: 支持多维度查询
- 持仓分析: 计算盈亏、权重、风险指标
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

from core.infrastructure.config import get_data_paths

logger = logging.getLogger(__name__)


@dataclass
class Position:
    stock_code: str
    stock_name: str
    quantity: int
    avg_cost: float
    current_price: float = 0.0
    sector: str = ""
    industry: str = ""
    entry_time: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notes: str = ""
    
    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price
    
    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_cost
    
    @property
    def profit_loss(self) -> float:
        return (self.current_price - self.avg_cost) * self.quantity
    
    @property
    def profit_loss_pct(self) -> float:
        if self.avg_cost == 0:
            return 0.0
        return (self.current_price - self.avg_cost) / self.avg_cost * 100
    
    @property
    def day_pnl(self) -> float:
        return 0.0
    
    def to_dict(self) -> Dict:
        return {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'quantity': self.quantity,
            'avg_cost': self.avg_cost,
            'current_price': self.current_price,
            'market_value': self.market_value,
            'cost_basis': self.cost_basis,
            'profit_loss': self.profit_loss,
            'profit_loss_pct': self.profit_loss_pct,
            'sector': self.sector,
            'industry': self.industry,
            'entry_time': self.entry_time,
            'updated_at': self.updated_at,
            'notes': self.notes,
        }
    
    def display(self) -> str:
        pnl_icon = "🟢" if self.profit_loss >= 0 else "🔴"
        pnl_sign = "+" if self.profit_loss >= 0 else ""
        
        lines = [
            f"  📊 {self.stock_code} {self.stock_name}",
            f"     数量: {self.quantity:,}",
            f"     成本: ¥{self.avg_cost:.2f} | 现价: ¥{self.current_price:.2f}",
            f"     市值: ¥{self.market_value:,.2f}",
            f"     盈亏: {pnl_icon} {pnl_sign}¥{self.profit_loss:,.2f} ({pnl_sign}{self.profit_loss_pct:.2f}%)",
        ]
        
        if self.sector or self.industry:
            lines.append(f"     行业: {self.sector} / {self.industry}")
        
        return "\n".join(lines)


class PositionManager:
    """持仓管理器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        data_root = self.config.get('data_root')
        if data_root:
            self.path_config = get_data_paths(data_root)
        else:
            self.path_config = get_data_paths()
        
        self.positions_file = Path(self.path_config.data_root) / "trading" / "positions.json"
        self.trades_file = Path(self.path_config.data_root) / "trading" / "trade_records.json"
        
        self.initial_capital = self.config.get('initial_capital', 1000000.0)
        self.cash = self.initial_capital
        self.positions: Dict[str, Position] = {}
        self.trade_records: List[Dict] = []
        
        self._ensure_directories()
        self._load_data()
    
    def _ensure_directories(self):
        self.positions_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _load_data(self):
        if self.positions_file.exists():
            try:
                with open(self.positions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.cash = data.get('cash', self.initial_capital)
                    for code, pos_data in data.get('positions', {}).items():
                        self.positions[code] = Position(
                            stock_code=code,
                            stock_name=pos_data.get('stock_name', ''),
                            quantity=pos_data.get('quantity', 0),
                            avg_cost=pos_data.get('avg_cost', 0),
                            current_price=pos_data.get('current_price', 0),
                            sector=pos_data.get('sector', ''),
                            industry=pos_data.get('industry', ''),
                            entry_time=pos_data.get('entry_time', datetime.now().isoformat()),
                            updated_at=pos_data.get('updated_at', datetime.now().isoformat()),
                            notes=pos_data.get('notes', ''),
                        )
                logger.info(f"加载持仓: {len(self.positions)} 个")
            except Exception as e:
                logger.warning(f"加载持仓失败: {e}")
        
        if self.trades_file.exists():
            try:
                with open(self.trades_file, 'r', encoding='utf-8') as f:
                    self.trade_records = json.load(f)
                logger.info(f"加载交易记录: {len(self.trade_records)} 条")
            except Exception as e:
                logger.warning(f"加载交易记录失败: {e}")
    
    def _save_positions(self):
        try:
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'cash': self.cash,
                    'initial_capital': self.initial_capital,
                    'positions': {code: pos.to_dict() for code, pos in self.positions.items()},
                    'updated_at': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存持仓失败: {e}")
    
    def _save_trade_records(self):
        try:
            with open(self.trades_file, 'w', encoding='utf-8') as f:
                json.dump(self.trade_records, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存交易记录失败: {e}")
    
    def update_position_from_trade(
        self,
        stock_code: str,
        stock_name: str,
        side: str,
        quantity: int,
        price: float,
        commission: float = 0,
        stamp_tax: float = 0,
        transfer_fee: float = 0,
        trade_id: str = None,
        notes: str = ""
    ) -> bool:
        trade_record = {
            'trade_id': trade_id or f"TR-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            'stock_code': stock_code,
            'stock_name': stock_name,
            'side': side,
            'quantity': quantity,
            'price': price,
            'amount': quantity * price,
            'commission': commission,
            'stamp_tax': stamp_tax,
            'transfer_fee': transfer_fee,
            'total_cost': commission + stamp_tax + transfer_fee,
            'timestamp': datetime.now().isoformat(),
            'notes': notes
        }
        self.trade_records.append(trade_record)
        
        if side.lower() == 'buy':
            total_cost = quantity * price + commission + transfer_fee
            self.cash -= total_cost
            
            if stock_code in self.positions:
                pos = self.positions[stock_code]
                total_quantity = pos.quantity + quantity
                total_cost_basis = pos.avg_cost * pos.quantity + quantity * price
                
                pos.quantity = total_quantity
                pos.avg_cost = total_cost_basis / total_quantity if total_quantity > 0 else 0
                pos.updated_at = datetime.now().isoformat()
            else:
                self.positions[stock_code] = Position(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    quantity=quantity,
                    avg_cost=price
                )
            
            logger.info(f"买入: {stock_code} {quantity}股 @ ¥{price:.2f}")
        
        elif side.lower() == 'sell':
            if stock_code not in self.positions:
                logger.warning(f"卖出未持仓股票: {stock_code}")
                return False
            
            pos = self.positions[stock_code]
            
            if quantity > pos.quantity:
                logger.warning(f"卖出数量超过持仓: {quantity} > {pos.quantity}")
                quantity = pos.quantity
            
            proceeds = quantity * price - commission - stamp_tax - transfer_fee
            self.cash += proceeds
            
            pos.quantity -= quantity
            pos.updated_at = datetime.now().isoformat()
            
            if pos.quantity <= 0:
                del self.positions[stock_code]
                logger.info(f"清仓: {stock_code}")
            
            logger.info(f"卖出: {stock_code} {quantity}股 @ ¥{price:.2f}")
        
        self._save_positions()
        self._save_trade_records()
        
        return True
    
    def update_prices(self, prices: Dict[str, float]):
        for stock_code, price in prices.items():
            if stock_code in self.positions:
                self.positions[stock_code].current_price = price
                self.positions[stock_code].updated_at = datetime.now().isoformat()
        
        self._save_positions()
    
    def get_position(self, stock_code: str) -> Optional[Position]:
        return self.positions.get(stock_code)
    
    def get_all_positions(self) -> Dict[str, Position]:
        return self.positions.copy()
    
    def get_total_value(self) -> float:
        position_value = sum(pos.market_value for pos in self.positions.values())
        return self.cash + position_value
    
    def get_position_weights(self) -> Dict[str, float]:
        total_value = self.get_total_value()
        if total_value <= 0:
            return {}
        
        return {
            code: pos.market_value / total_value
            for code, pos in self.positions.items()
        }
    
    def get_portfolio_summary(self) -> Dict:
        total_value = self.get_total_value()
        total_pnl = total_value - self.initial_capital
        total_pnl_pct = (total_pnl / self.initial_capital * 100) if self.initial_capital > 0 else 0
        
        return {
            'total_value': total_value,
            'cash': self.cash,
            'cash_ratio': self.cash / total_value if total_value > 0 else 0,
            'position_count': len(self.positions),
            'position_value': total_value - self.cash,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
            'positions': {code: pos.to_dict() for code, pos in self.positions.items()},
            'weights': self.get_position_weights()
        }
    
    def calculate_risk_metrics(self) -> Dict:
        positions = self.positions
        weights = self.get_position_weights()
        total_value = self.get_total_value()
        
        if not weights:
            return {
                'concentration': 0,
                'herfindahl_index': 0,
                'num_positions': 0,
                'effective_num_positions': 0,
                'cash_ratio': 1.0,
                'max_position_value': 0,
                'total_value': total_value
            }
        
        max_weight = max(weights.values())
        herfindahl = sum(w ** 2 for w in weights.values())
        max_position_value = max(pos.market_value for pos in positions.values()) if positions else 0
        
        industry_weights: Dict[str, float] = {}
        for code, pos in positions.items():
            industry = pos.industry or '未知'
            industry_weights[industry] = industry_weights.get(industry, 0) + weights.get(code, 0)
        
        max_industry_weight = max(industry_weights.values()) if industry_weights else 0
        
        return {
            'concentration': max_weight,
            'herfindahl_index': herfindahl,
            'num_positions': len(positions),
            'effective_num_positions': 1 / herfindahl if herfindahl > 0 else 0,
            'cash_ratio': self.cash / total_value if total_value > 0 else 0,
            'max_position_value': max_position_value,
            'total_value': total_value,
            'industry_concentration': max_industry_weight,
            'industry_distribution': industry_weights,
            'calculated_at': datetime.now().isoformat()
        }
    
    def get_trade_history(self, days: int = 30) -> List[Dict]:
        cutoff = datetime.now() - timedelta(days=days)
        return [
            t for t in self.trade_records
            if datetime.fromisoformat(t['timestamp']) >= cutoff
        ]
    
    def get_trade_summary(self, start_date: str = None, end_date: str = None) -> Dict:
        trades = self.trade_records
        
        if start_date:
            trades = [t for t in trades if t.get('timestamp', '') >= start_date]
        if end_date:
            trades = [t for t in trades if t.get('timestamp', '') <= end_date]
        
        buy_trades = [t for t in trades if t.get('side') == 'buy']
        sell_trades = [t for t in trades if t.get('side') == 'sell']
        
        total_buy = sum(t.get('amount', 0) for t in buy_trades)
        total_sell = sum(t.get('amount', 0) for t in sell_trades)
        total_commission = sum(t.get('commission', 0) for t in trades)
        total_stamp_tax = sum(t.get('stamp_tax', 0) for t in trades)
        total_transfer_fee = sum(t.get('transfer_fee', 0) for t in trades)
        
        return {
            'total_trades': len(trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_buy_amount': round(total_buy, 2),
            'total_sell_amount': round(total_sell, 2),
            'total_commission': round(total_commission, 2),
            'total_stamp_tax': round(total_stamp_tax, 2),
            'total_transfer_fee': round(total_transfer_fee, 2),
            'total_cost': round(total_commission + total_stamp_tax + total_transfer_fee, 2),
            'net_flow': round(total_sell - total_buy, 2)
        }
    
    def add_position_manually(
        self,
        stock_code: str,
        stock_name: str,
        quantity: int,
        avg_cost: float,
        sector: str = "",
        industry: str = "",
        notes: str = ""
    ) -> bool:
        """
        手动添加持仓（不经过交易反馈确认）
        
        注意：此方法直接添加持仓，不经过交易反馈确认流程。
        此方法仅用于特殊场景（如历史数据导入、系统初始化等），
        不应该用于正常的交易流程。
        
        在生产环境中，持仓更新应该通过LocalAccountTracker的submit_trade_feedback方法进行，
        以确保只有经过交易员反馈确认的交易才会更新持仓。
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            quantity: 持仓数量
            avg_cost: 平均成本
            sector: 板块
            industry: 行业
            notes: 备注
            
        Returns:
            是否成功
        """
        if stock_code in self.positions:
            logger.warning(f"持仓已存在: {stock_code}")
            return False
        
        self.positions[stock_code] = Position(
            stock_code=stock_code,
            stock_name=stock_name,
            quantity=quantity,
            avg_cost=avg_cost,
            sector=sector,
            industry=industry,
            notes=notes
        )
        
        self._save_positions()
        logger.info(f"手动添加持仓: {stock_code}")
        return True
    
    def update_position_manually(
        self,
        stock_code: str,
        quantity: int = None,
        avg_cost: float = None,
        current_price: float = None,
        notes: str = None
    ) -> bool:
        """
        手动更新持仓（不经过交易反馈确认）
        
        注意：此方法直接更新持仓，不经过交易反馈确认流程。
        此方法仅用于特殊场景（如历史数据修正、系统初始化等），
        不应该用于正常的交易流程。
        
        在生产环境中，持仓更新应该通过LocalAccountTracker的submit_trade_feedback方法进行，
        以确保只有经过交易员反馈确认的交易才会更新持仓。
        
        Args:
            stock_code: 股票代码
            quantity: 持仓数量
            avg_cost: 平均成本
            current_price: 当前价格
            notes: 备注
            
        Returns:
            是否成功
        """
        if stock_code not in self.positions:
            logger.warning(f"持仓不存在: {stock_code}")
            return False
        
        pos = self.positions[stock_code]
        
        if quantity is not None:
            pos.quantity = quantity
        if avg_cost is not None:
            pos.avg_cost = avg_cost
        if current_price is not None:
            pos.current_price = current_price
        if notes is not None:
            pos.notes = notes
        
        pos.updated_at = datetime.now().isoformat()
        
        self._save_positions()
        logger.info(f"更新持仓: {stock_code}")
        return True
    
    def delete_position(self, stock_code: str) -> bool:
        """
        删除持仓（不经过交易反馈确认）
        
        注意：此方法直接删除持仓，不经过交易反馈确认流程。
        此方法仅用于特殊场景（如历史数据清理、系统初始化等），
        不应该用于正常的交易流程。
        
        在生产环境中，持仓更新应该通过LocalAccountTracker的submit_trade_feedback方法进行，
        以确保只有经过交易员反馈确认的交易才会更新持仓。
        
        Args:
            stock_code: 股票代码
            
        Returns:
            是否成功
        """
        if stock_code not in self.positions:
            logger.warning(f"持仓不存在: {stock_code}")
            return False
        
        del self.positions[stock_code]
        self._save_positions()
        logger.info(f"删除持仓: {stock_code}")
        return True
    
    def clear_all_positions(self) -> bool:
        self.positions.clear()
        self.cash = self.initial_capital
        self._save_positions()
        logger.info("清空所有持仓")
        return True
    
    def print_summary(self):
        summary = self.get_portfolio_summary()
        risk = self.calculate_risk_metrics()
        
        pnl_icon = "🟢" if summary['total_pnl'] >= 0 else "🔴"
        pnl_sign = "+" if summary['total_pnl'] >= 0 else ""
        
        print(f"\n{'='*60}")
        print("📊 持仓摘要")
        print(f"{'='*60}")
        print(f"  总资产: ¥{summary['total_value']:,.2f}")
        print(f"  现金: ¥{summary['cash']:,.2f} ({summary['cash_ratio']:.1%})")
        print(f"  持仓数: {summary['position_count']}")
        print(f"  总盈亏: {pnl_icon} {pnl_sign}¥{summary['total_pnl']:,.2f} ({pnl_sign}{summary['total_pnl_pct']:.2f}%)")
        
        print(f"\n  风险指标:")
        print(f"    集中度: {risk['concentration']:.2%}")
        print(f"    有效持仓数: {risk['effective_num_positions']:.1f}")
        print(f"    行业集中度: {risk.get('industry_concentration', 0):.2%}")
        
        if self.positions:
            print(f"\n  持仓明细:")
            for code, pos in list(self.positions.items())[:10]:
                print(pos.display())
        
        print(f"{'='*60}\n")
