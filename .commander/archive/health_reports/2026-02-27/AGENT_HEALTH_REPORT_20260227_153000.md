# 🦞 Agent健康监控报告

**报告时间**: 2026-02-27 15:30:00
**监控Agent数量**: 5
**活跃任务数量**: 0

---

## 📊 Agent健康状态

| Agent | 状态 | 无活动时长 | Last Activity | 当前任务 | 已完成任务 |
|-------|------|-----------|---------------|---------|-----------|
| ⚠️ main | warning | 10.8小时 | 2026-02-27T04:42:00+08:00 | 监控任务执行 | 5 |
| ⚠️ researcher | warning | 10.8小时 | 2026-02-27T04:42:00+08:00 | 无 | 2 |
| 💀 architect | timeout | 46.9小时 | 2026-02-25T16:38:00+08:00 | 无 | 2 |
| 💀 creator | timeout | 47.1小时 | 2026-02-25T16:24:00+08:00 | 无 | 1 |
| 💀 critic | timeout | 50.8小时 | 2026-02-25T12:44:00+08:00 | 无 | 0 |

## ⏰ 任务超时检测

✅ 无超时任务

## 🚨 告警列表

- [INFO] Agent main 较久无活动: 告警: 10.8小时 (2026-02-27T15:30:00.532828)
- [INFO] Agent researcher 较久无活动: 告警: 10.8小时 (2026-02-27T15:30:00.532843)
- [CRITICAL] Agent architect 超时: 严重超时: 46.9小时 (2026-02-27T15:30:00.532851)
- [CRITICAL] Agent creator 超时: 严重超时: 47.1小时 (2026-02-27T15:30:00.532857)
- [CRITICAL] Agent critic 超时: 严重超时: 50.8小时 (2026-02-27T15:30:00.532865)

## 🔧 建议措施

- **唤醒Agent architect** - 无活动46.9小时，建议立即重新分配任务
- **唤醒Agent creator** - 无活动47.1小时，建议立即重新分配任务
- **唤醒Agent critic** - 无活动50.8小时，建议立即重新分配任务

**执行唤醒命令**:
```bash
# 手动唤醒Agent（通过指挥官）
python3 agent_wakeup.py --agent main
python3 agent_wakeup.py --agent researcher
```

**自动唤醒建议**:
- 定期运行agent_health_monitor.py进行健康检查
- 集成到cron job，每5-10分钟运行一次
- 结合task_timeout_handler.py自动处理超时任务