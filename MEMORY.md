# MEMORY.md - 长期记忆索引

> 这是我的长期记忆索引，指向具体的细节文件
> 只在私聊会话加载，群聊不加载

## 🦞 个人信息

- **名称**：小龙虾
- **角色**：AI Agent团队指挥官
- **核心信条**："为什么做？最终要达成什么？所有行动是否为此服务？"
- **职责**：目标解析、宏观规划、资源调度、状态监控、最终交付
- **管理频率**：根据心跳机制自主决策

---

## 👤 用户信息

- **称呼**：老大
- **时区**：GMT+8 (Asia/Shanghai)
- **期望**：AI Agent团队指挥官，负责目标解析、流程设计、专家团队分派、状态监控、严格交付

---

## 📂 记忆索引

### 活跃项目（2026-03-20更新）

#### 1. WildQuest Matrix A股量化系统 v6.4
- **路径**: `projects/a-stock-advisor 6/`
- **版本**: 6.4.0
- **状态**: 活跃开发中
- **负责人**: 老大（用户）
- **文档**: `README.md`, `COMMANDS.md`, `ARCHITECTURE_GUIDE.md`
- **特性**:
  - 三层架构设计（核心业务流程/支撑体系/基础设施）
  - v6.4新增：策略模块增强（股票池筛选、市场环境检查、信号质量过滤、组合风险监控）
  - v6.3新增：智能推送系统（盘前推送、盘中推送、盘后日报、实时告警）
  - 完整的量化交易功能（因子挖掘、策略构建、回测系统、风险管理）

#### 2. Microsoft RD-Agent
- **路径**: `projects/rdagent-temp/`
- **类型**: AI辅助量化研究框架（开源项目）
- **来源**: Microsoft GitHub (`https://github.com/microsoft/RD-Agent`)
- **状态**: 已下载，待评估
- **文档**: `README.md`, `pyproject.toml`, `docs/`
- **说明**: Research-Development Agent，自动化量化研究流程的AI框架

#### 3. 微信Channel研究项目
- **路径**: `projects/wechat-channel-research/`
- **创建时间**: 2026-03-19
- **负责人**: 🦞小龙虾
- **状态**: 研究进行中
- **进度**:
  - ✅ 插件配置分析
  - ✅ 实现代码审查
  - ✅ 环境变量识别
  - ⏳ 环境变量配置方法
  - ⏳ 消息发送测试
  - ⏳ 使用指南编写
- **目标**: 研究如何在Qclaw中使用wechat-access channel发送消息

### 已归档项目
- **`projects/a-stock-advisor/`** - 旧版A股量化系统（已删除，仅保留logs空壳，已于2026-03-20清理）

### 任务状态
- **`memory/active-tasks.md`** - 活跃任务追踪
  - 崩溃恢复存档
  - 当前任务列表
  - 关键状态

### 已终止项目
- **`memory/okx-project-terminated.md`** - OKX项目终止记录
  - 备份位置：`~/Desktop/okx_backup_20260301.tar.gz`
  - 项目总结（2026-02-25 至 2026-03-01）

### 组织机制
- **`workflow/`** - Sentinel FlowLoop Engine V3.0 ⭐ 新增目录
  - `SENTINEL_LOG.json` - 系统日志（模式、统计、历史）
  - `TASK_POOL.md` - 任务池（所有任务）
  - `ARCHIVE.md` - 统一归档（已完成任务）
  - `agents/REGISTRY.md` - Agent注册表（6个Agent已注册）
  - `agents/LOCK_STATE.json` - 任务锁状态
  - `memory/CONTEXT_SUMMARY.md` - 上下文摘要库
  - `memory/PATTERNS.md` - 模式学习库
  - `README.md` - 完整文档
- **`.commander/task_pool.json`** - 旧版任务池机制（已废弃）
- **`.commander/kanban.md`** - 看板机制
- **`.commander/auto_trigger.py`** - 自主触发器（每5分钟扫描）
- **`.commander/AUTONOMOUS_MECHANISM.md`** - 组织自主机制文档
- **`.commander/system_monitor.py`** - 统一监控器（合并健康检查+超时处理，每10分钟）
- **`.commander/LESSONS_LEARNED.md`** - 历史错误与教训清单
- **`.commander/SYSTEM_OPTIMIZATION_PROTOCOL.md`** - 常态化优化机制

### Sentinel V3 核心（2026-03-12部署）
**部署状态**: ✅ 正常运行 (mode: normal)
**核心能力**:
- 10步心跳工作流（自检→T0监控→任务化→上下文压缩→领取→执行→归档→探索→清理→通知）
- 任务锁机制（30分钟超时释放）
- 上下文压缩（自动检测长对话>50轮或>10K token）
- 模式学习（失败模式记录+智能优化）
- 主动探索（空窗期触发：40%延续+35%复盘+25%全局）
- 负载均衡（任务领取前检查Agent负载）
- 智能升级（优先级衰减+P0调查机制）

**部署时间**: 2026-03-12 22:33 GMT+8
**文档**: `workflow/README.md`

### 每日记录
- **`memory/YYYY-MM-DD.md`** - 每日操作日志（唯一记录源）
  - 原始记录 + 大事总结 + 待办事项
  - 整合了原cron生成的每日总结
  - 说明：`memory/README.md`

---

## 🔧 工具配置

- **API密钥**：见 `TOOLS.md`
- **GitHub**: `variyaone` (Gitee)

---

## 📅 日程任务配置（2026-03-05更新）

### 当前Cron任务（8个）
| 时间 | 任务名 | 脚本 | 优先级 | 状态 |
|------|--------|------|--------|------|
| 3:00 | health_check | health_check.py | 中 | ✅ |
| 7:00 | morning_data_check | data_update_v2.py | 高 | ✅ |
| 8:00 | morning_master_push | daily_master.py | 关键 | ✅ 主流程 |
| 8:00 | morning_push | paper_trading_push.py | 关键 | ⚠️ 待确认 |
| 16:00 | evening_data_check | data_update_v2.py | 高 | ✅ |
| 18:30 | daily_selection_push | daily_master.py | 关键 | ✅ |
| 每小时 | monitor_collector | monitor_collector.py | 低 | ✅ |
| 周日2:00 | weekly_backtest | run_backtest.py | 中 | ✅ |

### ⚠️ 待解决问题
1. **8:00任务冲突**：morning_push和morning_master_push同时执行
   - morning_master_push已包含完整流程（数据+因子+选股+报告+推送）
   - morning_push可能冗余，需验证paper_trading_push.py功能

### 系统状态文件（2026-03-05确认）
| 文件 | 状态 | 大小 | 更新时间 |
|------|------|------|----------|
| portfolio_state.json | ✅ | 2.9KB | 2026-03-05 04:20 |
| factor_dynamic_weights.json | ✅ | 449B | 2026-03-05 04:20 |
| factor_evaluation_history.json | ✅ | 6.5KB | 2026-03-05 04:20 |
| selection_result.json | ✅ | 3.3KB | 2026-03-05 04:20 |

### 模拟持仓状态（2026-03-05）
- 总资产：100万元
- 现金：40.8万元
- 持仓：59.2万元（5只股票）
- 持仓天数：0天（今日新建仓）

---

## 📊 Agent团队

| Agent | API | SOUL.md | 专精 | 独立性 |
|-------|-----|---------|------|--------|
| 🦞 小龙虾 (main) | nvidia | ✅ | 指挥、协调、决策 | N/A |
| 🕵️ 研究员 (researcher) | nvidia-key1 | ✅ | 市场研究、数据分析、因子挖掘 | 🔄 提升 |
| 🏗️ 架构师 (architect) | nvidia-key2 | ✅ | 系统设计、策略设计、代码实现 | 🔄 提升 |
| ✍️ 创作者 (creator) | nvidia-key3 | ✅ | 文档生成、报告撰写、内容创作 | 🔄 提升 |
| 🔍 评审官 (critic) | nvidia-key4 | ✅ | 代码审核、风险评估、质量检查 | 🔄 提升 |
| 🧩 整理者 (curator) | nvidia-key5 | ✅ | 系统维护、简洁管理、优化 | 🔄 提升 |

**SOUL.md位置**：`~/.openclaw/agents/[agent]/agent/SOUL.md`
**强制验证**：所有subagent声称"完成"时，必须用实际命令验证

### 组织分工（2026-03-02优化）

#### 🦞 指挥官（main）
- ✅ 决策制定（目标解析、任务拆解、资源调度）
- ✅ 进度监控（任务状态、异常处理）
- ✅ 交付验证（成果审核、质量把关）
- ❌ 禁止：写代码、调试、执行技术细节

#### 🕵️ 研究员（researcher）
- ✅ 独立完成市场研究和数据分析
- ✅ 研究成果必须有数据支撑
- ✅ 自主验证研究结论
- 🔥 目标：因子挖掘、市场趋势分析

#### 🏗️ 架构师（architect）
- ✅ 独立完成策略开发和代码实现
- ✅ 代码必须可运行，策略必须可回测
- ✅ 自主测试代码质量
- 🔥 目标：系统优化、策略开发

#### ✍️ 创作者（creator）
- ✅ 独立生成文档和报告
- ✅ 确保内容格式正确可读
- 🔥 目标：文档质量、知识沉淀

#### 🔍 评审官（critic）
- ✅ 独立审核所有交付成果
- ✅ 使用实际命令验证（禁止说"我检查过了"）
- ✅ 不合格的坚决不通过
- 🔥 目标：质量控制、风险管理

#### 🚀 整理者（innovator）
- ✅ Sentinel工作流监控和维护
- ✅ 文件整理和目录优化
- ✅ 系统性能优化
- 🔥 目标：组织效率提升、系统进化

---

## 🚫 限制

- **Brave Search**：中国大陆不可用（被墙）
- **Web Fetch**：正常可用（提供具体URL）

---

## 🎯 核心目标（最高优先级）

**老大的最终目标**：建立系统性量化交易能力，年化收益目标20%

**所有subagent的SOUL.md中都明确传达了这个目标**

**当前阶段**：系统自动运行 + 模拟盘验证 + 真实数据获取

**核心机制**：
- ✅ 组织自主机制（任务池 + 自动触发器）
- ✅ 回测引擎V2（成本模型 + 基准模型）
- ✅ 模拟盘系统（模块化设计）
- ✅ 统一监控器（system_monitor.py合并健康检查+超时处理）
- ✅ 强制验证机制（所有声称"完成"的任务必须有验证命令和结果）
- ✅ 常态化优化机制（每日监控+每周优化+每月复盘）
- ⏳ 真实A股数据获取（待解决方案）
- ⏳ 模拟盘实际运行（待启动）

**组织优化重点（2026-03-02启动）**：
- 🔴 P0: subagent独立性提升（已创建SOUL.md，强制验证，核心目标传达）
- 🔴 P0: 消除AI幻觉（强制要求验证命令和结果）
- 🔴 P0: 指挥官降负（从执行转向决策）
- 🟡 P1: 组织效率优化（每周复盘，持续改进）

**Boss明确要求（2026-02-28）**：
- "寻找圣杯"和"管理不确定性"
- 目标：建立系统性能力，而非找到"神模型"
- 核心任务：确定性任务脚本化，减少对agent的依赖
- 资源优化：优化算力、内存、网络负载

**回测引擎性能（V2）**：
- 总收益率: 946.16%
- 年化收益率: 83.61%
- 夏普比率: 2.05
- 最大回撤: -12.56%
- 基准模型准确率: 74.25%

**自动化架构**：
- 三层设计：自动化脚本层 → Cron调度层 → Agent监控层
- 资源优化：Agent调用减少80%，内存峰值降低75%，CPU峰值降低37.5%

---

## 📁 重要文件索引

### A股量化系统
- 项目路径：`/Users/variya/.openclaw/workspace/projects/a-stock-advisor/`
- 系统手册：`MANUAL.md`
- 因子库：`reports/factor_library.md`（80+因子）
- 策略库：`reports/strategy_library.md`（5大类）

### 组织机制
- `.commander/task_pool.json` - 任务池
- `.commander/kanban.md` - 看板
- `.commander/auto_trigger.py` - 自主触发器

### 自动化系统
- 脚本目录：`scripts/`
- Cron配置：`config/cron_config.json`
- 架构文档：`reports/automation_architecture.md`

---

*最后更新：2026-03-12 22:33*
*战略重心：A股量化系统 + Sentinel V3*
*指挥官小龙虾🦞*

---

## 🔄 心跳任务更新（2026-03-05 V2）

### HEARTBEAT.md全面更新到V2
**新增检查项**：系统状态文件监控、Cron任务监控（8个）、快速诊断命令、异常处理流程
**核心状态**：A股项目V2已正式运行
**参考文档**：`memory/agent_soul更新记录_2026-03-05.md`

### Agent SOUL.md全面更新到V2
**更新范围**：架构师、研究员、创作者、评审官、整理者
**新增内容**：
- 核心系统知识（主控流程、因子评估、持仓跟踪）
- 快速诊断命令（27个）
- 验证要求模板（10个）
- 优化方向建议（P0/P1/P2优先级）

