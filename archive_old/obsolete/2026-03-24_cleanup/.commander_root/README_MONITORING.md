# 🚀 Agent僵尸化修复实施方案

**版本**: 1.0
**日期**: 2026-02-27
**作者**: 创新者 (Innovator)
**优先级**: P0

---

## 📋 目录

- [问题摘要](#问题摘要)
- [核心组件](#核心组件)
- [快速开始](#快速开始)
- [详细实施](#详细实施)
- [监控指标](#监控指标)
- [故障排查](#故障排查)
- [后续优化](#后续优化)

---

## 问题摘要

### 当前状态
- **所有Agent僵尸化**: 5个Agent中有4个无活动24-40小时
- **任务停滞**: alpha-research-cycle任务停滞4小时+
- **无监控机制**: 缺少自动告警和恢复系统

### 解决方案
通过以下三个组件构建完整的Agent健康监控系统：

1. **agent_health_monitor.py** - Agent健康监控器
2. **task_timeout_handler.py** - 任务超时处理器
3. **deploy_monitoring.sh** - 自动化部署脚本

### 预期效果
| 指标 | 当前值 | 目标值 | 改善 |
|------|--------|--------|------|
| Agent响应时间 | 24-39小时 | <6小时 | 80%+ |
| 任务停滞率 | 100% | <10% | 90% |
| 自动恢复成功率 | 0% | >80% | N/A |
| 告警响应时间 | N/A | <10分钟 | N/A |

---

## 核心组件

### 1. agent_health_monitor.py - Agent健康监控器

**功能**:
- 定期检查各Agent的lastActivity状态
- 当Agent无活动超过阈值时触发告警
- 生成健康报告和建议措施

**特性**:
- ✅ 支持多Agent监控（main, researcher, architect, creator, critic）
- ✅ 多级告警（warning: 6h, critical: 12h, timeout: 24h）
- ✅ 活跃任务监控
- ✅ 告警日志记录
- ✅ Markdown格式报告

**使用**:
```bash
# 直接运行
python3 agent_health_monitor.py

# 使用自定义配置
python3 agent_health_monitor.py --config custom_config.json

# 查看详细报告
cat AGENT_HEALTH_REPORT.md
```

**输出**:
- `AGENT_HEALTH_REPORT.md` - 健康监控报告
- `AGENT_ALERTS.log` - 告警日志

### 2. task_timeout_handler.py - 任务超时处理器

**功能**:
- 监控TASK_STATE.json中的活跃任务
- 检测停滞的任务（status=in_progress超过阈值）
- 自动标记超时任务
- 生成任务转派建议

**特性**:
- ✅ 多级超时（warning: 2h, critical: 4h, fatal: 8h）
- ✅ 自动标记为timeout或failed
- ✅ 任务状态备份
- ✅ Agent备用映射（自动推荐新Agent）
- ✅ Dry-run模式（试运行，不修改文件）

**使用**:
```bash
# 直接运行
python3 task_timeout_handler.py

# 试运行模式（不修改文件）
python3 task_timeout_handler.py --dry-run

# 使用自定义配置
python3 task_timeout_handler.py --config custom_config.json
```

**输出**:
- `TASK_TIMEOUT_REPORT.md` - 超时处理报告
- `TASK_TIMEOUTS.log` - 超时历史日志
- `task_state_backups/` - 备份目录

### 3. deploy_monitoring.sh - 自动化部署脚本

**功能**:
- 创建必要的目录结构
- 设置文件权限
- 安装cron jobs
- 测试监控脚本
- 生成部署报告

**使用**:
```bash
# 安装
bash deploy_monitoring.sh

# 卸载
bash deploy_monitoring.sh --uninstall

# 使用自定义Python
PYTHON=/usr/local/bin/python3 bash deploy_monitoring.sh

# 使用自定义工作目录
WORKSPACE=/custom/path/.commander bash deploy_monitoring.sh
```

**安装的Cron Jobs**:
```cron
# Agent健康监控（每5分钟）
*/5 * * * * cd /path/to/.commander && python3 agent_health_monitor.py...

# 任务超时处理（每10分钟）
*/10 * * * * cd /path/to/.commander && python3 task_timeout_handler.py...
```

### 4. agent_monitor_config.json - 配置文件

**配置项**:
```json
{
  "warning_threshold_hours": 6,           // Agent告警阈值
  "critical_threshold_hours": 12,         // Agent严重告警阈值
  "timeout_threshold_hours": 24,          // Agent超时阈值
  "task_timeout_minutes": 240,            // 任务超时（4小时）
  "warning_timeout_minutes": 120,         // 任务告警（2小时）
  "critical_timeout_minutes": 240,        // 任务严重超时（4小时）
  "fatal_timeout_minutes": 480,          // 任务致命超时（8小时）
  "auto_mark_timeout": true,              // 自动标记超时任务
  "auto_reassign": false,                 // 自动重新分配（默认关闭）
  "backup_before_modify": true,           // 修改前备份
  "agent_fallback_map": {                 // Agent备用映射
    "researcher": ["architect", "creator"],
    "architect": ["researcher", "creator"],
    ...
  }
}
```

---

## 快速开始

### 第一步：快速部署

```bash
cd /Users/variya/.openclaw/workspace/.commander

# 运行部署脚本
bash deploy_monitoring.sh
```

这将自动完成：
- ✅ 创建必要目录
- ✅ 设置文件权限
- ✅ 测试监控脚本
- ✅ 安装cron jobs
- ✅ 生成部署报告

### 第二步：验证部署

```bash
# 查看安装的cron jobs
crontab -l

# 手动运行监控脚本测试
python3 agent_health_monitor.py

# 查看生成的报告
cat AGENT_HEALTH_REPORT.md
```

### 第三步：实时监控

```bash
# 查看监控cron日志（实时）
tail -f monitoring_cron.log

# 查看超时处理cron日志（实时）
tail -f timeout_cron.log

# 查看告警日志
tail -f AGENT_ALERTS.log
```

---

## 详细实施

### Phase 1: 紧急修复（1小时）

**目标**: 立即恢复Agent和任务

**步骤**:
1. ✅ 创建agent_health_monitor.py
2. ✅ 创建task_timeout_handler.py
3. ⏳ 运行脚本检测当前问题
4. ⏳ 根据报告手动唤醒关键Agent
5. ⏳ 检查并处理超时任务

**验证**:
- [ ] Agent健康监控器运行成功
- [ ] 任务超时处理器运行成功
- [ ] 生成完整报告
- [ ] 关键Agent被唤醒

### Phase 2: 稳定运行（1-2天）

**目标**: 部署自动化监控

**步骤**:
1. ⏳ 运行deploy_monitoring.sh
2. ⏳ 验证cron jobs安装
3. ⏳ 监控日志输出
4. ⏳ 调整配置参数

**验证**:
- [ ] Cron jobs正常运行
- [ ] 日志文件正常生成
- [ ] 告警及时触发
- [ ] 报告准确完整

### Phase 3: 持续改进（1周）

**目标**: 优化和增强

**步骤**:
1. ⏳ 分析告警数据
2. ⏳ 优化监控阈值
3. ⏳ 实施自动恢复机制
4. ⏳ 建立知识库

**验证**:
- [ ] 告警率下降
- [ ] 自动恢复成功率提升
- [ ] 文档完善
- [ ] 团队培训完成

---

## 监控指标

### Agent健康指标

| 指标 | 说明 | 目标值 | 测量方法 |
|------|------|--------|----------|
| Agent活跃度 | Agent无活动时间 | <6小时 | lastActivity检测 |
| Agent覆盖率 | 监控的Agent占比 | 100% | 配置文件检查 |
| 告警准确率 | 告警中真正需要干预的比例 | >90% | 人工审核 |

### 任务指标

| 指标 | 说明 | 目标值 | 测量方法 |
|------|------|--------|----------|
| 任务完成率 | 已完成/总任务 | >90% | TASK_STATE.json |
| 任务超时率 | 超时任务/活跃任务 | <10% | 任务状态检查 |
| 平均任务时间 | 任务从启动到完成 | <4小时 | 任务历史分析 |

### 系统指标

| 指标 | 说明 | 目标值 | 测量方法 |
|------|------|--------|----------|
| 监控可用性 | 监控脚本正常运行时间 | >99% | Cron日志 |
| 报告及时性 | 从问题发生到报告生成 | <10分钟 | 报告时间戳 |
| 日志完整性 | 日志无丢失或错误 | 100% | 日志检查 |

---

## 故障排查

### 常见问题

#### 1. Python环境问题

**症状**: 提示找不到Python或导入模块失败

**解决**:
```bash
# 检查Python版本
python3 --version

# 使用绝对路径
/usr/local/bin/python3 agent_health_monitor.py

# 或在crontab中指定路径
*/5 * * * * /usr/local/bin/python3 /path/to/agent_health_monitor.py
```

#### 2. TASK_STATE.json不存在或格式错误

**症状**: 提示无法读取任务状态

**解决**:
```bash
# 检查文件是否存在
ls -la TASK_STATE.json

# 验证JSON格式
python3 -m json.tool TASK_STATE.json

# 如有错误，手动修复或从备份恢复
cp task_state_backups/TASK_STATE_YYYYMMDD_HHMMSS.json TASK_STATE.json
```

#### 3. Cron jobs不运行

**症状**: 没有监控日志生成

**解决**:
```bash
# 检查cron服务
sudo launchctl list | grep cron

# 查看cron日志（macOS）
log show --predicate 'process == "cron"' --last 1h

# 手动测试cron命令
cd /path/to/.commander && python3 agent_health_monitor.py >> test.log 2>&1
```

#### 4. 权限问题

**症状**: 提示无法写入文件

**解决**:
```bash
# 设置执行权限
chmod +x agent_health_monitor.py
chmod +x task_timeout_handler.py
chmod +x deploy_monitoring.sh

# 设置目录写权限
chmod -R 755 /path/to/.commander
```

#### 5. 时区问题

**症状**: 时间计算错误（之前遇到过这个bug）

**解决**:
- ✅ 已修复：脚本会将所有datetime转换为naive datetime
- 如仍有问题，手动检查TASK_STATE.json中的时间格式

### 日志分析

**监控cron日志**:
```bash
# 查看最近的监控日志
tail -50 monitoring_cron.log

# 查找错误
grep ERROR monitoring_cron.log

# 统计运行次数
grep "Agent健康监控器启动" monitoring_cron.log | wc -l
```

**超时处理cron日志**:
```bash
# 查看最近的超时处理日志
tail -50 timeout_cron.log

# 查找处理记录
grep "已标记为timeout" timeout_cron.log
```

**告警日志**:
```bash
# 查看所有告警
cat AGENT_ALERTS.log

# 按级别过滤
grep CRITICAL AGENT_ALERTS.log
grep WARNING AGENT_ALERTS.log

# 按时间过滤（今天的告警）
grep $(date +%Y-%m-%d) AGENT_ALERTS.log
```

---

## 后续优化

### 短期（1-2周）

1. **优化告警阈值**
   - 根据实际运行数据调整threshold
   - 为不同Agent设置个性化阈值

2. **增强报告功能**
   - 添加图表可视化
   - 历史趋势分析
   - 邮件/Slack通知

3. **自动唤醒尝试**
   - 当Agent超时时，自动调用指挥官API
   - 尝试重新分配任务
   - 记录唤醒结果

### 中期（1-2个月）

1. **实时监控系统**
   - Web界面查看Agent状态
   - 实时任务进度
   - 系统健康指标仪表板

2. **预测性维护**
   - 基于历史数据预测Agent故障
   - 提前预警和干预
   - 自动优化任务分配

3. **集成告警渠道**
   - 邮件通知
   - Slack/微信通知
   - SMS告警（严重问题）

### 长期（3-6个月）

1. **自治Agent系统**
   - Agent自我诊断
   - 自动优化参数
   - 动态负载均衡

2. **多层监控架构**
   - 本地监控（当前方案）
   - 远程监控（多服务器）
   - 云端监控（集中管理）

3. **机器学习优化**
   - 异常检测
   - 智能告警（减少误报）
   - 自动调优

---

## 附录

### A. 文件结构

```
.commander/
├── agent_health_monitor.py          # Agent健康监控器
├── task_timeout_handler.py          # 任务超时处理器
├── deploy_monitoring.sh            # 部署脚本
├── agent_monitor_config.json       # 配置文件
├── AGENT_HEALTH_REPORT.md          # 健康监控报告
├── AGENT_ALERTS.log                # 告警日志
├── TASK_TIMEOUT_REPORT.md          # 超时处理报告
├── TASK_TIMEOUTS.log               # 超时日志
├── monitoring_cron.log             # 监控cron日志
├── timeout_cron.log                # 超时处理cron日志
├── DEPLOYMENT_REPORT.md            # 部署报告
├── AGENT_HEALTH_MONITOR.md         # 详细诊断报告
├── README_MONITORING.md            # 本文档
├── TASK_STATE.json                 # 任务状态（已存在）
├── task_state_backups/             # 备份目录
│   └── TASK_STATE_YYYYMMDD_HHMMSS.json
├── work_logs/                      # 工作日志
└── team_tasks/                     # 团队任务
```

### B. 命令参考

**手动监控**:
```bash
# 运行健康监控
python3 agent_health_monitor.py

# 运行超时处理
python3 task_timeout_handler.py

# 试运行超时处理
python3 task_timeout_handler.py --dry-run
```

**Cron管理**:
```bash
# 查看cron jobs
crontab -l

# 编辑cron jobs
crontab -e

# 删除所有cron jobs（谨慎！）
crontab -r
```

**日志查看**:
```bash
# 实时查看监控日志
tail -f monitoring_cron.log

# 实时查看超时日志
tail -f timeout_cron.log

# 查看告警
cat AGENT_ALERTS.log

# 查看健康报告
cat AGENT_HEALTH_REPORT.md

# 查看超时报告
cat TASK_TIMEOUT_REPORT.md
```

### C. 联系和支持

如有问题，请检查：
1. Python环境是否正常
2. TASK_STATE.json是否存在且格式正确
3. 日志文件中的错误信息
4. Cron服务是否运行

---

**文档版本**: 1.0
**最后更新**: 2026-02-27 04:50
**作者**: 创新者 (Innovator)
**审批**: 待指挥官确认

🦞 小龙虾 AI指挥官 | Agent监控系统 v1.0
