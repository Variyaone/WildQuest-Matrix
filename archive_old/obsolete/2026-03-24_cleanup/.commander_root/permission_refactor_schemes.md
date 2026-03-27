# 🔧 Agent权限配置重构方案

## 背景

当前Agent权限配置存在以下问题：
1. 手动逐个编辑`openclaw.json`
2. 工具列表重复复制粘贴
3. 无模板化、无继承机制
4. 修改权限需要逐个调整Agent

本文档提供两种重构方案供选择。

---

## 方案A：模板引用（推荐）

### 设计思路

在`openclaw.json`中使用模板引用，运行时动态解析模板。

### 实现方式

#### 1. 配置文件结构

```json5
{
  "agents": {
    "list": [
      {
        "id": "researcher",
        "name": "研究员",
        "tools": {
          "template": "researcher"
        }
      },
      {
        "id": "creator",
        "name": "创作者",
        "tools": {
          "template": "creator",
          "allow": ["canvas"]  // 可选：额外添加工具
        }
      }
    ]
  }
}
```

#### 2. 模板存储位置

**选项1：内嵌在openclaw.json**
```json5
{
  "tools": {
    "templates": {
      "researcher": {
        "allow": ["read", "write", "edit", ...]
      }
    }
  }
}
```

**选项2：外置模板文件（推荐）**
```
~/.openclaw/templates/permissions.json
```

#### 3. 运行时解析机制

OpenClaw在加载配置时：
1. 读取Agent的`tools.template`字段
2. 从模板存储加载模板定义
3. 解析模板继承关系（`inherits`字段）
4. 合并`allow` / `deny` / `profile`
5. 替换Agent的`tools`字段为解析后的完整工具列表

### 优点

✅ **配置简洁**: 只需指定模板名
✅ **单文件管理**: 所有配置仍在`openclaw.json`中（或外置模板文件）
✅ **向后兼容**: 旧配置不使用`template`字段仍然有效
✅ **易于迁移**: 使用脚本自动转换现有配置

### 缺点

❌ **需要运行时支持**: OpenClaw需要实现模板解析逻辑
❌ **模板修改需重启**: 修改模板后需要重新加载配置
❌ **调试困难**: 运行时解析，配置错误不直观

### 实施步骤

1. **阶段1：创建模板定义**
   ```bash
   # 创建模板文件
   mkdir -p ~/.openclaw/templates
   cp ~/.openclaw/workspace/.commander/permission_templates.json ~/.openclaw/templates/
   ```

2. **阶段2：迁移配置**
   ```bash
   # 使用脚本迁移
   cd ~/.openclaw/workspace/.commander
   python agent_permission_manager.py migrate researcher researcher --apply
   python agent_permission_manager.py migrate architect architect --apply
   # ... 对所有Agent
   ```

3. **阶段3：实现运行时解析**
   - 修改OpenClaw配置加载逻辑
   - 添加模板解析模块
   - 添加配置验证

4. **阶段4：测试验证**
   - 验证所有Agent权限正确
   - 测试模板继承功能
   - 验证额外工具添加/移除

---

## 方案B：外置权限配置

### 设计思路

将权限配置独立到外部JSON文件，`openclaw.json`只引用。

### 实现方式

#### 1. 权限配置文件

`~/.openclaw/agent_permissions.json`:
```json5
{
  "version": "1.0",
  "meta": {
    "description": "Agent工具权限配置",
    "lastUpdated": "2026-02-27T04:00:00Z"
  },
  "templates": {
    "researcher": {
      "name": "研究员",
      "inherits": null,
      "tools": {
        "allow": [
          "read", "write", "edit", "exec", "process",
          "web_search", "web_fetch", "browser", "canvas",
          "memory_search", "memory_get"
        ]
      }
    },
    "creator": {
      "name": "创作者",
      "inherits": "architect",
      "tools": {
        "allow": [
          "read", "write", "edit", "exec",
          "web_search", "web_fetch"
        ]
      }
    }
  },
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
  },
  "groups": {
    "read-only": ["critic", "minimal"],
    "full-access": ["main", "innovator"]
  }
}
```

#### 2. openclaw.json引用

```json5
{
  "agents": {
    "list": [
      {
        "id": "researcher",
        // 其他配置...
        "tools": {
          "_ref": ".permissionTemplates.researcher"
        }
      }
    ]
  },
  "permissionTemplates": "./agent_permissions.json"
}
```

#### 3. 运行时加载

OpenClaw启动时：
1. 读取`tools.permissionTemplates`路径
2. 加载外置权限配置文件
3. 解析模板和Agent映射
4. 合并overrides到Agent配置

### 优点

✅ **完全分离**: 权限配置独立于主配置
✅ **易于管理**: 专门文件管理权限，职责清晰
✅ **热重载**: 支持修改权限配置后重新加载
✅ **扩展性强**: 可以添加groups、rules等高级功能
✅ **版本控制**: 权限变更可独立追踪

### 缺点

❌ **多文件管理**: 需要维护两个配置文件
❌ **引用复杂**: 需要实现引用解析逻辑
❌ **同步问题**: AgentID修改时需要同步两个文件

### 实施步骤

1. **阶段1：创建权限配置文件**
   ```bash
   # 导出当前权限配置
   python agent_permission_manager.py export
   ```

2. **阶段2：修改openclaw.json**
   - 添加`permissionTemplates`引用
   - 移除Agent的硬编码`tools`配置
   - 使用`_ref`字段引用模板

3. **阶段3：实现加载逻辑**
   - 实现权限配置文件加载器
   - 实现引用解析和合并
   - 添加热重载支持

4. **阶段4：高级功能（可选）**
   - 添加权限组（groups）
   - 添加动态规则（rules）
   - 添加权限继承矩阵

---

## 方案对比

| 维度 | 方案A（模板引用） | 方案B（外置配置） |
|------|------------------|------------------|
| **配置复杂度** | ⭐⭐ 简单 | ⭐⭐⭐ 中等 |
| **运行时支持** | 需要实现解析 | 需要实现加载器 |
| **维护性** | ⭐⭐⭐ 单文件 | ⭐⭐⭐⭐ 职责分离 |
| **扩展性** | ⭐⭐ 受限 | ⭐⭐⭐⭐ 灵活 |
| **向后兼容** | ✅ 完全兼容 | ⚠️ 需要迁移 |
| **热重载** | ❌ 需要重启 | ✅ 支持 |
| **调试难度** | ⭐⭐ 中等 | ⭐ 容易 |
| **适用场景** | 快速迁移 | 长期维护 |

---

## 推荐选择

### 短期（快速见效）→ 方案A

如果你的优先级是：
- 快速解决当前配置混乱问题
- 不想大幅改动OpenClaw核心代码
- 需要快速迁移现有Agent

**选择方案A**

### 长期（架构优化）→ 方案B

如果你希望建立：
- 完全独立的权限管理系统
- 支持热重载和动态修改
- 更灵活的权限控制（组、规则等）

**选择方案B**

---

## 混合方案（最佳实践）

结合两者优点：

1. **第一阶段**：使用方案A快速迁移
   - 在`openclaw.json`中使用`template`引用
   - 内嵌模板定义（`tools.templates`）

2. **第二阶段**：逐步演进到方案B
   - 将模板定义移到外置文件
   - 实现`permissionTemplates`引用
   - 添加热重载支持

3. **第三阶段**：高级功能
   - 添加权限组
   - 添加规则引擎
   - 添加权限继承可视化

---

## 迁移脚本使用

无论选择哪个方案，都可以使用提供的脚本：

```bash
# 查看当前配置
python agent_permission_manager.py list

# 应用模板到Agent
python agent_permission_manager.py apply researcher researcher

# 验证权限配置
python agent_permission_manager.py validate

# 比较Agent与模板的差异
python agent_permission_manager.py compare researcher researcher

# 方案A：迁移到模板引用
python agent_permission_manager.py migrate researcher researcher --apply

# 方案B：导出权限配置
python agent_permission_manager.py export

# 方案B：导入权限配置
python agent_permission_manager.py import agent_permissions.json --apply
```

---

*文档版本: v1.0 | 更新日期: 2026-02-27*
