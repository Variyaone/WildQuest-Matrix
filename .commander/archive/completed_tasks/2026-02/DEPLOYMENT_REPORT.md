# 部署报告 - Agent监控系统

**部署时间**: 2026-02-27 04:49:13
**部署环境**: /Users/variya/.openclaw/workspace/.commander

---

## ✅ 部署内容

### 1. 文件结构
- `agent_health_monitor.py` - Agent健康监控器
- `task_timeout_handler.py` - 任务超时处理器
- `agent_monitor_config.json` - 配置文件
- `deploy_monitoring.sh` - 部署脚本

### 2. 目录结构
- `task_state_backups/` - 任务状态备份
- `work_logs/` - 工作日志
- `team_tasks/` - 团队任务

### 3. Cron Jobs
```cron
# Agent健康监控（每5分钟）
*/5 * * * * cd /path/to/.commander && python3 agent_health_monitor.py...

# 任务超时处理（每10分钟）
*/10 * * * * cd /path/to/.commander && python3 task_timeout_handler.py...
```

---

## 📊 监控指标

### Agent健康
- 告警阈值: 6小时无活动
- 严重告警: 12小时无活动
- 超时阈值: 24小时无活动

### 任务超时
- 告警超时: 2小时
- 严重超时: 4小时
- 致命超时: 8小时

---

## 📁 日志文件

- `AGENT_HEALTH_REPORT.md` - 健康监控报告
- `AGENT_ALERTS.log` - 告警日志
- `TASK_TIMEOUT_REPORT.md` - 超时处理报告
- `TASK_TIMEOUTS.log` - 超时日志
- `monitoring_cron.log` - 监控cron日志
- `timeout_cron.log` - 超时处理cron日志

---

## 🔧 维护命令

### 查看cron jobs
```bash
crontab -l
```

### 编辑cron jobs
```bash
crontab -e
```

### 查看实时日志
```bash
tail -f monitoring_cron.log
tail -f timeout_cron.log
```

### 手动运行监控
```bash
cd /path/to/.commander
python3 agent_health_monitor.py
python3 task_timeout_handler.py
```

### 测试模式（不修改文件）
```bash
python3 task_timeout_handler.py --dry-run
```

---

## 🔄 升级和回滚

### 升级
1. 备份当前文件
2. 替换新版本脚本
3. 测试新脚本
4. 更新cron jobs（如果需要）

### 回滚
1. 停止cron jobs: `crontab -e` (删除相关行)
2. 恢复备份文件
3. 手动测试
4. 重新安装cron jobs

---

## 📞 支持

如遇到问题，请检查：
1. Python环境是否正常
2. TASK_STATE.json是否存在
3. 日志文件中的错误信息
4. Cron服务是否运行

