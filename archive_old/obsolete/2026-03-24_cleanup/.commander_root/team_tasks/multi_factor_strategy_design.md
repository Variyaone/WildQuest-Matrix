# 🏗️ 多因子组合策略设计（基于Top 5因子）

**完成时间**: 2026-02-27 04:42
**截止时间**: 08:00 ✅ 提前完成

---

## 📊 Top5因子回顾

| 因子 | IC | IR | 换手率 | 类别 |
|------|---|---|--------|------|
| VWAP_Deviation | -0.0073 | -1.8803 | 0.5% | Volume_Weighted |
| Price_SMA200_Deviation | 0.0020 | -1.8172 | 7.0% | Mean_Reversion |
| Cumulative_Return_Negative | 0.0080 | 1.5451 | 5.0% | Mean_Reversion |
| EMA_12_26_Cross_Tendency | 0.0020 | -1.4444 | 6.8% | MA_Variant |
| VWAP_20_Deviation | -0.0160 | -1.3833 | 26.0% | Volume_Weighted |
| **Volume_Weighted_Momentum_10d** (推荐) | **-0.0284** | **N/A** | <100% | Volume_Weighted |
| **DEMA_12_Deviation** (推荐) | **-0.0211** | **N/A** | <100% | MA_Variant |

---

## 🎯 组合策略设计（初版：等权重）

### 策略逻辑

1. **信号生成**: 对每个因子计算其Z-score标准化信号
2. **组合加权**: 等权重（每个因子20%）
3. **目标构建**:
   - 信号 > 1.5: 做多
   - 信号 < -1.5: 做空
   - 否则: 平仓或持仓不变

### 因子标准化

```python
# 伪代码
for factor in top5_factors:
    z_score = (factor_value - factor_mean) / factor_std
    factor_signal = z_score  # 直接使用Z-score
```

### 组合信号

```python
portfolio_signal = (f1_signal + f2_signal + f3_signal + f4_signal + f5_signal) / 5

# 交易规则
if portfolio_signal > 1.5:
    position_size = min_factor_signal * 0.02  # 单因子最大2%
elif portfolio_signal < -1.5:
    position_size = min_factor_signal * 0.02
else:
    position_size = 0
```

---

## 🔧 实施步骤

### 1. 数据准备
- [ ] 加载因子数据: `/Users/variya/.openclaw/workspace/research/factors/20260227/`
- [ ] 加载价格数据（BTC/ETH）
- [ ] 对齐时间戳（确保因子和价格数据同步）

### 2. 因子标准化
- [ ] 计算每个因子的滚动均值（60日窗口）
- [ ] 计算每个因子的滚动标准差（60日窗口）
- [ ] 生成Z-score信号

### 3. 组合权重优化
- **初版**: 等权重（20% each）
- **优化方向**:
  - IC加权: 按因子IC值加权（Volume_Weighted_Momentum占比最高）
  - IR加权: 按IR值加权（稳定性高的因子更多）
  - 风险平价: 按因子波动率倒数加权

### 4. 回测准备
```python
# 回测框架核心
class MultiFactorBacktester:
    def __init__(self, factor_data, price_data, rebalance_freq='1D'):
        self.factor_data = factor_data
        self.price_data = price_data
        self.rebalance_freq = rebalance_freq

    def run_backtest(self, weights):
        """
        weights: dict, e.g., {'VWAP_Deviation': 0.2, ...}
        """
        # 计算组合信号
        # 生成交易信号（多/空/平）
        # 计算收益（考虑换手率成本）
        # 计算风险指标（最大回撤、夏普比率）
        return results
```

---

## 📈 预期结果

### 风险指标
- **年化收益**: 预期 15-25% (优于单因子)
- **最大回撤**: 预期 <20% (因子间分散风险)
- **夏普比率**: 预期 >1.5 (因子去相关提升)
- **换手率**: 预期 15-30% (等权混合降低换手)

### 组合优势
1. **分散化**: 5个因子来自3个类别（MA_Variant, Mean_Reversion, Volume_Weighted）
2. **稳定性**: 组合信号平滑，减少单个因子的噪声
3. **鲁棒性**: 单个因子失效时，其他因子补偿

---

## 🔄 后续优化方向

### 1. 因子去相关
- 使用PCA提取主成分
- 逐步回归剔除高相关因子

### 2. 动态权重
- 根据因子IC滚动动态调整权重
- 市场状态分类（趋势/震荡）——不同组合

### 3. 风控模块
- 组合信号置信度低时降低仓位
- 最大回撤触发时强制减仓

---

## 📝 回测框架代码（初版框架）

```python
# 位置: /Users/variya/.openclaw/workspace/research/multi_factor_backtester.py

import pandas as pd
import numpy as np

class MultiFactorStrategy:
    def __init__(self, factor_files, weights=None):
        self.factors = self.load_factors(factor_files)
        self.weights = weights or {f: 0.2 for f in self.factors.columns}

    def load_factors(self, files):
        """加载因子数据，合并时间序列"""
        factors = pd.concat([pd.read_csv(f) for f in files], axis=1)
        return factors

    def normalize(self, factor, window=60):
        """滚动Z-score标准化"""
        return (factor - factor.rolling(window).mean()) / factor.rolling(window).std()

    def generate_signals(self):
        """生成组合信号"""
        signals = pd.DataFrame(index=self.factors.index)
        for factor in self.factors.columns:
            signals[factor] = self.normalize(self.factors[factor])

        # 等权组合
        portfolio_signal = signals * pd.Series(self.weights)
        portfolio_signal['combined'] = portfolio_signal.sum(axis=1)

        return portfolio_signal

    def backtest(self, price_data, commission=0.0005):
        """回测"""
        signals = self.generate_signals()
        positions = self.generate_positions(signals)
        returns = self.calculate_returns(positions, price_data, commission)
        return self.evaluate(returns)

    def generate_positions(self, signals):
        """信号->仓位"""
        combined = signals['combined']
        positions = pd.Series(index=combined.index, dtype=float)

        # 阈值交易
        positions[combined > 1.5] = 0.02  # 做多2%
        positions[combined < -1.5] = -0.02  # 做空2%
        positions[(combined >= -1.5) & (combined <= 1.5)] = 0  # 平仓

        return positions

    def calculate_returns(self, positions, price_data, commission):
        """计算收益（含手续费）"""
        returns = pd.Series(index=positions.index)
        for i in range(1, len(positions)):
            pos_change = abs(positions[i] - positions[i-1])
            trade_cost = pos_change * commission
            return_val = (price_data[i] / price_data[i-1] - 1) * positions[i-1]
            returns[i] = return_val - trade_cost

        return returns

    def evaluate(self, returns):
        """评估指标"""
        annual_return = returns.mean() * 365
        annual_vol = returns.std() * np.sqrt(365)
        sharpe = annual_return / annual_vol if annual_vol > 0 else 0
        max_drawdown = (returns.cumsum() - returns.cumsum().cummax()).min()

        return {
            'annual_return': annual_return,
            'annual_volatility': annual_vol,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown
        }
```

---

## ✅ 完成清单

- [x] 基于Top5因子设计组合策略
- [x] 等权重组合方案
- [x] 回测框架代码框架
- [x] 后续优化方向规划

---

## 🚀 下一步行动

1. **实现回测代码**: 保存到 `/Users/variya/.openclaw/workspace/research/multi_factor_backtester.py`
2. **加载数据运行**: 使用因子挖掘结果和价格数据
3. **评估结果对比**: 等权重 vs IC加权 vs IR加权
4. **Gate Review评审**: 梳理后进入实盘测试

---

*研究员交付 | 指挥官小龙虾复核*
