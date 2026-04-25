#!/bin/bash
# OKX模拟盘资金费套利测试 - 环境设置脚本

echo "========================================="
echo "OKX模拟盘资金费套利测试 - 环境设置"
echo "========================================="
echo ""

# 检查Python版本
echo "检查Python版本..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3未安装"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✅ Python版本: $PYTHON_VERSION"

# 安装依赖
echo ""
echo "安装Python依赖..."
pip3 install --upgrade pip
pip3 install ccxt pandas numpy

# 验证安装
echo ""
echo "验证依赖安装..."
python3 -c "import ccxt; print('✅ ccxt:', ccxt.__version__)"

python3 -c "import pandas; print('✅ pandas:', pandas.__version__)"

python3 -c "import numpy; print('✅ numpy:', numpy.__version__)"

echo ""
echo "========================================="
echo "✅ 环境设置完成！"
echo "========================================="
echo ""
echo "下一步操作："
echo "1. 申请OKX模拟盘API密钥"
echo "2. 设置环境变量"
echo "3. 运行测试脚本"
echo ""
echo "详细操作请查看 README_simulation.md"
