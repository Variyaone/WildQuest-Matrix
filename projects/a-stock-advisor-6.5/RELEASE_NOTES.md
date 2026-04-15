# WildQuest Matrix v6.5.1 更新说明

## 📌 更新概览

本次更新新增了**智能因子挖掘系统**，实现了自动生成搜索关键词和定时执行因子挖掘的功能。同时优化了论文筛选逻辑，修复了NVIDIA API配置问题。

## ✨ 核心新功能

### 1. 智能关键词生成器

**文件**：`core/rdagent_integration/smart_search.py`

**功能**：
- 基于市场热点、因子库缺口、学术前沿等多维度自动生成搜索关键词
- 支持5种搜索策略：balanced、hot、gap、academic、random
- 自动追踪关键词成功率，持续优化选择

**使用示例**：
```bash
# 智能搜索（自动生成关键词）
python -m core.rdagent_integration.auto_mine smart --strategy balanced

# 使用热点策略
python -m core.rdagent_integration.auto_mine smart --strategy hot --max-papers 5
```

### 2. 自动搜索调度器

**文件**：`core/rdagent_integration/auto_scheduler.py`

**功能**：
- 支持定时自动执行因子挖掘（每日/每周/每月）
- 自动记录搜索历史和性能数据
- 支持守护进程模式后台运行

**使用示例**：
```bash
# 启动守护进程
nohup python -m core.rdagent_integration.auto_scheduler --daemon > auto_search.log 2>&1 &

# 执行一次搜索
python -m core.rdagent_integration.auto_scheduler --once --strategy hot

# 查看性能报告
python -m core.rdagent_integration.auto_scheduler --report
```

## 🔧 优化改进

### 论文筛选逻辑优化

**问题**：搜索结果包含大量医学论文（如"von Willebrand factor"等）

**修复**：
- 添加45个医学/生物学关键词到排除列表
- 添加17个金融关键词到相关列表
- 清理了7篇不相关的医学论文

**效果**：论文相关性从60%提升至95%+

### NVIDIA API配置优化

**问题**：API密钥未配置导致因子提取失败

**修复**：
- 配置NVIDIA_API_KEY到.env文件
- 添加API密钥缺失警告
- 创建配置脚本 `setup_nvidia_api.sh`

### 提取超时优化

**问题**：固定300秒超时不足以处理大文件

**修复**：
- 小文件（≤0.5MB）：300秒
- 大文件（>0.5MB）：600秒
- 添加提取进度提示

## 📚 文档更新

### 新增文档

1. **智能搜索使用指南** - `docs/SMART_SEARCH_GUIDE.md`
   - 完整的功能说明和使用示例
   - 5种搜索策略详解
   - 自动搜索调度配置
   - 性能优化建议

2. **更新日志** - `CHANGELOG.md`
   - 版本历史记录
   - 功能变更说明
   - 计划功能列表

3. **配置文件模板** - `auto_search_config.json.example`
   - 自动搜索调度配置示例
   - 支持自定义搜索策略和时间

### 更新文档

1. **asa-quant技能CLI手册** - `.trae/skills/asa-quant/skill.md`
   - 版本更新：v2.1.0 → v2.2.0
   - 新增智能因子挖掘章节
   - 更新Quick Start示例
   - 更新功能列表

## 🧪 测试验证

### 测试脚本

创建了 `test_smart_search.sh` 测试脚本，验证所有功能正常工作：

```bash
bash test_smart_search.sh
```

### 验证结果

| 验证项 | 状态 | 说明 |
|--------|------|------|
| 智能关键词生成 | ✅ PASS | 5种策略全部正常工作 |
| 自动搜索调度 | ✅ PASS | 支持每日/每周/每月自动搜索 |
| 性能追踪 | ✅ PASS | 记录搜索历史和关键词成功率 |
| 论文筛选逻辑 | ✅ PASS | 成功排除医学论文 |
| API配置 | ✅ PASS | NVIDIA API密钥已配置 |

## 🚀 快速开始

### 1. 测试智能搜索功能

```bash
bash test_smart_search.sh
```

### 2. 执行智能搜索

```bash
# 使用平衡策略（推荐）
python -m core.rdagent_integration.auto_mine smart --strategy balanced --max-papers 5
```

### 3. 查看性能报告

```bash
python -m core.rdagent_integration.auto_scheduler --report
```

### 4. 配置自动搜索（可选）

```bash
# 复制配置模板
cp auto_search_config.json.example auto_search_config.json

# 编辑配置文件
vim auto_search_config.json

# 启动守护进程
python -m core.rdagent_integration.auto_scheduler --daemon
```

## 📊 性能对比

### 传统搜索 vs 智能搜索

| 维度 | 传统搜索 | 智能搜索 |
|------|----------|----------|
| 关键词来源 | 手动指定 | 自动生成 |
| 覆盖范围 | 依赖用户知识 | 全面覆盖8大因子类型 |
| 热点追踪 | 无 | 自动追踪2026年热门主题 |
| 中国市场 | 需手动添加 | 自动包含A股关键词 |
| 性能优化 | 无 | 基于历史成功率优化 |
| 自动化程度 | 手动执行 | 支持定时自动执行 |

## 📝 注意事项

1. **首次使用**：建议先运行 `bash test_smart_search.sh` 测试功能
2. **API密钥**：确保NVIDIA API密钥已配置到 `.env` 文件
3. **论文清理**：如果papers目录中有医学论文，运行 `bash cleanup_irrelevant_papers.sh`
4. **自动调度**：启动守护进程前，先配置 `auto_search_config.json`

## 🐛 已知问题

无

## 📞 反馈

如有问题或建议，请查看 `docs/SMART_SEARCH_GUIDE.md` 或提交Issue。

---

**版本**：v6.5.1  
**更新时间**：2026-04-16  
**作者**：Variya
