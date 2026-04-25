#!/bin/bash
###########################################
# Gateway 5 OKX沙盒模拟盘启动脚本
# BTC-USDT + ETH-USDT
# 使用OKX的沙盒环境（非本地Mock）
###########################################

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 工作目录
WORKSPACE="/Users/variya/.openclaw"

# 日志目录
LOG_DIR="$WORKSPACE/logs/okx_sandbox"
mkdir -p "$LOG_DIR"

# PID文件
BTC_PID="$LOG_DIR/btc_okx_sandbox.pid"
ETH_PID="$LOG_DIR/eth_okx_sandbox.pid"
MONITOR_PID="$LOG_DIR/monitor.pid"

echo ""
echo "============================================================"
echo "  🚀 Gateway 5 OKX沙盒模拟盘启动"
echo "  使用OKX沙盒环境（非本地Mock）"
echo "  BTC-USDT + ETH-USDT"
echo "============================================================"
echo ""

# 检查是否已在运行
check_running() {
    if [ -f "$BTC_PID" ] && kill -0 $(cat "$BTC_PID") 2>/dev/null; then
        echo -e "${YELLOW}⚠️  BTC沙盒已在运行${NC}"
        return 0
    fi
    if [ -f "$ETH_PID" ] && kill -0 $(cat "$ETH_PID") 2>/dev/null; then
        echo -e "${YELLOW}⚠️  ETH沙盒已在运行${NC}"
        return 0
    fi
    return 1
}

if check_running; then
    echo ""
    echo -e "${BLUE}运行状态:${NC}"
    [ -f "$BTC_PID" ] && kill -0 $(cat "$BTC_PID") 2>/dev/null && echo "  [BTC-USDT] 运行中 (PID: $(cat $BTC_PID))"
    [ -f "$ETH_PID" ] && kill -0 $(cat "$ETH_PID") 2>/dev/null && echo "  [ETH-USDT] 运行中 (PID: $(cat $ETH_PID))"
    echo ""
    echo "提示: 使用 $0 stop 停止模拟盘"
    echo ""
    exit 0
fi

# 停止旧的本地模拟盘
echo -e "${BLUE}🔄 停止旧的本地模拟盘...${NC}"
cd "$WORKSPACE"
bash start_gate5_simulation.sh stop 2>/dev/null || true
rm -f "$WORKSPACE/logs/simulation"/*.pid 2>/dev/null
echo -e "${GREEN}  ✓ 已清理${NC}"
echo ""

# 启动BTC沙盒
echo -e "${BLUE}[1/3]📊 启动BTC-USDT OKX沙盒模拟盘...${NC}"
cd "$WORKSPACE"
nohup python3 start_btc_okx_sandbox.py > "$LOG_DIR/btc_okx_sandbox.log" 2>&1 &
echo $! > "$BTC_PID"
sleep 3

if kill -0 $(cat "$BTC_PID") 2>/dev/null; then
    echo -e "${GREEN}  ✅ BTC沙盘启动成功 (PID: $(cat $BTC_PID))${NC}"
    echo -e "     日志: $LOG_DIR/btc_okx_sandbox.log"
else
    echo -e "${RED}  ❌ BTC沙盘启动失败${NC}"
    tail -20 "$LOG_DIR/btc_okx_sandbox.log"
    exit 1
fi
echo ""

# 启动ETH沙盒
echo -e "${BLUE}[2/3]💎 启动ETH-USDT OKX沙盒模拟盘...${NC}"
cd "$WORKSPACE"
nohup python3 start_eth_okx_sandbox.py > "$LOG_DIR/eth_okx_sandbox.log" 2>&1 &
echo $! > "$ETH_PID"
sleep 3

if kill -0 $(cat "$ETH_PID") 2>/dev/null; then
    echo -e "${GREEN}  ✅ ETH沙盘启动成功 (PID: $(cat $ETH_PID))${NC}"
    echo -e "     日志: $LOG_DIR/eth_okx_sandbox.log"
else
    echo -e "${RED}  ❌ ETH沙盘启动失败${NC}"
    tail -20 "$LOG_DIR/eth_okx_sandbox.log"
    exit 1
fi
echo ""

# 启动监控
echo -e "${BLUE}[3/3]📈 启动双币种监控...${NC}"
cd "$WORKSPACE"
nohup python3 workspace-architect/backtest/dual_coin_monitor.py > "$LOG_DIR/monitor.log" 2>&1 &
echo $! > "$MONITOR_PID"
sleep 2

if kill -0 $(cat "$MONITOR_PID") 2>/dev/null; then
    echo -e "${GREEN}  ✅ 监控启动成功 (PID: $(cat $MONITOR_PID))${NC}"
else
    echo -e "${YELLOW}  ⚠️  监控启动失败，但不影响策略运行${NC}"
    rm -f "$MONITOR_PID"
fi
echo ""

# 显示摘要
echo "============================================================"
echo "  🎉 OKX沙盒模拟盘启动完成！"
echo "============================================================"
echo ""
echo -e "${BLUE}执行方式:${NC}"
echo "  • 使用OKX沙盒环境（非本地Mock）"
echo "  • 获取真实市场价格"
echo "  • 模拟订单执行（不真实下单）"
echo ""
echo -e "${BLUE}配置摘要:${NC}"
echo "  • 总资金: $20,000"
echo "  • BTC-USDT: $12,000 (60%) - 8格, ±7.5%"
echo "  • ETH-USDT: $8,000 (40%) - 8格, ±7.5%"
echo "  • 手续费: 0.2%/笔"
echo "  • 趋势过滤: 启用"
echo ""
echo -e "${BLUE}运行状态:${NC}"
echo "  • BTC沙盒: $(if [ -f "$BTC_PID" ] && kill -0 $(cat "$BTC_PID") 2>/dev/null; then echo -e "${GREEN}运行中${NC}"; else echo -e "${RED}已停止${NC}"; fi)"
echo "  • ETH沙盒: $(if [ -f "$ETH_PID" ] && kill -0 $(cat "$ETH_PID") 2>/dev/null; then echo -e "${GREEN}运行中${NC}"; else echo -e "${RED}已停止${NC}"; fi)"
echo "  • 监控: $(if [ -f "$MONITOR_PID" ] && kill -0 $(cat "$MONITOR_PID") 2>/dev/null; then echo -e "${GREEN}运行中${NC}"; else echo -e "${YELLOW}停止/未启动${NC}"; fi)"
echo ""
echo -e "${BLUE}管理命令:${NC}"
echo "  • 查看状态:   bash $0 status"
echo "  • 停止模拟盘: bash $0 stop"
echo "  • 查看日志:   bash $0 logs"
echo "  • 重启:       bash $0 restart"
echo ""
echo "============================================================"
echo ""
echo -e "${YELLOW}提示: OKX沙盒使用真实价格，但订单是模拟执行${NC}"
echo -e "${YELLOW}      不会产生真实的资金交易${NC}"
echo ""

exit 0
