# WildQuest Matrix - 智能管线优化

## 🎯 解决的核心问题

### 1. 工作流走到最后才发现前期策略/数据不行
**解决方案**: 质量门控系统
- 每个关键步骤都有质量检查
- 不达标的步骤自动停止
- 避免浪费时间在无效步骤上

### 2. 前置步骤没有执行就直接开启推送
**解决方案**: 依赖检查机制
- 检查前置步骤是否完成
- 检查前置步骤是否通过质量门控
- 不满足条件自动跳过

### 3. 没有回测就直接应用
**解决方案**: 强制回测检查
- 回测是必需步骤
- 回测结果需要达到阈值
- 不达标的策略不能应用

### 4. 工作流执行到一半就中断
**解决方案**: 断点续传
- 保存每个步骤的执行状态
- 支持从断点恢复执行
- 避免重复执行已完成步骤

### 5. 终止后又重新开始
**解决方案**: 状态管理
- 记录管线执行状态
- 支持手动重试失败步骤
- 支持清除状态重新开始

## 🏗️ 架构设计

### 混合方案
- **固定流程**: 用代码自动化，提高效率
- **关键决策**: 用 LLM 审查，保证质量

### 质量门控系统
```
步骤执行 → 质量检查 → 自动判断/LLM审查 → 决策 → 继续/停止
```

### 状态管理
```
开始 → 执行步骤 → 保存状态 → 检查状态 → 恢复/继续
```

## 📦 模块说明

### 1. 性能优化模块 (`core/optimization/performance.py`)
- **ParallelFactorCalculator**: 并行因子计算器
- **MemoryOptimizedProcessor**: 内存优化处理器
- **SmartDataUpdater**: 智能数据更新器

**使用场景**:
- 因子计算耗时过长
- 内存占用过高导致 OOM
- 数据更新全量下载浪费时间

**预期收益**:
- 执行时间减少 50-70%
- 内存占用降低 40%

### 2. 质量门控系统 (`core/quality/quality_gate.py`)
- **QualityGateManager**: 质量门控管理器
- **SmartPipelineExecutor**: 智能管线执行器
- **PipelineState**: 管线状态管理

**使用场景**:
- 需要质量检查的步骤
- 需要 LLM 审查的决策
- 需要断点续传的场景

**预期收益**:
- 失败率从 20% 降到 5% 以下
- 支持断点续传，避免重复执行

### 3. 智能管线执行器 (`core/pipeline/intelligent_pipeline.py`)
- **IntelligentPipeline**: 智能管线执行器
- **create_intelligent_pipeline**: 创建智能管线的工厂函数

**使用场景**:
- 完整的管线执行
- 状态查询和管理
- 手动审查和重试

**预期收益**:
- 完全自动化，无需手动干预
- 支持灵活的执行控制

## 🚀 快速开始

### 1. 创建智能管线

```python
from core.pipeline import create_intelligent_pipeline

# 创建智能管线
pipeline = create_intelligent_pipeline(
    pipeline_id="daily_pipeline_20240425",
    config={
        'enable_llm_review': True,  # 启用 LLM 审查
        'auto_resume': True,        # 自动从断点恢复
    }
)
```

### 2. 注册步骤执行函数

```python
# 注册步骤执行函数
pipeline.register_step_executor(0, execute_position_check)
pipeline.register_step_executor(1, execute_data_update)
pipeline.register_step_executor(2, execute_data_quality_check)
# ... 注册其他步骤
```

### 3. 注册步骤检查函数

```python
# 注册步骤检查函数
pipeline.register_step_checker(1, check_data_update)
pipeline.register_step_checker(3, check_factor_calculation)
# ... 注册其他检查函数
```

### 4. 执行管线

```python
# 执行管线
result = pipeline.execute(mode="standard")

# 查看结果
print(f"完成步骤: {result['summary']['passed_gates']}/{result['summary']['total_gates']}")
print(f"失败步骤: {result['summary']['failed_gates']}")
```

### 5. 查询状态

```python
# 获取管线状态
status = pipeline.get_status()
print(f"当前步骤: {status['current_step']}")
print(f"完成步骤: {status['completed_steps']}")

# 获取质量报告
report = pipeline.get_report()
for gate_name, gate_result in report['gates'].items():
    print(f"{gate_name}: {gate_result['status']} (分数: {gate_result['score']:.2f})")
```

### 6. 手动审查

```python
# 手动审查需要审查的门控
pipeline.manual_review(
    gate_name="backtest",
    decision="approve",  # approve, reject, modify, defer
    comment="回测结果符合要求"
)
```

### 7. 重试失败步骤

```python
# 重试失败的步骤
pipeline.retry_failed_step(step_id=3)
```

### 8. 清除状态

```python
# 清除管线状态，重新开始
pipeline.clear_state()
```

## 📋 质量门控规则

### 数据更新 (data_update)
- **必需**: 是
- **阈值**: 0.8
- **自动批准**: 否
- **需要审查**: 是

### 数据质量 (data_quality)
- **必需**: 是
- **阈值**: 0.9
- **自动批准**: 是
- **需要审查**: 否

### 因子计算 (factor_calculation)
- **必需**: 是
- **阈值**: 0.7
- **自动批准**: 否
- **需要审查**: 是

### Alpha 生成 (alpha_generation)
- **必需**: 是
- **阈值**: 0.6
- **自动批准**: 否
- **需要审查**: 是

### 回测 (backtest)
- **必需**: 是
- **阈值**: 0.5
- **自动批准**: 否
- **需要审查**: 是

### 组合优化 (portfolio_optimization)
- **必需**: 是
- **阈值**: 0.7
- **自动批准**: 是
- **需要审查**: 否

### 风控检查 (risk_check)
- **必需**: 是
- **阈值**: 0.8
- **自动批准**: 否
- **需要审查**: 是

## 🔧 LLM 审查集成

### 审查触发条件
1. 质量分数低于阈值
2. 质量门控规则要求审查
3. 关键决策点（如回测、风控）

### 审查流程
```
质量检查 → 分数不达标 → 需要 LLM 审查 → LLM 分析 → 批准/拒绝
```

### 审查提示词
系统会自动构建审查提示词，包括：
- 门控名称
- 检查结果
- 质量分数
- 详细信息

### 审查决策
- **approve**: 批准，继续执行
- **reject**: 拒绝，停止执行
- **modify**: 修改后重试
- **defer**: 延迟决策

## 📊 状态管理

### 状态文件
- 位置: `./pipeline_states/{pipeline_id}.json`
- 格式: JSON
- 内容: 管线状态、门控结果、执行数据

### 状态查询
```python
# 获取管线状态
status = pipeline.get_status()

# 状态字段
- pipeline_id: 管线 ID
- status: 状态 (running, completed, failed)
- current_step: 当前步骤
- completed_steps: 已完成步骤
- failed_steps: 失败步骤
- start_time: 开始时间
- end_time: 结束时间
- failed_gates: 失败的门控
- review_required_gates: 需要审查的门控
```

### 断点续传
```python
# 自动从断点恢复
result = pipeline.execute(auto_resume=True)

# 手动指定恢复点
result = pipeline.execute(resume=True)
```

## 🎯 使用建议

### 1. 性能优化
- 对于计算密集型任务，使用并行计算
- 对于大数据处理，使用分块处理
- 对于数据更新，使用智能增量更新

### 2. 质量控制
- 为关键步骤设置质量门控
- 为重要决策启用 LLM 审查
- 定期检查质量报告

### 3. 状态管理
- 定期清理旧的状态文件
- 使用有意义的管线 ID
- 记录重要的执行日志

### 4. LLM 审查
- 为关键决策启用 LLM 审查
- 提供清晰的审查上下文
- 记录审查决策和理由

## 📈 预期收益

### 性能提升
- 执行时间减少 50-70%
- 内存占用降低 40%
- CPU 利用率提升 30%

### 稳定性提升
- 失败率从 20% 降到 5% 以下
- 故障恢复时间 < 5 分钟
- 支持断点续传

### 质量提升
- 关键决策有 LLM 审查
- 质量门控保证数据质量
- 避免无效策略应用

### 可维护性提升
- 代码可读性和可维护性显著提升
- 状态管理清晰
- 易于调试和优化

## 🔍 故障排查

### 问题 1: 管线执行失败
**原因**: 某个步骤执行失败
**解决**:
1. 查看失败步骤的错误信息
2. 检查输入数据是否正确
3. 重试失败步骤

### 问题 2: 质量门控不通过
**原因**: 质量分数低于阈值
**解决**:
1. 查看质量报告
2. 检查数据质量
3. 调整阈值或改进数据

### 问题 3: LLM 审查被拒绝
**原因**: LLM 认为不符合要求
**解决**:
1. 查看审查评论
2. 改进策略或数据
3. 手动审查批准

### 问题 4: 状态文件损坏
**原因**: 状态文件写入失败
**解决**:
1. 清除状态文件
2. 重新执行管线
3. 检查磁盘空间

## 📚 参考资料

- [质量门控系统设计](./docs/quality_gate_design.md)
- [LLM 审查最佳实践](./docs/llm_review_best_practices.md)
- [状态管理指南](./docs/state_management_guide.md)
- [性能优化技巧](./docs/performance_optimization_tips.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License
