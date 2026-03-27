# API密钥分配表

**更新时间**: 2026-02-27 05:22
**总容量**: 6个NVIDIA API密钥（每个40 RPM）= **240 RPM**

---

## 📊 Agent分配

| Agent | API Key | 密钥ID | 描述 | 工具权限 |
|-------|---------|--------|------|---------|
| 🦞 小龙虾 (main) | nvidia | nvapi-q7-... | 核心指挥官 | Full |
| 🕵️ 研究员 | nvidia-key1 | nvapi-Vuz... | 数据分析+网络 | Full (11工具) |
| 🏗️ 架构师 | nvidia-key2 | nvapi-w1P... | 架构+代码 | Coding (7工具) |
| ✍️ 创作者 | nvidia-key5 | nvapi-hvSN... | 文档+生成 | Coding (7工具) |
| 🔍 评审官 | nvidia-key3 | nvapi-psC... | 审核报告 | Coding (4工具) |
| 🚀 创新者 | nvidia-key4 | nvapi-TuA... | 系统进化 | Full |

---

## 🔑 密钥详情

### 1. nvidia (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)
- **分配**: main (小龙虾)
- **容量**: 40 RPM
- **用途**: 核心决策、监控、协调

### 2. nvidia-key1 (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)
- **分配**: researcher (研究员)
- **容量**: 40 RPM
- **用途**: 数据分析、网络研究

### 3. nvidia-key2 (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)
- **分配**: architect (架构师)
- **容量**: 40 RPM
- **用途**: 架构设计、代码实现

### 4. nvidia-key3 (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)
- **分配**: critic (评审官)
- **容量**: 40 RPM
- **用途**: 审核报告、风险评估

### 5. nvidia-key4 (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)
- **分配**: innovator (创新者)
- **容量**: 40 RPM
- **用途**: 系统进化、优化设计

### 6. nvidia-key5 (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)
- **分配**: creator (创作者)
- **容量**: 40 RPM
- **用途**: 文档生成、代码生成

---

## 📈 使用统计

**总容量**: 240 RPM
**当前分配**: 6个Agent，每个独立密钥

**负载预估**:
- main: 低-中（决策+监控）
- researcher: 高（数据分析+网络）
- architect: 中（架构设计）
- creator: 中（文档生成）
- critic: 低-中（审核）
- innovator: 中（优化设计）

---

## 🔄 变更历史

### 2026-02-27 05:22
- ✅ 添加 nvidia-key4 分配给 innovator
- ✅ 添加 nvidia-key5 分配给 creator
- ✅ architect 和 creator 不再共享密钥（各自独立）

**Before**:
- main: nvidia
- researcher: nvidia-key1
- architect: nvidia-key2
- creator: nvidia-key2 (共享)
- critic: nvidia-key3
- innovator: nvidia (与main共享)

**After**:
- main: nvidia
- researcher: nvidia-key1
- architect: nvidia-key2
- creator: nvidia-key5 (独立)
- critic: nvidia-key3
- innovator: nvidia-key4 (独立)

---

## 🎯 配置文件

**文件**: `~/.openclaw/openclaw.json`
**工具权限**: `agent_permission_manager.py`

**验证命令**:
```bash
python3 agent_permission_manager.py validate
```

---

**维护者**: 小龙虾 (main)
