# 架构设计文档

## 版本信息
- **版本**: v2.0
- **更新日期**: 2026-04-03
- **架构师**: 陈默

---

## 架构概览

### 新架构设计
```
因子 → Alpha → 策略
 ↓       ↓       ↓
计算    生成    执行
```

### 核心理念
1. **简化层级**: 从三层简化为两层
2. **业界标准**: 符合顶级量化机构实践
3. **可扩展性**: 易于添加新功能
4. **可维护性**: 清晰的模块边界

---

## 架构对比

### 旧架构 (v1.0)
```
因子 → 信号 → 策略
      ↑
   问题层
```

**问题**:
- 信号层未实现
- 架构断层
- 不符合业界标准
- 维护成本高

### 新架构 (v2.0)
```
因子 → Alpha → 策略
 ↓       ↓       ↓
组合    生成    执行
```

**优势**:
- ✅ 两层架构，简洁清晰
- ✅ Alpha层已完整实现
- ✅ 符合业界标准
- ✅ 易于维护和扩展

---

## 核心模块

### 1. 因子层 (Factor Layer)

#### 功能
- 因子计算和验证
- 因子质量评估
- 因子数据存储

#### 关键组件
- `FactorRegistry` - 因子注册表
- `FactorEngine` - 因子计算引擎
- `FactorStorage` - 因子数据存储

#### 数据流
```
原始数据 → 因子计算 → 因子验证 → 因子存储
```

---

### 2. Alpha层 (Alpha Layer) ⭐ 新增

#### 功能
- 因子组合优化
- Alpha生成
- 股票排名

#### 关键组件

##### FactorCombiner - 因子组合器
```python
from core.strategy import FactorCombiner, FactorCombinationConfig

combiner = FactorCombiner()
config = FactorCombinationConfig(
    factor_ids=["F00001", "F00002"],
    combination_method="ic_weighted",  # IC加权
    min_ic=0.03,
    min_ir=1.5
)

result = combiner.combine(config)
# result.factor_ids - 筛选后的因子ID
# result.weights - 因子权重
```

**组合方法**:
- `ic_weighted` - IC加权优化
- `ir_weighted` - IR加权优化
- `equal` - 等权组合

##### AlphaGenerator - Alpha生成器
```python
from core.strategy import AlphaGenerator

generator = AlphaGenerator()
alpha_result = generator.generate(
    factor_config,  # 因子组合配置
    date,           # 日期
    factor_data     # 因子数据
)

# alpha_result.alpha_values - Alpha值
# alpha_result.ranked_stocks - 排序后的股票
# alpha_result.scores - 评分
```

#### 数据流
```
因子数据 → 因子组合 → Alpha生成 → 股票排名
```

---

### 3. 策略层 (Strategy Layer)

#### 功能
- 策略定义和管理
- 策略回测
- 策略优化

#### 关键组件
- `StrategyRegistry` - 策略注册表
- `StrategyDesigner` - 策略设计器
- `StrategyBacktester` - 策略回测器

#### 数据结构

##### StrategyMetadata
```python
@dataclass
class StrategyMetadata:
    id: str
    name: str
    description: str
    strategy_type: StrategyType
    factor_config: FactorCombinationConfig  # 新：使用因子配置
    rebalance_freq: RebalanceFrequency
    max_positions: int
    risk_params: RiskParams
```

#### 数据流
```
Alpha值 → 股票选择 → 组合构建 → 策略执行
```

---

## 数据流转

### 完整流程
```
1. 因子计算
   原始数据 → 因子引擎 → 因子值

2. 因子组合
   因子值 → 因子组合器 → 组合权重

3. Alpha生成
   因子值 + 权重 → Alpha生成器 → Alpha值

4. 策略执行
   Alpha值 → 股票选择 → 组合构建 → 交易执行
```

### 数据格式

#### 因子数据
```python
DataFrame:
  - date: 日期
  - stock_code: 股票代码
  - factor_value: 因子值
```

#### Alpha数据
```python
Dict:
  - alpha_values: {stock_code: alpha_value}
  - ranked_stocks: [stock_code1, stock_code2, ...]
  - scores: [score1, score2, ...]
```

---

## 关键改进

### 1. 架构简化
- **旧**: 三层架构，信号层未实现
- **新**: 两层架构，Alpha层完整

### 2. 数据结构统一
- **旧**: SignalConfig (未实现)
- **新**: FactorCombinationConfig (已实现)

### 3. 功能完整
- **旧**: 信号生成缺失
- **新**: Alpha生成完整

### 4. 性能优化
- 因子组合支持权重优化
- Alpha生成支持批量处理
- 数据流转更高效

---

## 扩展性设计

### 1. 组合方法扩展
```python
# 当前支持
- ic_weighted
- ir_weighted
- equal

# 未来可扩展
- ml_methods (机器学习)
- risk_parity (风险平价)
- black_litterman
```

### 2. Alpha分析扩展
```python
# 未来功能
- Alpha衰减分析
- Alpha相关性分析
- Alpha归因分析
```

### 3. 策略类型扩展
```python
# 当前支持
- MULTI_FACTOR (多因子)
- TREND_FOLLOWING (趋势跟踪)
- MEAN_REVERSION (均值回归)

# 未来可扩展
- ML_BASED (机器学习)
- HIGH_FREQUENCY (高频)
```

---

## 性能考虑

### 1. 因子组合
- 时间复杂度: O(n log n)
- 空间复杂度: O(n)
- 优化: 缓存因子数据

### 2. Alpha生成
- 时间复杂度: O(n × m)
- 空间复杂度: O(n)
- 优化: 并行计算

### 3. 策略回测
- 时间复杂度: O(d × n)
- 空间复杂度: O(n)
- 优化: 增量计算

---

## 部署架构

### 单机部署
```
应用层: Alpha Matrix CLI
  ↓
业务层: Factor + Alpha + Strategy
  ↓
数据层: Parquet + SQLite
```

### 分布式部署 (未来)
```
应用层: Web UI + API
  ↓
服务层: 微服务架构
  ↓
计算层: Spark/Dask
  ↓
存储层: 分布式存储
```

---

## 安全考虑

### 1. 数据安全
- 因子数据加密存储
- Alpha值访问控制
- 策略配置权限管理

### 2. 计算安全
- 输入验证
- 异常处理
- 日志审计

### 3. 执行安全
- 交易限额
- 风控检查
- 实时监控

---

## 监控和运维

### 1. 性能监控
- 因子计算耗时
- Alpha生成耗时
- 策略回测耗时

### 2. 质量监控
- 因子IC/IR跟踪
- Alpha衰减监控
- 策略表现跟踪

### 3. 系统监控
- 资源使用率
- 错误率统计
- 告警机制

---

## 迁移指南

### 从旧架构迁移

#### 1. 数据迁移
```bash
# 旧数据已备份
data/backup_signals_20260403/
```

#### 2. 代码迁移
```python
# 旧代码
from core.signal import SignalGenerator

# 新代码
from core.strategy import FactorCombiner, AlphaGenerator
```

#### 3. 配置迁移
```python
# 旧配置
signal_config = SignalConfig(
    signal_ids=["S00001"],
    weights=[1.0]
)

# 新配置
factor_config = FactorCombinationConfig(
    factor_ids=["F00001", "F00002"],
    combination_method="ic_weighted"
)
```

---

## 最佳实践

### 1. 因子选择
- IC > 0.03
- IR > 1.5
- 胜率 > 55%

### 2. 组合优化
- 使用IC加权或IR加权
- 定期重新优化
- 监控组合表现

### 3. Alpha生成
- 使用最新因子数据
- 标准化Alpha值
- 验证Alpha分布

### 4. 策略管理
- 明确策略类型
- 设置合理参数
- 定期回测验证

---

## 未来规划

### 短期 (1-3个月)
- [ ] 完善Alpha分析功能
- [ ] 添加更多组合方法
- [ ] 性能优化

### 中期 (3-6个月)
- [ ] 机器学习组合方法
- [ ] 因子正交化
- [ ] 分布式部署

### 长期 (6-12个月)
- [ ] 实时Alpha生成
- [ ] 自动化策略优化
- [ ] 多资产支持

---

## 参考资料

### 业界标准
- WorldQuant Alpha101
- Alpha191
- Two Sigma Factor Model

### 学术研究
- Barra Risk Model
- Fama-French Factors
- APT Model

---

**文档维护**: 架构团队  
**最后更新**: 2026-04-03
