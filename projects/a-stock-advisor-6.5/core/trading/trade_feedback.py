"""
交易反馈模块

提供交易员反馈成交记录的接口:
- CLI命令
- 交互式输入
- 批量导入
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from core.trading.local_account import get_local_account_tracker, TradeFeedback
from core.infrastructure.config import get_data_paths

logger = logging.getLogger(__name__)


class TradeFeedbackHandler:
    """交易反馈处理器"""
    
    def __init__(self):
        self.account = get_local_account_tracker()
    
    def list_pending_orders(self) -> List[Dict]:
        """列出待确认订单"""
        orders = self.account.get_pending_orders()
        
        if not orders:
            print("\n暂无待确认订单\n")
            return []
        
        print(f"\n{'='*70}")
        print("待确认订单列表")
        print(f"{'='*70}")
        
        for i, order in enumerate(orders, 1):
            status_icon = "⏳" if order['status'] == 'pending' else "❓"
            side_icon = "🟢" if order['side'] == 'buy' else "🔴"
            
            print(f"\n{i}. {status_icon} {order['trade_id']}")
            print(f"   {side_icon} {order['side'].upper()} {order['stock_code']} {order['stock_name']}")
            print(f"   委托: {order['quantity']}股 @ ¥{order['price']:.2f}")
            print(f"   原因: {order.get('reason', '-')}")
            print(f"   时间: {order['created_at']}")
        
        print(f"\n{'='*70}\n")
        return orders
    
    def submit_feedback(
        self,
        trade_id: str,
        executed_quantity: int,
        executed_price: float,
        notes: str = ""
    ) -> bool:
        """
        提交交易反馈
        
        Args:
            trade_id: 订单ID
            executed_quantity: 实际成交数量 (0表示取消)
            executed_price: 实际成交价格
            notes: 备注
            
        Returns:
            是否成功
        """
        return self.account.submit_trade_feedback(
            trade_id=trade_id,
            executed_quantity=executed_quantity,
            executed_price=executed_price,
            notes=notes
        )
    
    def cancel_order(self, trade_id: str, reason: str = "") -> bool:
        """取消订单"""
        return self.submit_feedback(
            trade_id=trade_id,
            executed_quantity=0,
            executed_price=0,
            notes=reason or "交易员取消"
        )
    
    def batch_feedback(self, feedbacks: List[Dict]) -> Dict:
        """
        批量反馈
        
        Args:
            feedbacks: 反馈列表 [{trade_id, executed_quantity, executed_price, notes}, ...]
            
        Returns:
            结果统计
        """
        results = {
            'success': 0,
            'failed': 0,
            'errors': []
        }
        
        for fb in feedbacks:
            try:
                success = self.submit_feedback(
                    trade_id=fb['trade_id'],
                    executed_quantity=fb.get('executed_quantity', 0),
                    executed_price=fb.get('executed_price', 0),
                    notes=fb.get('notes', '')
                )
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
                    results['errors'].append(f"{fb['trade_id']}: 提交失败")
            except Exception as e:
                results['failed'] += 1
                results['errors'].append(f"{fb['trade_id']}: {str(e)}")
        
        return results
    
    def import_from_file(self, file_path: str) -> Dict:
        """
        从文件导入反馈
        
        文件格式 (JSON):
        [
            {
                "trade_id": "ORD-20260329-600519",
                "executed_quantity": 100,
                "executed_price": 1850.00,
                "notes": "全部成交"
            },
            ...
        ]
        """
        path = Path(file_path)
        if not path.exists():
            return {'success': 0, 'failed': 0, 'errors': [f'文件不存在: {file_path}']}
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
        except json.JSONDecodeError as e:
            return {'success': 0, 'failed': 1, 'errors': [f'JSON解析错误: {e}']}
        
        return self.batch_feedback(feedbacks)
    
    def interactive_feedback(self):
        """交互式反馈"""
        orders = self.list_pending_orders()
        
        if not orders:
            return
        
        print("请选择要反馈的订单编号 (输入 0 退出):")
        
        try:
            choice = int(input("> "))
            if choice == 0:
                return
            if choice < 1 or choice > len(orders):
                print("无效选择")
                return
        except ValueError:
            print("请输入数字")
            return
        
        order = orders[choice - 1]
        trade_id = order['trade_id']
        
        print(f"\n订单: {trade_id}")
        print(f"委托: {order['side']} {order['quantity']}股 @ ¥{order['price']:.2f}")
        print()
        
        print("请输入成交数量 (输入 0 表示取消):")
        try:
            quantity = int(input("> "))
        except ValueError:
            print("无效数量")
            return
        
        if quantity == 0:
            print("请输入取消原因:")
            reason = input("> ") or "交易员取消"
            if self.cancel_order(trade_id, reason):
                print("✓ 订单已取消")
            else:
                print("✗ 取消失败")
            return
        
        print(f"请输入成交价格 (默认: {order['price']:.2f}):")
        price_input = input("> ").strip()
        try:
            price = float(price_input) if price_input else order['price']
        except ValueError:
            print("无效价格")
            return
        
        print("备注 (可选):")
        notes = input("> ")
        
        if self.submit_feedback(trade_id, quantity, price, notes):
            print(f"\n✓ 反馈成功: 成交 {quantity}股 @ ¥{price:.2f}")
        else:
            print("\n✗ 反馈失败")


def show_account_status():
    """显示账户状态"""
    account = get_local_account_tracker()
    summary = account.get_account_summary()
    
    print(f"\n{'='*60}")
    print("📊 账户状态")
    print(f"{'='*60}")
    
    acc = summary['account']
    pnl_icon = "🟢" if acc['total_pnl'] >= 0 else "🔴"
    pnl_sign = "+" if acc['total_pnl'] >= 0 else ""
    
    print(f"  总资产: ¥{acc['total_value']:,.2f}")
    print(f"  现金: ¥{acc['cash']:,.2f} ({acc['cash_ratio']:.1%})")
    print(f"  持仓数: {acc['position_count']}")
    print(f"  总盈亏: {pnl_icon} {pnl_sign}¥{acc['total_pnl']:,.2f} ({pnl_sign}{acc['total_pnl_pct']:.2f}%)")
    
    perf = summary['performance']
    trading_days = perf.get('trading_days', 0)
    print(f"\n  绩效指标 (近{trading_days}天):")
    print(f"    年化收益: {perf.get('annual_return', 0):.2f}%")
    print(f"    夏普比率: {perf.get('sharpe_ratio', 0):.2f}")
    print(f"    最大回撤: {perf.get('max_drawdown', 0):.2f}%")
    print(f"    胜率: {perf.get('win_rate', 0):.2f}%")
    
    risk = summary['risk']
    print(f"\n  风险指标:")
    print(f"    持仓集中度: {risk.get('concentration', 0):.2%}")
    print(f"    行业集中度: {risk.get('industry_concentration', 0):.2%}")
    
    print(f"\n  待确认订单: {summary.get('pending_orders', 0)} 笔")
    print(f"{'='*60}\n")


def show_equity_curve(days: int = 30):
    """显示净值曲线"""
    account = get_local_account_tracker()
    curve = account.get_equity_curve(days)
    
    if not curve:
        print("\n暂无净值数据\n")
        return
    
    print(f"\n{'='*60}")
    print(f"📈 净值曲线 (近{len(curve)}天)")
    print(f"{'='*60}")
    
    print(f"{'日期':<12} {'总资产':>14} {'日收益':>10} {'累计收益':>10}")
    print("-" * 50)
    
    for point in curve[-20:]:
        daily_ret = point['daily_return'] * 100
        cum_ret = point['cumulative_return'] * 100
        
        daily_icon = "🟢" if daily_ret >= 0 else "🔴"
        cum_icon = "🟢" if cum_ret >= 0 else "🔴"
        
        print(f"{point['date']:<12} ¥{point['total_value']:>12,.0f} {daily_icon}{daily_ret:>7.2f}% {cum_icon}{cum_ret:>7.2f}%")
    
    print(f"{'='*60}\n")


_trade_feedback_handler: Optional[TradeFeedbackHandler] = None


def get_trade_feedback_handler() -> TradeFeedbackHandler:
    """获取交易反馈处理器单例"""
    global _trade_feedback_handler
    if _trade_feedback_handler is None:
        _trade_feedback_handler = TradeFeedbackHandler()
    return _trade_feedback_handler


__all__ = [
    'TradeFeedbackHandler',
    'get_trade_feedback_handler',
    'show_account_status',
    'show_equity_curve'
]
