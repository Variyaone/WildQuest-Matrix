# 🦞 Agent健康监控报告

**报告时间**: 2026-02-27 18:55:00
**监控Agent数量**: 5
**活跃任务数量**: 0

---

## 📊 Agent健康状态

| Agent | 状态 | 无活动时长 | Last Activity | 当前任务 | 已完成任务 |
|-------|------|-----------|---------------|---------|-----------|
| 🔴 main | critical | 14.2小时 | 2026-02-27T04:42:00+08:00 | 监控任务执行 | 5 |
| 🔴 researcher | critical | 14.2小时 | 2026-02-27T04:42:00+08:00 | 无 | 2 |
| 💀 architect | timeout | 50.3小时 | 2026-02-25T16:38:00+08:00 | 无 | 2 |
| 💀 creator | timeout | 50.5小时 | 2026-02-25T16:24:00+08:00 | 无 | 1 |
| 💀 critic | timeout | 54.2小时 | 2026-02-25T12:44:00+08:00 | 无 | 0 |

## ⏰ 任务超时检测

✅ 无超时任务

## 🚨 告警列表

- [WARNING] Agent main 僵尸: 严重告警: 14.2小时 (2026-02-27T18:55:00.289687)
- [WARNING] Agent researcher 僵尸: 严重告警: 14.2小时 (2026-02-27T18:55:00.289701)
- [CRITICAL] Agent architect 超时: 严重超时: 50.3小时 (2026-02-27T18:55:00.289713)
- [CRITICAL] Agent creator 超时: 严重超时: 50.5小时 (2026-02-27T18:55:00.289720)
- [CRITICAL] Agent critic 超时: 严重超时: 54.2小时 (2026-02-27T18:55:00.289727)

## 🔧 建议措施

- **唤醒Agent main** - 无活动14.2小时，建议立即重新分配任务
- **唤醒Agent researcher** - 无活动14.2小时，建议立即重新分配任务
- **唤醒Agent architect** - 无活动50.3小时，建议立即重新分配任务
- **唤醒Agent creator** - 无活动50.5小时，建议立即重新分配任务
- **唤醒Agent critic** - 无活动54.2小时，建议立即重新分配任务

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