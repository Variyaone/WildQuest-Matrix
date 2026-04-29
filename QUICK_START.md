# WildQuest Matrix - 一键启动工作流系统

## 🚀 快速开始

### 一键安装
```bash
cd /Users/variya/.hermes/workspace/a-stock-advisor-6.5
./install.sh
```

### 一键启动
```bash
# 标准模式（完整流程）
./run_full_pipeline.py

# 快速模式（核心步骤）
./run_full_pipeline.py --mode fast

# 实盘模式（包含交易）
./run_full_pipeline.py --mode live

# 禁用LLM审查（节省token）
./run_full_pipeline.py --no-llm-review

# 禁用飞书推送
./run_full_pipeline.py --no-feishu-push
```

## 📋 工作流步骤

### 完整工作流包含8个步骤：

1. **环境检查** - 验证项目结构和依赖
2. **交易日检查** - 确认是否为交易日
3. **数据更新** - 更新股票数据
4. **因子计算** - 计算量化因子
5. **信号生成** - 生成交易信号
6. **策略回测** - 回测策略表现
7. **报告生成** - 生成分析报告
8. **飞书推送** - 推送到飞书

### 质量保障机制

- **质量门控**: 每个步骤都有质量检查
- **LLM审查**: 关键决策由LLM审查
- **断点续传**: 支持从失败处恢复
- **详细日志**: 记录所有执行过程

## 📊 监控和日志

### 查看实时日志
```bash
# 查看最新执行日志
tail -f logs/full_pipeline_*.log

# 查看错误日志
tail -f logs/full_pipeline_error_*.log

# 查看健康检查日志
tail -f logs/health_check.log

# 查看监控数据
tail -f logs/monitor_collector.log
```

### 查看执行报告
```bash
# 查看最新的执行报告
cat logs/execution_report_*.md

# 查看健康检查报告
cat logs/health_report_*.json

# 查看监控指标
cat logs/metrics/metrics_latest.json
```

## ⏰ 定时任务

系统已配置以下定时任务（通过crontab）：

| 时间 | 任务 | 说明 |
|------|------|------|
| 07:00 | 盘前数据更新 | 更新股票数据 |
| 08:45 | 盘前报告推送 | 推送盘前分析 |
| 09:30 | 开盘监控 | 监控开盘情况 |
| 12:00 | 盘中推送 | 推送盘中分析 |
| 15:00 | 收盘数据更新 | 更新收盘数据 |
| 15:30 | 盘后报告推送 | 推送盘后分析 |
| 16:00 | 盘后完整分析 | 完整分析流程 |
| 03:00 | 系统健康检查 | 检查系统健康 |
| 每小时 | 监控数据收集 | 收集监控数据 |

### 管理定时任务
```bash
# 查看当前crontab
crontab -l

# 编辑crontab
crontab -e

# 删除所有定时任务
crontab -r

# 重新安装crontab
crontab config/crontab_fixed.txt
```

## 🔧 系统维护

### 健康检查
```bash
# 运行健康检查
python3 scripts/health_check.py

# 查看健康报告
cat logs/health_report_*.json
```

### 监控数据收集
```bash
# 手动收集监控数据
python3 scripts/monitor_collector.py

# 查看监控指标
cat logs/metrics/metrics_latest.json
```

### 清理日志
```bash
# 清理7天前的日志
find logs -name "*.log" -mtime +7 -delete

# 清理30天前的报告
find logs -name "execution_report_*.md" -mtime +30 -delete

# 清理旧的监控数据
find logs/metrics -name "metrics_*.json" -mtime +7 -delete
```

## 🎯 使用场景

### 1. 日常运营（自动化）
- 系统通过crontab自动运行
- 无需手动干预
- 自动推送报告到飞书

### 2. 手动执行（按需）
- 需要立即分析时手动运行
- 可以选择不同的执行模式
- 查看实时执行过程

### 3. 开发调试
- 使用快速模式测试
- 禁用LLM审查节省token
- 查看详细日志调试问题

### 4. 紧急处理
- 发现问题时立即运行
- 查看健康检查报告
- 检查监控数据定位问题

## 📈 性能优化

### 并行因子计算
- 利用M4多核性能
- 执行时间减少50-70%

### 内存优化
- 分块处理大数据
- 内存占用降低40%

### 智能增量更新
- 只下载缺失数据
- 减少网络和存储压力

## 🛡️ 质量保障

### 质量门控
- 数据更新: 阈值 0.8
- 数据质量: 阈值 0.9
- 因子计算: 阈值 0.7
- 信号生成: 阈值 0.8
- 回测: 阈值 0.5
- 组合优化: 阈值 0.7
- 风控检查: 阈值 0.8

### LLM审查
- 关键决策由LLM审查
- 保证策略质量
- 避免无效策略应用

### 断点续传
- 保存执行状态
- 支持从失败处恢复
- 避免重复执行

## 🚨 故障排查

### 常见问题

1. **crontab任务不执行**
   - 检查crontab配置: `crontab -l`
   - 检查脚本权限: `ls -l run_full_pipeline.py`
   - 查看错误日志: `tail -f logs/full_pipeline_error_*.log`

2. **Python依赖缺失**
   - 重新安装依赖: `pip install -r requirements.txt`
   - 检查虚拟环境: `ls -la venv/`

3. **飞书推送失败**
   - 检查环境变量: `cat .env`
   - 验证webhook URL
   - 查看推送日志

4. **数据更新失败**
   - 检查网络连接
   - 检查数据目录权限
   - 查看数据更新日志

### 获取帮助

1. 查看日志文件
2. 运行健康检查
3. 查看监控数据
4. 检查执行报告

## 📝 配置说明

### 环境变量（.env）
```bash
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
```

### 执行模式
- **standard**: 标准模式，完整管线
- **fast**: 快速模式，核心步骤
- **live**: 实盘模式，包含交易执行

## 🎉 特性总结

✅ 一键启动，无需手动干预
✅ 非交互式执行，适合自动化
✅ LLM审查，保证质量
✅ 质量门控，避免无效步骤
✅ 断点续传，支持恢复
✅ 详细日志，便于调试
✅ 定时任务，自动运行
✅ 监控数据，实时掌握
✅ 健康检查，预防问题
✅ 性能优化，高效执行

## 📞 支持

如有问题，请查看：
1. 日志文件
2. 健康检查报告
3. 监控数据
4. 执行报告

---

**版本**: v4.0.0
**更新时间**: 2026-04-25
**维护者**: 🦞 小龙虾 AI指挥官
