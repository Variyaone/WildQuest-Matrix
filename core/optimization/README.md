# WildQuest Matrix 优化模块

针对个人用户（MacBook Air M4 16G）的性能、稳定性和自动化优化方案。

## 模块说明

### 1. 性能优化 (performance.py)

- **ParallelFactorCalculator**: 并行因子计算器，利用 M4 多核性能
- **MemoryOptimizedProcessor**: 内存优化处理器，分块处理避免 OOM
- **SmartDataUpdater**: 智能数据更新器，只下载缺失数据

**预期收益**: 执行时间减少 50-70%，内存占用降低 40%

### 2. 稳定性优化 (stability.py)

- **RetryManager**: 智能重试管理器，自动重试失败的 API 调用
- **CheckpointManager**: 断点续传管理器，支持从失败处恢复
- **FaultTolerantPipeline**: 容错管线执行器，非必需步骤失败不中断

**预期收益**: 失败率从 20% 降到 5% 以下

### 3. 自动化调度 (automation.py)

- **AutomationScheduler**: 自动化调度器，支持 Hermes Cronjob 和 macOS launchd
- **TaskManager**: 简单的任务管理器，管理定时任务

**预期收益**: 完全自动化，无需手动干预

### 4. 轻量级监控 (monitoring.py)

- **ProgressMonitor**: 进度监控器，显示执行进度
- **LoggerManager**: 日志管理器，结构化日志记录
- **ExecutionReporter**: 执行报告生成器，生成执行报告

**预期收益**: 实时了解执行状态，快速定位问题

## 快速开始

### 安装依赖

```bash
pip install tqdm requests python-dotenv
```

### 使用示例

#### 1. 性能优化

```python
from core.optimization import ParallelFactorCalculator, MemoryOptimizedProcessor

# 并行计算因子
calculator = ParallelFactorCalculator()
results = calculator.calculate_factors(
    factor_ids=['F00001', 'F00002', 'F00003'],
    calculate_func=calculate_factor,
    market_data=market_data
)

# 内存优化处理
processor = MemoryOptimizedProcessor(chunk_size=50)
results = processor.process_in_chunks(stock_list, process_func)
```

#### 2. 稳定性优化

```python
from core.optimization import RetryManager, CheckpointManager, FaultTolerantPipeline

# 智能重试
retry_manager = RetryManager(max_attempts=3)
result = retry_manager.retry(api_call, url, params)

# 断点续传
checkpoint_manager = CheckpointManager(checkpoint_dir="./checkpoints")
checkpoint_manager.save(step_id=1, data=result)
loaded_data = checkpoint_manager.load(step_id=1)

# 容错执行
pipeline = FaultTolerantPipeline()
result = pipeline.execute_pipeline(steps)
```

#### 3. 自动化调度

```python
from core.optimization import AutomationScheduler, setup_daily_pipeline

# 设置每日管线自动化
setup_daily_pipeline(
    project_path="~/workspace/a-stock-advisor-6.5",
    python_env="venv",
    use_hermes=True,
    use_launchd=False
)

# 手动创建调度器
scheduler = AutomationScheduler(project_path, python_env)
cronjob_config = scheduler.generate_hermes_cronjob(
    name="daily_pipeline",
    schedule="0 20 * * 1-5",
    command="asa daily"
)
```

#### 4. 轻量级监控

```python
from core.optimization import setup_monitoring, execution_context

# 设置监控系统
logger_manager, reporter, progress_monitor = setup_monitoring()

# 使用执行上下文
with execution_context("每日管线", logger_manager, reporter) as ctx:
    logger_manager.info("开始执行...")
    for stock in progress_monitor.with_progress(stock_list, "更新数据"):
        update_stock_data(stock)
        ctx['results'].append({'stock': stock, 'status': 'success'})
```

## 配置文件

### Hermes Cronjob 配置

生成的配置文件位于 `config/hermes_cronjob.json`:

```json
{
  "action": "create",
  "name": "a_stock_daily_pipeline",
  "schedule": "0 20 * * 1-5",
  "prompt": "执行 a_stock_daily_pipeline 任务：\ncd ~/workspace/a-stock-advisor-6.5\nsource venv/bin/activate\nasa daily\n",
  "workdir": "/Users/variya/workspace/a-stock-advisor-6.5",
  "skills": ["asa-quant"]
}
```

### macOS launchd 配置

生成的 plist 文件位于 `~/Library/LaunchAgents/com.variya.a_stock_daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.variya.a_stock_daily</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd ~/workspace/a-stock-advisor-6.5 && source venv/bin/activate && asa daily</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>5</integer>
        <key>Hour</key>
        <integer>20</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/com_variya_a_stock_daily.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/com_variya_a_stock_daily_error.log</string>
</dict>
</plist>
```

## 目录结构

```
core/optimization/
├── __init__.py           # 模块初始化
├── performance.py        # 性能优化
├── stability.py          # 稳定性优化
├── automation.py         # 自动化调度
├── monitoring.py         # 轻量级监控
└── README.md            # 本文档
```

## 预期收益

实施这些优化后：

- ⚡ **执行时间**: 从 60 分钟降到 20-30 分钟
- 🛡️ **成功率**: 从 80% 提升到 95%+
- 💾 **内存占用**: 降低 40%
- 🤖 **自动化**: 完全无需手动干预
- 📈 **可维护性**: 更容易调试和优化

## 注意事项

1. **并行计算**: 确保 `calculate_func` 是可序列化的，不能使用闭包
2. **内存优化**: 根据可用内存调整 `chunk_size`，16G 内存建议 50-100
3. **断点续传**: 定期清理旧检查点，避免占用过多磁盘空间
4. **日志轮转**: 默认保留 3 个日志文件，每个最大 10MB
5. **自动化**: 首次使用时测试调度配置，确保命令能正常执行

## 故障排除

### 并行计算失败

如果遇到并行计算失败，检查：
1. 函数是否可序列化
2. 是否有全局变量或闭包
3. 是否有不可序列化的对象（如数据库连接）

### 内存不足

如果遇到 OOM，尝试：
1. 减小 `chunk_size`
2. 减少 `max_stocks` 和 `max_factors`
3. 使用 `fast` 模式而非 `standard` 模式

### 检查点加载失败

如果检查点加载失败，检查：
1. 检查点文件是否存在
2. 检查点文件是否损坏
3. 检查点数据结构是否匹配

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 作者

Variya

## 版本历史

- **1.0.0** (2026-04-25): 初始版本
  - 性能优化模块
  - 稳定性优化模块
  - 自动化调度模块
  - 轻量级监控模块
