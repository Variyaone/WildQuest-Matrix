#!/bin/bash
# WildQuest Matrix - 一键安装和配置脚本
# 用途：自动安装和配置整个工作流系统

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
PROJECT_DIR="/Users/variya/.hermes/workspace/a-stock-advisor-6.5"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}WildQuest Matrix 一键安装脚本${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查项目目录
echo -e "${GREEN}[1/8]${NC} 检查项目目录..."
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}错误: 项目目录不存在: $PROJECT_DIR${NC}"
    exit 1
fi
echo -e "${GREEN}✓${NC} 项目目录存在"

# 检查Python环境
echo -e "${GREEN}[2/8]${NC} 检查Python环境..."
if [ ! -d "${PROJECT_DIR}/venv" ]; then
    echo -e "${YELLOW}警告: Python虚拟环境不存在，正在创建...${NC}"
    cd "$PROJECT_DIR"
    python3 -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo -e "${GREEN}✓${NC} Python虚拟环境创建完成"
else
    echo -e "${GREEN}✓${NC} Python虚拟环境存在"
fi

# 安装依赖
echo -e "${GREEN}[3/8]${NC} 安装Python依赖..."
cd "$PROJECT_DIR"
source venv/bin/activate
pip install psutil 2>&1 | grep -v "Requirement already satisfied" || true
echo -e "${GREEN}✓${NC} Python依赖安装完成"

# 设置脚本权限
echo -e "${GREEN}[4/8]${NC} 设置脚本权限..."
chmod +x run_full_pipeline.sh
chmod +x run_full_pipeline.py
chmod +x scripts/health_check.py
chmod +x scripts/monitor_collector.py
chmod +x asa
echo -e "${GREEN}✓${NC} 脚本权限设置完成"

# 创建必要的目录
echo -e "${GREEN}[5/8]${NC} 创建必要的目录..."
mkdir -p logs
mkdir -p logs/metrics
mkdir -p data
mkdir -p pipeline_states
echo -e "${GREEN}✓${NC} 目录创建完成"

# 检查环境变量
echo -e "${GREEN}[6/8]${NC} 检查环境变量..."
if [ ! -f "${PROJECT_DIR}/.env" ]; then
    echo -e "${YELLOW}警告: .env文件不存在，创建示例文件...${NC}"
    cat > "${PROJECT_DIR}/.env" << EOF
# WildQuest Matrix 环境变量配置

# 飞书推送配置
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_WEBHOOK_URL
ASA_NOTIFICATION_ENABLED=true

# 数据配置
DATA_ROOT=./data
LOOKBACK_DAYS=365

# 交易配置
INITIAL_CAPITAL=1000000
MAX_POSITIONS=20

# 系统配置
LOG_LEVEL=INFO
ENABLE_QUALITY_GATE=true
ENABLE_LLM_REVIEW=true
EOF
    echo -e "${GREEN}✓${NC} .env文件创建完成（请修改配置）"
else
    echo -e "${GREEN}✓${NC} .env文件存在"
fi

# 安装crontab
echo -e "${GREEN}[7/8]${NC} 安装crontab配置..."
if [ -f "${PROJECT_DIR}/config/crontab_fixed.txt" ]; then
    # 备份现有crontab
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    
    # 安装新的crontab
    crontab "${PROJECT_DIR}/config/crontab_fixed.txt"
    echo -e "${GREEN}✓${NC} Crontab配置安装完成"
    
    # 显示crontab
    echo ""
    echo -e "${BLUE}当前crontab配置:${NC}"
    crontab -l
else
    echo -e "${YELLOW}警告: crontab配置文件不存在${NC}"
fi

# 测试运行
echo -e "${GREEN}[8/8]${NC} 测试运行..."
cd "$PROJECT_DIR"
echo -e "${BLUE}运行健康检查...${NC}"
python3 scripts/health_check.py || echo -e "${YELLOW}健康检查完成（可能有警告）${NC}"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}安装完成！${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}下一步操作:${NC}"
echo -e "1. 修改 .env 文件中的配置（特别是飞书webhook）"
echo -e "2. 运行测试: ${YELLOW}./run_full_pipeline.py --mode fast${NC}"
echo -e "3. 查看日志: ${YELLOW}tail -f logs/full_pipeline_*.log${NC}"
echo -e "4. 检查crontab: ${YELLOW}crontab -l${NC}"
echo ""
echo -e "${GREEN}定时任务说明:${NC}"
echo -e "  07:00 - 盘前数据更新"
echo -e "  08:45 - 盘前报告推送"
echo -e "  09:30 - 开盘监控"
echo -e "  12:00 - 盘中推送"
echo -e "  15:00 - 收盘数据更新"
echo -e "  15:30 - 盘后报告推送"
echo -e "  16:00 - 盘后完整分析"
echo -e "  03:00 - 系统健康检查"
echo -e "  每小时 - 监控数据收集"
echo ""
