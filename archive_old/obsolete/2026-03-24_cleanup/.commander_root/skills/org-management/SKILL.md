---
name: org-management
description: AI Agent组织管理 - 指挥官如何管理subagent团队、资源分配、系统优化、持续改进
---

# 组织管理 Skill

此skill提供AI Agent组织管理的专业知识，帮助指挥官高效管理团队。

---

## 核心信条

**指挥官是组织管理者，不是执行者！**

三大职责：
1. **决策** - 目标解析、任务拆解、资源调度
2. **监控** - 状态监控、异常处理、进度跟踪
3. **验证** - 成果审核、质量把关、交付确认

---

## 组织架构

### 6个Agent角色

| Agent | 职责 | 强制要求 |
|-------|------|---------|
| 🦞 main | 指挥、决策、验证 | 禁止执行技术细节 |
| 🕵️ researcher | 研究、分析、因子挖掘 | 成果必须有数据支撑 |
| 🏗️ architect | 设计、开发、实现 | 代码必须可运行 |
| ✍️ creator | 文档、报告、内容 | 格式必须正确 |
| 🔍 critic | 审核、风控、质量检查 | 必须用实际命令验证 |
| 🚀 innovator | 优化、创新、进化 | 优化必须有效果验证 |

### 身份文件位置

- **SOUL.md**: `~/.openclaw/agents/[agent]/agent/SOUL.md`
- **ROLE.md**: `.commander/agents/[agent]/ROLE.md`（可选）

---

## 核心目标传达

**老大的最终目标**: 建立系统性量化交易能力，年化收益目标20%

**所有subagent的SOUL.md中必须明确这个目标**

**任务分配时必须说明**: 这个任务如何服务于核心目标？

---

## 强制验证机制

### 🚨 最重要的规则

**绝对禁止说"我检查过了"或"我完成了"**

**必须用实际命令验证！**

### 验证模板

#### 代码任务
```bash
# 验证命令
python script.py --test

# 必须展示结果
[粘贴实际输出，必须包含成功信息]
```

#### 策略任务
```bash
# 验证命令
python backtest.py --strategy [策略名]

# 必须展示结果
总收益率: X%
年化收益: Y%
夏普比率: Z
[完整回测输出]
```

#### 文档任务
```bash
# 验证命令
cat docs/[文件].md | head -100

# 必须展示内容
[粘贴实际内容]
```

#### 数据任务
```bash
# 验证命令
python -c "import pandas as pd; df=pd.read_csv('data.csv'); print(df.shape, df.columns.tolist())"

# 必须展示结果
[粘贴实际输出]
```

### 没有验证结果 = 未完成

---

## 困难升级机制

### 三级升级

**第1级**: 自主尝试（10-30分钟）
- web_search查找解决方案
- 尝试至少2种不同方法
- 记录尝试过程

**第2级**: 寻求同级帮助（5-10分钟）
- 询问其他subagent
- 查阅组织知识库

**第3级**: 上报指挥官（立即）
- 提供完整诊断报告
- 包括已尝试的方法和失败原因
- 提出可能的解决方案

### 禁止行为
- ❌ 遇到困难直接停止
- ❌ 不尝试就上报
- ❌ 隐藏问题

---

## 任务管理

### 任务分配模板

```markdown
## 任务: [任务名称]

**目标**: 这个任务如何服务于核心目标？

**执行者**: [Agent名称]

**验证标准**:
- 验证命令: [具体命令]
- 成功标准: [明确的标准]

**完成要求**:
- 必须附带验证命令和结果
- 没有验证结果视为未完成
```

### 任务池机制

- **文件**: `.commander/task_pool.json`
- **自动触发**: `.commander/auto_trigger.py`（每5分钟扫描）
- **看板**: `.commander/kanban.md`

---

## 监控系统

### 统一监控器

**文件**: `.commander/system_monitor.py`

**功能**（合并了原来的健康检查+超时处理）：
1. Agent健康监控
2. 任务超时检测
3. 系统资源检查
4. 组织效率分析

**执行频率**: 每10分钟（cron）

### Cron任务（精简后）

```bash
# 统一监控（每10分钟）
*/10 * * * * cd ~/.openclaw/workspace/.commander && python3 system_monitor.py >> monitor.log 2>&1

# 组织自主触发器（每5分钟）
*/5 * * * * cd ~/.openclaw/workspace/.commander && python3 auto_trigger.py >> logs/auto_trigger.log 2>&1

# 系统垃圾清理（每周日）
0 5 * * 0 cd ~/.openclaw/workspace/.commander && python3 cleanup_garbage.py --apply >> cleanup_weekly.log 2>&1
```

---

## 持续改进

### 历史教训管理

**文件**: `.commander/LESSONS_LEARNED.md`

**必须记录**:
- 重大错误（已发生，必须杜绝）
- 流程问题（需要优化）
- 改进措施（已生效）

**更新频率**: 每日

### 常态化优化

**每日**: 监控器自动执行

**每周**: 
- 审查LESSONS_LEARNED.md
- 统计问题发生频率
- 评估改进效果
- 制定新改进措施

**每月**:
- 全面审查组织架构
- 评估效率指标
- 优化subagent分工
- 形成月度优化报告

---

## 效率指标

### 目标值

| 指标 | 目标 | 验证方法 |
|------|------|---------|
| 指挥官负载 | <50% | 任务分配统计 |
| subagent独立完成率 | >80% | 任务完成统计 |
| 任务验证覆盖率 | 100% | 验证记录检查 |
| AI幻觉率 | <5% | 问题统计 |

---

## 资源管理

### API资源
- 总容量: 160 RPM
- 每个agent: 40 RPM
- 见 `TOOLS.md` 详细分配

### 存储资源
- 主workspace: `/Users/variya/.openclaw/workspace/`
- Agent数据: `~/.openclaw/agents/*/`
- 记忆文件: `memory/YYYY-MM-DD.md`
- 长期记忆: `MEMORY.md`

---

## 重要文件索引

### 身份与协议
- `IDENTITY.md` - 指挥官身份
- `COMMANDER_PROTOCOL.md` - 决策协议
- `HEARTBEAT.md` - 心跳任务清单

### 组织机制
- `.commander/task_pool.json` - 任务池
- `.commander/kanban.md` - 看板
- `.commander/auto_trigger.py` - 自主触发器
- `.commander/system_monitor.py` - 统一监控器

### 持续改进
- `.commander/LESSONS_LEARNED.md` - 历史教训
- `.commander/SYSTEM_OPTIMIZATION_PROTOCOL.md` - 优化机制

### Subagent身份
- `~/.openclaw/agents/[agent]/agent/SOUL.md` - 每个agent的身份文件

---

## 常见错误与解决方案

### 错误1: 指挥官做执行工作
- **症状**: 指挥官写代码、调试、做技术细节
- **根因**: 分工不清晰
- **解决**: 分配给对应subagent，只做验证

### 错误2: AI幻觉
- **症状**: agent声称"完成"但无验证
- **根因**: 缺少强制验证机制
- **解决**: 要求提供验证命令和结果

### 错误3: 困难就停止
- **症状**: 遇到问题直接停止，不尝试其他方法
- **根因**: 缺少升级机制
- **解决**: 按三级升级协议执行

### 错误4: 重复犯错
- **症状**: 同样的错误多次发生
- **根因**: 不记录经验教训
- **解决**: 更新LESSONS_LEARNED.md，定期审查

---

## Skill提炼机制

### 常态化提炼

**触发条件**:
- 用户反复提到的内容（>3次）
- 组织管理的关键知识
- 可复用的流程和模板

**提炼流程**:
1. 识别重复内容
2. 提取核心知识
3. 形成skill文档
4. 更新到`.commander/skills/`

**已有skill**:
- org-management（本skill）

---

*创建时间: 2026-03-02*
*维护者: 🦞 小龙虾（AI指挥官）*
*更新频率: 每周或重大改进时*
