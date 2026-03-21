# 组织自主机制 - 文件清单

**创建时间**: 2026-03-01 02:17 GMT+8
**创建者**: 创新者 (Innovator)

---

## 📦 文件结构

```
.commander/
├── task_pool.json              # 任务池 (核心) - 持久化存储所有任务
├── kanban.md                   # 看板 (可视化) - 实时任务状态展示
├── auto_trigger.py             # 触发器 (引擎) - 自动扫描、分配、监控
├── auto_trigger.log            # 触发器日志
├── AUTONOMOUS_MECHANISM.md     # 机制文档 (完整版) - 详细设计说明
├── QUICKSTART_AUTONOMY.md      # 快速上手指南 - 5分钟学会使用
└── README_AUTONOMY.md          # 本文件 - 文件清单和索引
```

---

## 📖 文件说明

### 1️⃣ task_pool.json (任务池)

**用途**: 持久化存储所有任务和Agent状态

**内容**:
- 任务列表 (pending, in_progress, completed, failed)
- Agent信息 (状态、能力、当前任务)
- 统计数据
- 自动分配规则
- 重试策略

**谁会使用**:
- 触发器 - 读取和更新
- Agent - 读取分配给自己的任务
- 用户 - 可直接编辑添加任务

### 2️⃣ kanban.md (看板)

**用途**: 可视化展示任务进度和Agent状态

**内容**:
- 任务统计 (待执行、进行中、已完成、失败)
- 各状态下的任务列表
- Agent状态监控
- 自动配置状态
- 提醒规则

**谁会使用**:
- 触发器 - 自动生成
- 用户 - 查看进度
- **不要手动编辑**

### 3️⃣ auto_trigger.py (触发器)

**用途**: 自动扫描、分配任务，监控系统运行

**功能**:
- 每5分钟扫描任务池
- 自动分配待执行任务
- 检查超时和失败任务
- 更新看板
- 记录日志

**运行方式**:
```bash
# 持续运行
python3 auto_trigger.py

# 单次扫描
python3 auto_trigger.py --once

# 添加任务
python3 auto_trigger.py add "标题" 类型 优先级
```

### 4️⃣ auto_trigger.log (日志)

**用途**: 记录所有系统操作和事件

**内容**:
- 扫描记录
- 任务分配日志
- 任务失败和重试
- 系统警告

### 5️⃣ AUTONOMOUS_MECHANISM.md (机制文档)

**用途**: 完整的自主机制设计文档

**内容**:
- 核心目标
- 问题分析
- 架构设计
- 任务池机制
- 看板机制
- 自主工作触发器
- 失败重试机制
- Agent角色与职责
- 工作流程
- 使用指南
- 最佳实践
- 未来扩展

**适合**: 深入了解系统设计的开发者

### 6️⃣ QUICKSTART_AUTONOMY.md (快速上手)

**用途**: 5分钟快速上手指南

**内容**:
- 5分钟快速开始
- Agent自主工作流程
- 常用命令
- 核心概念
- 注意事项

**适合**: 想要快速使用的所有Agent

### 7️⃣ README_AUTONOMY.md (本文件)

**用途**: 文件清单和索引

**内容**:
- 文件结构
- 文件说明
- 快速开始
- 工作流程
- 常见问题

---

## 🚀 快速开始

### 1. 启动触发器 (必须!)

```bash
cd /Users/variya/.openclaw/workspace/.commander
python3 auto_trigger.py
```

**注意**: 触发器必须持续运行，否则任务无法自动分配！

### 2. 创建任务

```bash
python3 auto_trigger.py add "研究Alpha因子" research high
```

### 3. 查看自动分配

触发器会自动将任务分配给合适的Agent。

### 4. 查看看板

```bash
cat kanban.md
```

---

## 🔄 工作流程

### 创建任务

```
用户创建任务
    ↓
task_pool.json: pending
    ↓
触发器扫描 (5分钟)
    ↓
自动分配给合适的Agent
    ↓
task_pool.json: in_progress
    ↓
Agent执行任务，更新进度
    ↓
完成 → task_pool.json: completed
失败 → task_pool.json: failed → 重试
    ↓
触发器更新看板
    ↓
kanban.md 更新
```

### Agent状态

```
idle (空闲)
    ↓
分配任务
    ↓
active (活跃)
    ↓
任务完成
    ↓
idle (空闲)
```

---

## 🎯 核心特性

✅ **任务池化** - 所有任务统一管理，全局可见
✅ **自主领取** - Agent主动扫描并领取适合的任务
✅ **自动分配** - 基于能力和优先级智能分配
✅ **实时监控** - 看板可视化任务进度
✅ **失败重试** - 自动分析并重试失败任务
✅ **状态同步** - Agent状态实时同步系统

---

## 🔧 配置参数

| 参数 | 位置 | 默认值 | 说明 |
|------|------|--------|------|
| 扫描间隔 | auto_trigger.py | 300秒 | 触发器扫描频率 |
| 最大重试 | task_pool.json | 3次 | 任务失败重试次数 |
| 超时时间 | auto_trigger.py | 2小时 | 任务执行超时时间 |
| 积压阈值 | auto_trigger.py | 10个 | 任务积压警告阈值 |
| 最大并发 | auto_trigger.py | 3个 | Agent最大并发任务数 |

---

## 📊 任务类型与Agent映射

| 任务类型 | 主要分配 | 备选分配 | 说明 |
|---------|---------|---------|------|
| research | researcher | innovator | 研究、分析 |
| analysis | researcher | innovator | 数据分析 |
| execution | executor | commander | 执行、自动化 |
| automation | executor | - | 自动化脚本 |
| design | innovator | commander | 设计、架构 |
| coordination | commander | - | 协调、决策 |
| monitoring | executor | researcher | 监控、报告 |
| generic | executor | researcher/innovator/commander | 通用任务 |

---

## 🤖 Agent列表

| Agent ID | 名称 | 状态 | 当前任务 |
|----------|------|------|----------|
| commander | 指挥官 | idle | 0个 |
| researcher | 研究员 | active | 1个 |
| executor | 执行者 | active | 1个 |
| innovator | 创新者 | active | 1个 |

---

## ⚠️ 常见问题

### Q: 任务一直没有执行?

**A**: 检查触发器是否正在运行
```bash
ps aux | grep auto_trigger.py
```

如果没在运行，启动它：
```bash
python3 auto_trigger.py
```

### Q: 看板不更新?

**A**: 看板由触发器自动生成，确保触发器正在运行。

### Q: 如何手动添加任务?

**A**: 直接编辑 `task_pool.json` 或使用命令行：
```bash
python3 auto_trigger.py add "标题" 类型 优先级
```

### Q: Agent如何自主工作?

**A**: 参考快速上手指南中的示例代码。

### Q: 如何查看任务进度?

**A**: 查看日志或看板：
```bash
tail -f auto_trigger.log
cat kanban.md
```

---

## 📚 相关文档

| 文档 | 用途 | 目标读者 |
|------|------|---------|
| AUTONOMOUS_MECHANISM.md | 完整设计文档 | 开发者 |
| QUICKSTART_AUTONOMY.md | 快速上手指南 | 所有Agent |
| README_AUTONOMY.md | 文件清单 (本文件) | 所有用户 |

---

## 🎓 学习路径

### 新手

1. 阅读 `QUICKSTART_AUTONOMY.md` (5分钟)
2. 启动触发器
3. 创建任务
4. 查看看板

### 进阶

1. 阅读本文件 README
2. 理解任务池结构
3. 了解Agent状态流转
4. 修改配置参数

### 专家

1. 阅读 `AUTONOMOUS_MECHANISM.md` (完整版)
2. 理解系统架构
3. 扩展功能
4. 优化性能

---

## 🚨 重要提醒

1. **触发器必须一直运行** - 否则任务无法自动分配
2. **不要手动编辑看板** - 看板由触发器自动生成
3. **Agent及时更新进度** - 让看板反映真实状态
4. **合理设置优先级** - 避免所有任务都是高优先级
5. **任务类型要准确** - 确保分配给正确的Agent

---

## 📞 联系方式

如有问题或建议：
- **负责人**: 创新者 (Innovator)
- **工作空间**: /Users/variya/.openclaw/workspace
- **文档位置**: .commander/

---

## ✨ 版本信息

| 项目 | 版本 | 日期 |
|------|------|------|
| 机制版本 | 1.0 | 2026-03-01 |
| 触发器版本 | 1.0 | 2026-03-01 |
| 文档版本 | 1.0 | 2026-03-01 |

---

**🎯 核心理念**: 让组织自主运转，而不是依赖手动分配。
**✨ 目标**: 指挥官不再成为瓶颈，所有Agent都能自主工作。
