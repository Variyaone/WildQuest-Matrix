# A股量化系统完整交付 - DAG流程图

> 创建时间：2026-02-28 08:13
> 指挥官：小龙虾🦞
> 目标：完整交付生产级A股量化系统

---

## 🎯 总目标

**交付一个可每日自动运行、生成真实交易建议的A股量化系统**

---

## 📊 四阶段并行DAG

```
                    ┌─────────────────────────────────────────────────────┐
                    │           Phase 1: 真实数据接入 (2-3h)              │
                    │                    [架构师]                          │
                    └─────────────────────┬───────────────────────────────┘
                                          │
                     ┌────────────────────┴────────────────────┐
                     │                                         │
                     ▼                                         ▼
    ┌─────────────────────────────────┐    ┌─────────────────────────────────┐
    │  Phase 2: 因子专业化研究 (4-6h)  │    │  Phase 3: 策略系统化 (3-4h)      │
    │          [研究员]                │    │        [架构师]                  │
    │                                 │    │                                 │
    │  • 扩展因子池(20-30个)          │    │  • 多因子打分模型               │
    │  • IC/IR检验                    │───▶│  • Top N选股逻辑               │
    │  • 因子正交化                   │    │  • 风险控制模块                │
    │  • 筛选高质量因子               │    │                                 │
    └─────────────────────────────────┘    └─────────────────────────────────┘
                     │                                         │
                     └────────────────────┬────────────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────────────────┐
                    │           Phase 4: 自动化交付 (2h)                 │
                    │                   [创作者]                          │
                    │                                                     │
                    │  • 每日报告生成脚本                                 │
                    │  • 飞书推送集成                                     │
                    │  • Cron定时任务                                     │
                    └─────────────────────────────────────────────────────┘
```

---

## 🔀 并行执行策略

### 第一波启动（立即）

| Agent | 任务 | 预计时间 | 依赖 |
|-------|------|----------|------|
| 🏗️ 架构师 | Phase 1: 真实数据接入 | 2-3h | 无 |
| 🕵️ 研究员 | Phase 2预备：因子池设计 | 1h | 无 |

### 第二波启动（Phase 1完成后）

| Agent | 任务 | 预计时间 | 依赖 |
|-------|------|----------|------|
| 🕵️ 研究员 | Phase 2: 因子研究 | 4-6h | Phase 1 |
| 🏗️ 架构师 | Phase 3: 策略系统化 | 3-4h | Phase 1 |

### 第三波启动（Phase 2&3完成后）

| Agent | 任务 | 预计时间 | 依赖 |
|-------|------|----------|------|
| ✍️ 创作者 | Phase 4: 自动化交付 | 2h | Phase 2, 3 |

---

## 📋 详细任务分解

### Phase 1: 真实数据接入

**负责人**: 🏗️ 架构师
**目标**: 获取3-5年真实A股数据

#### 任务1.1: AkShare验证与安装
```python
# 验证代码
import akshare as ak
import pandas as pd

# 测试连接
df = ak.stock_zh_a_hist(symbol="000001", period="daily", start_date="20200101")
print(f"获取到 {len(df)} 条数据")
```

**成功标准**: 成功获取至少1只股票的历史数据

#### 任务1.2: 下载成分股数据
```python
# 沪深300成分股
hs300 = ak.index_stock_cons_weight_csindex(symbol="000300")
stock_codes = hs300['成分券代码'].tolist()

# 下载所有成分股数据（3年）
for code in stock_codes[:50]:  # 先测试50只
    df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="20210101")
    df.to_csv(f"data/stocks/{code}.csv")
```

**成功标准**: 至少50只股票的完整历史数据

#### 任务1.3: 因子数据计算
- PE_TTM（市盈率TTM）
- PB（市净率）
- ROE（净资产收益率）
- 营收增长率
- 资产负债率

**成功标准**: 每只股票都有完整的因子数据

---

### Phase 2: 因子专业化研究

**负责人**: 🕵️ 研究员
**目标**: 筛选出5-10个高质量因子

#### 因子池设计（20-30个候选因子）

**估值因子**:
1. PE_TTM（市盈率）
2. PB（市净率）
3. PS（市销率）
4. EV/EBITDA
5. 股息率

**质量因子**:
6. ROE（净资产收益率）
7. ROA（总资产收益率）
8. 毛利率
9. 净利率
10. 资产负债率

**成长因子**:
11. 营收增长率
12. 净利润增长率
13. EPS增长率
14. 经营现金流增长率

**动量因子**:
15. 1个月收益率
16. 3个月收益率
17. 6个月收益率
18. 12个月收益率

**技术因子**:
19. RSI_14
20. MACD
21. 布林带位置
22. 成交量变化率

**其他因子**:
23. 换手率
24. 市值
25. 流动性
26. 波动率

#### IC/IR检验
```python
def calculate_ic(factor_values, future_returns):
    """计算IC（信息系数）"""
    ic = factor_values.corr(future_returns, method='spearman')
    return ic

def calculate_ir(ic_series):
    """计算IR（信息比率）"""
    ir = ic_series.mean() / ic_series.std()
    return ir
```

**成功标准**: IC均值>0.02, IR>0.5

#### 因子正交化
```python
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

def orthogonalize_factors(factor_df):
    """因子正交化处理"""
    scaler = StandardScaler()
    factors_scaled = scaler.fit_transform(factor_df)
    
    pca = PCA(n_components=0.95)  # 保留95%方差
    factors_ortho = pca.fit_transform(factors_scaled)
    
    return factors_ortho, pca
```

**成功标准**: 因子间相关性<0.3

---

### Phase 3: 策略系统化

**负责人**: 🏗️ 架构师
**目标**: 构建完整的多因子选股策略

#### 多因子打分模型
```python
def calculate_factor_score(stock_factors, factor_weights):
    """计算因子综合得分"""
    score = 0
    for factor, weight in factor_weights.items():
        score += weight * stock_factors[factor]
    return score
```

#### Top N选股逻辑
```python
def select_top_stocks(all_stocks_scores, n=10):
    """选出得分最高的N只股票"""
    sorted_stocks = sorted(all_stocks_scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_stocks[:n]
```

#### 风险控制模块
```python
def apply_risk_controls(selected_stocks, portfolio):
    """应用风险控制"""
    # 行业中性
    selected_stocks = industry_neutral(selected_stocks)
    
    # 风格中性
    selected_stocks = style_neutral(selected_stocks)
    
    # 波动率控制
    selected_stocks = volatility_control(selected_stocks)
    
    return selected_stocks
```

**成功标准**: 样本外夏普>1.5, 最大回撤<25%

---

### Phase 4: 自动化交付

**负责人**: ✍️ 创作者
**目标**: 实现每日自动推送

#### 每日报告生成脚本
```python
def generate_daily_report(date, recommendations):
    """生成每日交易建议报告"""
    report = f"""
# A股量化日报 - {date}

## 推荐买入（Top 10）
"""
    for i, stock in enumerate(recommendations, 1):
        report += f"""
{i}. {stock['code']} {stock['name']}
   - 综合得分: {stock['score']:.2f}
   - 推荐理由: {stock['reason']}
   - 因子表现: {stock['factors']}
"""
    return report
```

#### 飞书推送集成
```python
def send_to_feishu(report):
    """推送报告到飞书"""
    # 使用现有的飞书工具
    feishu_doc(action="create", title=f"A股量化日报-{date}", content=report)
```

#### Cron定时任务
```bash
# 每个交易日收盘后18:30运行
30 18 * * 1-5 cd /path/to/a-stock && python run_daily.py >> logs/daily.log 2>&1
```

**成功标准**: 飞书推送成功，定时任务稳定运行

---

## ✅ 交付验收标准

### 最终交付物

| 文件 | 内容 | 验证标准 |
|------|------|----------|
| `run_production.py` | 生产环境运行脚本 | 真实数据可运行 |
| `factor_research_report.md` | 因子研究报告 | 包含IC/IR分析 |
| `backtest_results.json` | 回测结果 | 样本外夏普>1.5 |
| `risk_control_module.py` | 风险控制模块 | 行业/风格中性 |
| `run_daily.py` | 每日运行脚本 | 可自动生成报告 |
| `feishu_push.py` | 飞书推送脚本 | 可成功推送 |
| Cron配置 | 定时任务配置 | 可自动触发 |

### 性能指标

| 指标 | 目标 | 验证方法 |
|------|------|----------|
| 年化收益 | >15% | 样本外回测 |
| 夏普比率 | >1.5 | 样本外回测 |
| 最大回撤 | <25% | 历史回测 |
| IC均值 | >0.02 | 因子检验 |
| IR | >0.5 | 因子检验 |

---

## 🚀 立即行动

### 启动命令

```bash
# 1. 架构师启动Phase 1
sessions_spawn(
    agentId="architect",
    task="A股Phase 1: 真实数据接入。安装AkShare，下载沪深300成分股3年历史数据，计算基础因子。输出到 projects/a-stock-advisor/data/"
)

# 2. 研究员启动Phase 2预备
sessions_spawn(
    agentId="researcher",
    task="A股Phase 2预备: 因子池设计。设计20-30个候选因子列表，编写因子计算代码框架。输出到 projects/a-stock-advisor/factors/"
)
```

---

## 📅 时间线

| 时间 | 里程碑 | 状态 |
|------|--------|------|
| 08:13 | 启动Phase 1 & 2预备 | 🔄 进行中 |
| 10:30 | Phase 1完成 | ⏳ 待定 |
| 11:00 | Phase 2 & 3启动 | ⏳ 待定 |
| 17:00 | Phase 2 & 3完成 | ⏳ 待定 |
| 18:00 | Phase 4启动 | ⏳ 待定 |
| 20:00 | 完整交付 | ⏳ 目标 |

---

*由小龙虾🦞设计*
*创建时间: 2026-02-28 08:13*
