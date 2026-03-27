# 🔐 Agent工具权限配置记录

## 修改时间
2026-02-27 04:45

## 修改原因
老大指正：没有风险的T0以下任务应该授权agent自己执行，而不是指挥官代劳。

研究员subagent无法读取主workspace的本地文件，因此无法完成P0任务。

---

## 已修改的权限

### 🕵️ 研究员
**新增工具**:
- `read` - 读取本地文件（从绝对路径）
- `write` - 创建/写入文件
- `edit` - 精确编辑文件
- `exec` - 执行shell命令（用于数据分析/脚本）
- `process` - 管理后台进程
- `browser` - 浏览器控制
- `canvas` - Canvas展示
- 原有保留：`web_search`, `web_fetch`, `memory_search`, `memory_get`

**subagents权限**: 允许启动任意agent (`["*"]`)

---

### 🏗️ 架构师
**新增工具**:
- `read` - 读取架构文档代码
- `write` - 创建架构设计文档
- `edit` - 修改配置文件
- `exec` - 运行架构验证脚本
- `process` - 管理进程
- 原有保留：`web_search`, `web_fetch`

**profile**: `coding` (保留)

**subagents权限**: 允许启动任意agent (`["*"]`)

---

### ✍️ 创作者
**新增工具**:
- `read` - 读取素材/参考资料
- `write` - 创建文档/代码
- `edit` - 修改内容
- `exec` - 运行代码生成/测试
- 原有保留：`web_search`, `web_fetch`

**profile**: `coding` (保留)

**subagents权限**: 允许启动任意agent (`["*"]`)

---

### 🔍 评审官
**新增工具**:
- `read` - 读取待评审文档
- `write` - 输出评审报告
- `edit` - 注释修改建议
- 原有保留：`web_search`

**profile**: `coding` (保留)

**subagents权限**: 允许启动任意agent (`["*"]`)

---

### 🚀 创新者
**完整权限**:
- `profile`: `full` - 获得除session/system工具外的所有工具
- 包括：`read`, `write`, `edit`, `exec`, `process`, `browser`, `canvas`, `web_search`, `web_fetch`, `memory_search`, `memory_get`, 等等

**职责**: 系统进化、Agent升级、架构优化

**subagents权限**: 允许启动任意agent (`["*"]`)

---

## 配置文件位置
`~/.openclaw/openclaw.json`

---

## 生效方式
配置文件保存后，下次创建subagents时自动生效。
已运行的subagent需要重新创建才能获得新权限。

---

## 权限原则

1. **安全第一**: 不授权的agent仍然无法使用相应工具
2. **职责匹配**:
   - 研究员: 数据分析 + 网络研究
   - 架构师: 代码 +架构设计
   - 创作者: 文档 + 代码生成
   - 评审官: 只读 + 审核报告
   - 创新者: 全功能（需要）

3. **风险评估**: 外部actions (邮件/发帖) 仍需决策

---

*由指挥官小龙虾🦞配置*
