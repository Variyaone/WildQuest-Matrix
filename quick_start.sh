#!/bin/bash
# WildQuest Matrix 快速启动脚本
# 用于日常量化投资工作流

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}WildQuest Matrix 快速启动${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${RED}错误: 虚拟环境不存在，请先创建虚拟环境${NC}"
    exit 1
fi

# 激活虚拟环境
echo -e "${GREEN}✓ 激活虚拟环境...${NC}"
source venv/bin/activate

# 检查必要文件
if [ ! -f "run_asa.py" ]; then
    echo -e "${RED}错误: run_asa.py 不存在${NC}"
    exit 1
fi

# 默认参数
MODE="backtest"
MAX_STOCKS=50
MAX_FACTORS=20

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            MODE="$2"
            shift 2
            ;;
        --max-stocks)
            MAX_STOCKS="$2"
            shift 2
            ;;
        --max-factors)
            MAX_FACTORS="$2"
            shift 2
            ;;
        --help)
            echo "用法: $0 [选项]"
            echo "选项:"
            echo "  --mode MODE          执行模式 (backtest/standard/fast/live)"
            echo "  --max-stocks NUM     最大股票数量"
            echo "  --max-factors NUM    最大因子数量"
            echo "  --help               显示帮助信息"
            exit 0
            ;;
        *)
            echo -e "${RED}未知选项: $1${NC}"
            exit 1
            ;;
    esac
done

# 显示配置信息
echo -e "${YELLOW}配置信息:${NC}"
echo -e "  模式: ${MODE}"
echo -e "  最大股票数: ${MAX_STOCKS}"
echo -e "  最大因子数: ${MAX_FACTORS}"
echo ""

# 执行量化工作流
echo -e "${GREEN}开始执行量化工作流...${NC}"
echo ""

python run_asa.py \
    --mode "$MODE" \
    --max-stocks "$MAX_STOCKS" \
    --max-factors "$MAX_FACTORS"

# 检查执行结果
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ 执行成功！${NC}"
    echo -e "${GREEN}========================================${NC}"
    exit 0
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}✗ 执行失败！${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi