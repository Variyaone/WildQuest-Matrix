# 📖 Agent权限管理系统使用指南

本指南帮助你快速上手Agent权限管理系统。

---

## 快速开始

### 1. 查看可用模板

```bash
cd ~/.openclaw/workspace/.commander
python agent_permission_manager.py list
```

输出示例：
```
📋 Agent权限列表
============================================================

🤖 小龙虾 (main)
   模板: 未设置
   配置: profile = full

🤖 研究员 (researcher)
   模板: researcher
   允许: read, write, edit, exec, process, web_search, web_fetch, browser, canvas, memory_search, memory_get
```

### 2. 应用权限模板

```bash
# 为researcher应用researcher模板
python agent_permission_manager.py apply researcher researcher

# 为creator应用creator模板，并额外添加canvas工具
python agent_permission_manager.py apply creator creator canvas
```

---

## 添加新Agent的权限配置

### 步骤1：选择合适模板

根据Agent的职责选择模板：

| 模板 | 适用场景 | 工具数 |
|------|----------|--------|
| **full** | 系统管理员、核心Agent | 全部 |
| **researcher** | 数据分析、网络研究 | 11 |
| **architect** | 架构设计、代码实现 | 7 |
| **creator** | 文档生成、代码创作 | 6 |
| **critic** | 代码评审、文档审核 | 4 |
| **minimal** | 临时测试Agent | 3 |

### 步骤2：在openclaw.json中添加Agent

```json5
{
  "id": "my-new-agent",
  "name": "我的Agent",
  "workspace": "/path/to/workspace",
  "tools": {
    "template": "researcher"
  }
}
```

### 步骤3：应用模板（可选）

如果已经创建了Agent，使用脚本应用模板：

```bash
python agent_permission_manager.py apply my-new-agent researcher
```

### 步骤4：验证权限

```bash
python agent_permission_manager.py compare my-new-agent researcher
```

---

## 修改现有Agent权限

### 场景1：切换模板

```bash
# 将creator从architect模板改为researcher模板
python agent_permission_manager.py apply creator researcher
```

### 场景2：添加额外工具

```bash
# 为researcher添加额外的工具
python agent_permission_manager.py apply researcher researcher tts message
```

### 场景3：移除工具（deny）

`openclaw.json`中手动配置：

```json5
{
  "id": "researcher",
  "tools": {
    "template": "researcher",
    "deny": ["browser", "canvas"]  // 拒绝这些工具
  }
}
```

---

## 常见操作

### 1. 批量授权

创建批量脚本`batch_apply.py`:

```python
#!/usr/bin/env python3
from agent_permission_manager import PermissionManager

# Agent到模板的映射
AGENT_TEMPLATES = {
    "researcher": "researcher",
    "architect": "architect",
    "creator": "creator",
    "critic": "critic",
    "innovator": "full"
}

manager = PermissionManager()
for agent_id, template in AGENT_TEMPLATES.items():
    print(f"处理Agent: {agent_id}")
    manager.apply_template(agent_id, template)

manager.save_config()
```

运行：
```bash
python batch_apply.py
```

### 2. 撤销权限

```bash
# 将Agent降级到minimal权限
python agent_permission_manager.py apply creator minimal
```

### 3. 检查权限一致性

```bash
# 验证所有Agent的权限配置
python agent_permission_manager.py validate
```

### 4. 对比权限差异

```bash
# 查看agent1和agent2的权限差异
python agent_permission_manager.py compare researcher researcher
python agent_permission_manager.py compare architect researcher
```

---

## 配置重构（方案A：模板引用）

### 步骤1：预览迁移

```bash
# 不实际修改，只显示预览
python agent_permission_manager.py migrate researcher researcher
```

输出：
```
🔍 迁移预览: 研究员 (researcher)
   原始配置: {"allow": ["read", "write", ...], "profile": "full"}
   新配置:   {"template": "researcher"}
```

### 步骤2：执行迁移

```bash
# 实际修改配置
python agent_permission_manager.py migrate researcher researcher --apply
```

### 步骤3：迁移所有Agent

创建批量迁移脚本`migrate_all.py`:

```python
#!/usr/bin/env python3
from agent_permission_manager import PermissionManager

AGENTS = {
    "researcher": "researcher",
    "architect": "architect",
    "creator": "creator",
    "critic": "critic",
    "innovator": "full",
    "main": "full"
}

manager = PermissionManager()
for agent_id, template in AGENTS.items():
    print(f"迁移Agent: {agent_id} -> {template}")
    manager.migrate_to_template(agent_id, template, dry_run=False)

manager.save_config()
print("✅ 迁移完成")
```

---

## 配置重构（方案B：外置配置）

### 步骤1：导出当前权限配置

```bash
python agent_permission_manager.py export
```

生成文件：`~/.openclaw/workspace/.commander/agent_permissions.json`

### 步骤2：修改导出的配置

编辑`agent_permissions.json`，调整Agent的模板引用：

```json5
{
  "agents": {
    "researcher": {
      "template": "researcher",
      "overrides": {}
    },
    "creator": {
      "template": "creator",
      "overrides": {
        "allow": ["canvas"]
      }
    }
  }
}
```

### 步骤3：导入配置（预览）

```bash
python agent_permission_manager.py import agent_permissions.json
```

### 步骤4：导入配置（应用）

```bash
python agent_permission_manager.py import agent_permissions.json --apply
```

---

## 创建自定义模板

### 步骤1：编辑模板定义

编辑`agent_permission_templates.md`或`agent_permission_manager.py`中的`PERMISSION_TEMPLATES`：

```python
PERMISSION_TEMPLATES = {
    # ... 其他模板
    "data-scientist": {
        "name": "数据科学家",
        "description": "专注于数据挖掘和机器学习",
        "inherits": "researcher",
        "tools": {
            "allow": [
                "read", "write", "edit", "exec", "process",
                "web_search", "web_fetch"
            ]
        }
    }
}
```

### 步骤2：应用新模板

```bash
python agent_permission_manager.py apply researcher data-scientist
```

---

## 故障排查

### 问题1：模板不存在

**错误信息**:
```
❌ 模板不存在: invalid-template
```

**解决方法**:
- 检查模板名称拼写
- 查看`agent_permission_templates.md`中的可用模板
- 如果是新模板，需要先定义

### 问题2：Agent不存在

**错误信息**:
```
❌ Agent不存在: unknown-agent
```

**解决方法**:
- 检查Agent ID拼写
- 使用`agent_permission_manager.py list`查看所有Agent
- 先在`openclaw.json`中创建Agent

### 问题3：权限验证失败

**错误信息**:
```
⚠️  发现 2 个问题:
   - researcher: 'exec'在deny列表中但不在allow列表中
```

**解决方法**:
- 检查配置中的`deny`和`allow`列表
- 移除冗余的deny规则
- 根据提示调整配置

### 问题4：配置文件保存失败

**错误信息**:
```
❌ 保存配置文件失败: Permission denied
```

**解决方法**:
- 检查文件权限
- 确保你有写权限
- 检查磁盘空间

---

## 最佳实践

### 1. 权限最小化

新Agent从`minimal`模板开始，根据需求逐步添加权限：

```bash
# 先应用最小权限
python agent_permission_manager.py apply new-agent minimal

# 再根据需要添加工具
python agent_permission_manager.py apply new-agent researcher web_search
```

### 2. 定期验证

定期运行验证命令，检查权限配置：

```bash
python agent_permission_manager.py validate
```

### 3. 文档记录

在`.commander/agent_permissions_config.md`中记录重要的权限变更：

```markdown
## 2026-02-27 权限更新

- researcher: 添加browser工具以支持UI自动化
- creator: 从architect模板改为独立模板
```

### 4. 版本控制

将权限配置文件纳入版本控制：

```bash
cd ~/.openclaw/workspace/.commander
git add agent_permission_templates.md
git commit -m "Add permission templates"
```

### 5. 测试环境

在测试Agent上先验证权限配置，再应用到生产环境：

```bash
# 测试Agent
python agent_permission_manager.py apply test-agent researcher

# 验证后应用到生产Agent
python agent_permission_manager.py apply prod-agent researcher
```

---

## 高级技巧

### 1. 模板继承链

利用模板继承创建层次化的权限体系：

```
minimal (基础)
  └─ critic (审核)
     └─ reviewer (只读评审，继承critic)

researcher (独立)
  └─ data-analyst (数据分析，继承researcher)

architect (独立)
  └─ creator (创作，继承architect)
     └─ content-writer (写作，继承creator)
```

### 2. 权限覆盖

使用`overrides`实现权限的灵活调整：

```json5
{
  "tools": {
    "template": "researcher",
    "overrides": {
      "allow": ["tts"],      // 添加
      "deny": ["browser"]    // 移除
    }
  }
}
```

### 3. 权限组（方案B）

利用外置配置的groups功能：

```json5
{
  "groups": {
    "read-only": ["critic", "minimal", "reviewer"],
    "full-access": ["main", "innovator"],
    "dev-team": ["architect", "creator", "researcher"]
  }
}
```

---

## 参考资料

- **权限模板定义**: `agent_permission_templates.md`
- **重构方案**: `permission_refactor_schemes.md`
- **手动权限记录**: `~/.openclaw/workspace/.commander/agent_permissions_config.md`
- **OpenClaw文档**: `/opt/homebrew/lib/node_modules/openclaw/docs/tools/subagents.md`

---

## 更新日志

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-02-27 | 初始版本 |

---

*文档版本: v1.0 | 最后更新: 2026-02-27*
