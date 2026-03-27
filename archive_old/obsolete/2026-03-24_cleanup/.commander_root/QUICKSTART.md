# 🚀 快速开始指南 - Agent监控系统

**版本**: 1.0
**日期**: 2026-02-27
**时间**: 5分钟完成部署

---

## ⚡ 5分钟快速部署

### 第1步：进入目录（10秒）

```bash
cd /Users/variya/.openclaw/workspace/.commander
```

### 第2步：运行部署脚本（2分钟）

```bash
bash deploy_monitoring.sh
```

这个脚本会自动完成：
- ✅ 创建必要目录
- ✅ 设置文件权限
- ✅ 测试监控脚本
- ✅ 安装cron jobs
- ✅ 生成部署报告

### 第3步：验证部署（1分钟）

```bash
# 查看安装的cron jobs
crontab -l

# 应该看到类似这样的输出：
# */5 * * * * ... agent_health_monitor.py ...
# */10 * * * * ... task_timeout_handler.py ...
```

### 第4步：手动测试（1分钟）

```bash
# 运行健康监控
python3 agent_health_monitor.py

# 查看生成的报告
cat AGENT_HEALTH_REPORT.md

# 应该看到类似这样的输出：
# 🦞 Agent健康监控器启动
# ...
# 📊 健康检查完成
```

### 第5步：实时监控（20秒）

```bash
# 查看监控日志（实时）
tail -f monitoring_cron.log

# 按Ctrl+C退出
```

---

## ✅ 部署完成！

现在监控系统已经自动运行：
- **频率**: 每5分钟检查Agent健康，每10分钟检查任务超时
- **日志**: 所有日志保存在 `.commander/` 目录
- **报告**: 自动生成Markdown报告

---

## 📊 查看监控结果

### 健康报告

```bash
cat AGENT_HEALTH_REPORT.md
```

### 超时报告

```bash
cat TASK_TIMEOUT_REPORT.md
```

### 告警日志

```bash
cat AGENT_ALERTS.log
```

---

## 🔧 手动运行命令

```bash
# 健康监控
python3 agent_health_monitor.py

# 超时处理（不修改文件，只检测）
python3 task_timeout_handler.py --dry-run

# 超时处理（实际执行）
python3 task_timeout_handler.py
```

---

## 🛑 卸载（如果需要）

```bash
bash deploy_monitoring.sh --uninstall
```

---

## ❓ 常见问题

### Q: Cron jobs不运行怎么办？

A: 检查cron服务和日志：
```bash
# 查看cron日志
tail -20 monitoring_cron.log

# 手动测试
cd /Users/variya/.openclaw/workspace/.commander
python3 agent_health_monitor.py >> test.log 2>&1
```

### Q: 如何修改监控阈值？

A: 编辑配置文件 `agent_monitor_config.json`：
```json
{
  "warning_threshold_hours": 6,        // Agent告警阈值（小时）
  "critical_threshold_hours": 12,      // Agent严重告警阈值
  "timeout_threshold_hours": 24,       // Agent超时阈值
  "task_timeout_minutes": 240         // 任务超时（分钟）
}
```

### Q: 如何查看部署报告？

A: 运行部署脚本后会自动生成：
```bash
cat DEPLOYMENT_REPORT.md
```

---

## 📞 需要帮助？

查看完整文档：
- 详细实施方案: `README_MONITORING.md`
- 诊断报告: `AGENT_HEALTH_MONITOR.md`
- 实施总结: `IMPLEMENTATION_SUMMARY.md`

---

**部署时间**: 2026-02-27
**创新者 (Innovator)**

🦞 小龙虾 AI指挥官 | Agent监控系统
