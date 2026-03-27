# Subagent路径传递标准化文档

**版本**: 1.0  
**创建时间**: 2026-03-21  
**作者**: ✍️创作者  
**适用范围**: 所有OpenClaw Subagent路径传递场景  

---

## 📋 目录

1. [问题背景](#问题背景)
2. [路径传递规则](#路径传递规则)
3. [标准模板](#标准模板)
4. [常见错误和解决方案](#常见错误和解决方案)
5. [检查清单](#检查清单)
6. [参考文档](#参考文档)

---

## 问题背景

### 为什么需要标准化？

在 TASK-20260321-001 中，发生了一个典型的Subagent路径错误问题：

```
❌ 错误路径: /Users/variya/projects/a-stock-advisor 6/
✅ 正确路径: /Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/
```

**问题根源**：
1. Subagent使用被引用agent的workspace，但路径必须正确
2. 路径传递不准确时，**Subagent无法自动纠正**（特别是只有read工具时）
3. OpenClaw不会自动映射或继承路径

**影响**：
- 任务失败，浪费时间
- Subagent无法探索文件系统验证路径
- 需要重新分配任务，降低效率

**解决方案**：
- 标准化路径传递方式
- 使用绝对的、完整的路径
- 提供可复用的模板和检查清单

---

## 路径传递规则

### 规则1：使用完整绝对路径（推荐）✅

**适用场景**：
- 传递路径给subagent的项目目录
- 跨workspace的文件访问
- 需要高可靠性的生产任务

**示例**：
```markdown
# 标准路径传递
主workspace绝对路径：/Users/variya/.openclaw/workspace/
项目路径：/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/
```

**优点**：
- ✅ 高可靠性，不依赖当前工作目录
- ✅ 清晰明确，无歧义
- ✅ 易于调试和验证

---

### 规则2：避免相对路径（Subagent场景）⚠️

**适用场景**：
- ❌ **不推荐**：传递给subagent的任务
- ✅ 可用于：同一工作目录内的文件引用

**示例**：
```markdown
# ❌ 不推荐（传递给subagent时）
项目路径：projects/a-stock-advisor 6/
# 问题：subagent的工作目录可能不同，导致路径错误

# ✅ 可用（同一workspace内部）
read(path="config.json")  # 相对于当前agent的workspace
```

**风险**：
- ⚠️ 依赖subagent的工作目录
- ⚠️ 可能因目录结构变化而失效
- ⚠️ 每个subagent的workspace可能不同

---

### 规则3：路径必须完整准确 🔑

**关键原则**：
1. **从根目录开始**（`/Users/...` 或 `~/.openclaw/...`）
2. **不要省略任何目录层级**
3. **确认路径与文件系统实际结构一致**

**示例**：
```markdown
# ✅ 正确
/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/

# ❌ 错误1：缺少中间目录
/Users/variya/projects/a-stock-advisor 6/

# ❌ 错误2：路径不存在
/Users/variya/.openclaw/workspace/missing-path/
```

---

### 规则4：验证路径有效性（如有工具）🔍

**适用场景**：
- 指挥官spawn subagent前
- Subagent有exec工具权限时

**验证方式**：
```python
# 指挥官spawn前验证
if not os.path.exists(project_path):
    raise ValueError(f"项目路径不存在: {project_path}")

# Subagent有exec工具时自验证
exec(command=f"ls {project_path}")
```

---

## 标准模板

### 模板1：Subagent任务路径传递

```markdown
你是{角色名}，负责{任务描述}。

# 路径配置（重要！）
主workspace绝对路径：/Users/variya/.openclaw/workspace/
项目路径：{project_path}

# 其他路径
- 配置文件：{project_path}/config.json
- 数据目录：{project_path}/data/
- 输出目录：/Users/variya/.openclaw/workspace/reports/

# 注意事项
- 所有路径必须使用完整绝对路径
- 不要省略任何目录层级
- 使用read工具时直接使用上述路径

# 任务目标
{task_objective}
```

**使用示例**：
```markdown
你是验证专家，负责验证项目代码质量。

# 路径配置（重要！）
主workspace绝对路径：/Users/variya/.openclaw/workspace/
项目路径：/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/

# 其他路径
- 配置文件：/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/config.json
- 数据目录：/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/data/
- 输出目录：/Users/variya/.openclaw/workspace/reports/

# 注意事项
- 所有路径必须使用完整绝对路径
- 不要省略任何目录层级
- 使用read工具时直接使用上述路径

# 任务目标
检查新模块导入、代码质量、数据文件状态，生成验证报告
```

---

### 模板2：Python代码中的路径传递

```python
# Subagent spawning函数
def spawn_subagent_with_standard_path(
    project_name: str,
    role: str,
    task_description: str
):
    """使用标准路径传递spawn subagent"""
    
    # 1. 定义标准路径
    workspace_root = "/Users/variya/.openclaw/workspace/"
    project_path = f"{workspace_root}/projects/{project_name}/"
    
    # 2. 验证路径存在（如果需要）
    import os
    if not os.path.exists(project_path):
        raise ValueError(f"项目路径不存在: {project_path}")
    
    # 3. 构建任务描述
    task_prompt = f"""
你是{role}，负责{task_description}。

# 路径配置（重要！）
主workspace绝对路径：{workspace_root}
项目路径：{project_path}

# 注意事项
- 所有路径必须使用完整绝对路径
- 不要省略任何目录层级
- 使用read工具时直接使用上述路径
"""
    
    # 4. spawn subagent
    # spawn_subagent(prompt=task_prompt, ...)
    return task_prompt

# 使用示例
task = spawn_subagent_with_standard_path(
    project_name="a-stock-advisor 6",
    role="验证专家",
    task_description="验证项目代码质量"
)
```

---

### 模板3：多路径引用模板

```markdown
你是{角色名}，负责{任务描述}。

# 标准路径配置
- 主workspace: /Users/variya/.openclaw/workspace/
- 项目路径: /Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/
- 输出路径: /Users/variya/.openclaw/workspace/reports/
- 其他项目路径: /Users/variya/.openclaw/workspace/other-project/

# 常用完整路径（直接复制使用）
项目根目录: /Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/
配置文件: /Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/config.json
数据目录: /Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/data/
版本文件: /Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/VERSION

# 任务目标
{task_objective}
```

---

## 常见错误和解决方案

### 错误1：缺少目录层级

**错误示例**：
```python
# ❌ 错误：缺少`.openclaw/workspace`前缀
project_path = "/Users/variya/projects/a-stock-advisor 6/"
```

**根本原因**：
- 记忆错误或猜测路径
- 对OpenClaw目录结构不熟悉

**解决方案**：
```python
# ✅ 正确：完整绝对路径
project_path = "/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/"

# 或使用环境变量构建
import os
workspace = os.path.expanduser("~/.openclaw/workspace/")
project_path = f"{workspace}/projects/a-stock-advisor 6/"
```

---

### 错误2：使用相对路径

**错误示例**：
```python
# ❌ 错误：使用相对路径
read(path="../projects/a-stock-advisor 6/config.json")
```

**根本原因**：
- 假设subagent和主agent在同一工作目录
- 没有考虑workspace隔离

**解决方案**：
```python
# ✅ 正确：使用绝对路径
read(path="/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/config.json")

# ✅ 或在任务开始时定义路径
project_root = "/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/"
read(path=f"{project_root}/config.json")
```

---

### 错误3：路径拼写错误

**错误示例**：
```python
# ❌ 错误：拼写错误（"advisor" 写成 "adviser"）
project_path = "/Users/variya/.openclaw/workspace/projects/a-stock-adviser 6/"
```

**根本原因**：
- 手动输入路径
- 没有验证路径有效性

**解决方案**：
```python
# ✅ 正确：验证路径
project_path = "/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/"
if not os.path.exists(project_path):
    raise ValueError(f"项目路径不存在: {project_path}")

# ✅ 或使用常量定义
A_STOCK_PATH = "/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/"
```

---

### 错误4：Subagent只有read工具无法验证路径

**错误场景**：
```
评审官（只有read工具）收到路径错误，但无法使用exec ls验证
```

**根本原因**：
- Subagent工具权限受限
- 无法探索文件系统

**解决方案**：

**方案1：指挥官在spawn前验证**
```python
# 指挥官执行
if not os.path.exists(project_path):
    print(f"项目路径不存在: {project_path}")
    # 修正路径或报错
else:
    spawn_subagent(prompt=task_prompt, ...)
```

**方案2：为subagent添加exec工具**
```json
{
  "agents": {
    "list": [
      {
        "id": "reviewer",
        "tools": {
          "allow": ["read", "write", "edit", "exec", "process"]
        }
      }
    ]
  }
}
```

**方案3：明确告知路径已验证**
```markdown
# 路径配置（已验证✅）
主workspace绝对路径：/Users/variya/.openclaw/workspace/
项目路径：/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/

# 注意：以上路径已由指挥官验证有效性，可直接使用
```

---

## 检查清单

### Spawn Subagent前检查清单 ✓

在调用spawn_subagent前，确认以下项目：

- [ ] **1. 路径是绝对路径吗？**
  - 检查路径是否以 `/` 或 `~` 开头
  - 确认路径从根目录或用户主目录开始

- [ ] **2. 路径完整准确吗？**
  - 检查是否包含所有必要的目录层级（`.openclaw/workspace/`）
  - 确认路径拼写正确
  - 确认项目名称正确

- [ ] **3. 路径在文件系统中存在吗？**
  - 使用 `os.path.exists()` 验证
  - 或使用 `ls` 命令检查
  - 如果不能验证，明确告知subagent路径未验证

- [ ] **4. Subagent工具有权限吗？**
  - 确认subagent有read权限
  - 如果需要验证路径，确认subagent有exec权限
  - 在任务描述中明确工具要求

- [ ] **5. 路径格式统一吗？**
  - 使用统一的前缀：`/Users/variya/.openclaw/workspace/`
  - 避免混合使用不同格式
  - 使用路径变量或常量

---

### 任务描述路径格式检查清单 ✓

- [ ] **1. 有明确路径配置章节吗？**
  - 标记为"路径配置（重要！）"
  - 包含主workspace和项目路径
  - 使用代码块展示完整路径

- [ ] **2. 路径易于复制使用吗？**
  - 提供常用完整路径列表
  - 使用明确标签（项目根目录、配置文件等）
  - 避免使用缩写或省略

- [ ] **3. 有路径使用注意事项吗？**
  - 提醒使用完整绝对路径
  - 提醒不要省略目录层级
  - 提供错误示例

- [ ] **4. 路径验证了吗？**
  - 如果验证过，明确标注"路径已验证✅"
  - 如果未验证，说明风险
  - 提供验证方法给subagent

---

## 参考文档

### 相关文档

1. **复盘报告**
   - 路径：`/Users/variya/.openclaw/workspace/workflow/ARCHIVE-MORNING-REVIEW-20260321.md`
   - 内容：TASK-001路径问题分析、最佳实践总结

2. **Subagent使用指南**
   - 路径：`/Users/variya/.openclaw/workspace-curator/SUBAGENT-GUIDE.md`
   - 内容：Workspace访问模式、常见场景、最佳实践

3. **Workspace机制调查报告**
   - 路径：`/Users/variya/.openclaw/workspace-curator/workspace-inheritance-report.md`
   - 内容：Subagent workspace继承机制详细分析

### 标准路径速查表

| 项目名称 | 标准绝对路径 | 备注 |
|---------|-------------|------|
| 主workspace | `/Users/variya/.openclaw/workspace/` | 根目录 |
| A股项目v6 | `/Users/variya/.openclaw/workspace/projects/a-stock-advisor 6/` | 主要业务代码 |
| 评审官workspace | `/Users/variya/.openclaw/workspace-critic/` | 审视任务 |
| 研究员workspace | `/Users/variya/.openclaw/workspace-researcher/` | 调查分析 |

---

**文档维护**：如有更新，请更新版本号和修改记录
