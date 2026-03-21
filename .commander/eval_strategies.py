from strategy_evaluator import StrategyEvaluator

# 创建评估器
evaluator = StrategyEvaluator()

# 评估3个低频策略

# 1. 网格交易（低频配置）
evaluator.evaluate(
    name="网格交易（低频）",
    description="价格区间内多空对冲，波动获利。低频配置：10-20格，单格大间距",
    frequency=5,  # 每日5次
    cost_sensitivity="中",
    expected_return=15,  # 年化15%
    risk=3,
    difficulty=2,
    data_needs="中"
)

# 2. 趋势跟踪（4H周期）
evaluator.evaluate(
    name="趋势跟踪（4H）",
    description="4H K线，移动平均线交叉，捕捉大趋势",
    frequency=0.5,  # 每2天1次
    cost_sensitivity="低",
    expected_return=20,  # 年化20%
    risk=4,
    difficulty=2,
    data_needs="低"
)

# 3. 资金费套利
evaluator.evaluate(
    name="资金费套利",
    description="8小时1次，做多现货+做空合约，赚取资金费率",
    frequency=3,  # 每8小时1次 ≈ 3次/天
    cost_sensitivity="低",
    expected_return=30,  # 年化30%（资金费率>0.1%时）
    risk=2,
    difficulty=3,
    data_needs="低"
)

# 打印排名
evaluator.print_ranking()
