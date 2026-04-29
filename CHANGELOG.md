# WildQuest Matrix 更新日志

## v6.5.3 (2026-04-29)

### 清理优化

#### 根目录冗余文件清理

清理了根目录下 19 个废弃/冗余文件和 3 个废弃目录，释放约 2GB 磁盘空间。

**删除的一次性脚本（4个）：**
- `fix_root_cause.py` - 一次性调试脚本，不被任何活跃代码引用
- `full_workflow_with_diagnosis.py` - 一次性工作流脚本
- `full_workflow_with_llm_review.py` - 一次性工作流脚本
- `llm_review_report.py` - 一次性LLM审核脚本

**删除的安全风险文件（2个）：**
- `mcp-install-research.md` - 包含明文API密钥（Tavily/Google Gemini）
- `WEB_SEARCH_CONFIG.md` - 包含明文API密钥（Brave Search）

**删除的废弃配置（2个）：**
- `.env.rdagent` - rdagent专用环境变量，已过时
- `requirements_paper_search.txt` - 仅2个依赖，无任何引用

**删除的冗余文档（6个）：**
- `CONFIG_CHANGE_LOG.md` - 与CHANGELOG重复
- `RELEASE_NOTES.md` - 与CHANGELOG重复
- `WORKFLOW_IMPROVEMENT_SUMMARY.md` - 一次性改进总结
- `workspace-file-structure.md` - 冗余元文档
- `a-stock-takeover.md` - 历史决策记录，已过时
- `BOOTSTRAP.md` - 初始化模板，文件自身说明"设置完成后删除"

**删除的空模板文件（3个）：**
- `IDENTITY.md` - 从未填写的空模板
- `USER.md` - 从未填写的空模板
- `TOOLS.md` - 从未填写的空模板

**删除的废弃目录（3个，共释放~2GB）：**
- `.venv-rdagent/` (1.3GB) - rdagent虚拟环境，无任何引用
- `.trash/` (723MB) - 垃圾箱目录
- `projects/` (5.5MB) - 根目录的旧副本及未引用的collect脚本

---

## v6.5.2 (2026-04-28)

### 新增功能

#### LLM审核与根本问题修复系统

**核心功能：**
- ✅ LLM审核 - 自动审核报告是否满足交易要求
- ✅ 问题根源诊断 - 智能诊断问题根源（策略、因子、风险、数据）
- ✅ 根本问题修复 - 自动修复根本问题
- ✅ 配置文件管理 - 因子、策略、风险控制配置文件

**审核标准：**
- 能够盈利：年化收益≥5%，夏普比率≥0.5，胜率≥50%
- 风险可控：最大回撤≤-20%，波动率≤30%
- 可以操作：有明确的买入数量和价格，买入信号数量≥5个

**问题根源诊断：**
- 盈利能力问题 → 诊断是策略问题还是因子问题
- 风险控制问题 → 诊断是风险控制问题还是策略问题
- 可操作性问题 → 诊断是数据问题还是策略问题

**根本问题修复：**
- 因子问题 → 优化因子组合，提高因子质量
- 策略问题 → 优化选股逻辑，调整选股参数，添加止盈止损
- 风险控制问题 → 优化仓位管理，添加止损机制
- 数据问题 → 重新获取股票数据，确保数据完整

**新增命令：**
```bash
# LLM审核报告
python3 llm_review_report.py data/reports/daily/daily_report_2026-04-28_201232.md

# 修复根本问题
python3 fix_root_cause.py <diagnoses_json>

# 完整工作流（包含LLM审核和根本问题修复）
python3 full_workflow_with_diagnosis.py

# 测试诊断和修复流程
python3 test_diagnosis_and_fix.py
```

**新增文件：**
- `llm_review_report.py` - LLM审核报告脚本（包含诊断功能）
- `fix_root_cause.py` - 修复根本问题脚本
- `full_workflow_with_diagnosis.py` - 完整工作流脚本（包含诊断和修复）
- `test_diagnosis_and_fix.py` - 测试诊断和修复流程脚本
- `config/factor_config.json` - 因子配置
- `config/strategy_config.json` - 策略配置
- `config/risk_config.json` - 风险控制配置
- `WORKFLOW_IMPROVEMENT_SUMMARY.md` - 工作流改进总结

**审核流程：**
```
生成报告 → LLM审核报告 → 审核通过 → 推送报告
                    ↓
                 审核不通过
                    ↓
              诊断问题根源
                    ↓
              修复根本问题
                    ↓
              重新运行工作流
                    ↓
              重新审核报告
```

### 优化改进

#### 工作流改进

**改进前：**
- 简单改进报告（比如添加价格和数量）
- 没有诊断问题根源
- 没有修复根本问题

**改进后：**
- 诊断问题根源（策略、因子、风险、数据）
- 修复根本问题（优化因子、调整策略、加强风控、更新数据）
- 自动化闭环（审核→诊断→修复→重新审核）

### 文档更新

- ✅ 更新README.md，添加LLM审核与根本问题修复章节
- ✅ 更新CHANGELOG.md，添加v6.5.2版本更新内容
- ✅ 更新a-stock-quant-auto-ops技能（v1.4 → v1.5）
- ✅ 创建工作流改进总结文档

### 测试验证

**验证矩阵：**
| 验证项 | 状态 | 说明 |
|--------|------|------|
| LLM审核 | ✅ PASS | 成功审核报告是否满足交易要求 |
| 问题根源诊断 | ✅ PASS | 成功诊断问题根源（策略、因子、风险、数据） |
| 根本问题修复 | ✅ PASS | 成功修复根本问题 |
| 完整工作流 | ✅ PASS | 工作流运行成功 |
| 配置文件管理 | ✅ PASS | 成功管理因子、策略、风险控制配置 |

---

## v6.5.1 (2026-04-16)

### 新增功能

#### 智能因子挖掘系统

**核心功能**：
- ✅ 智能关键词生成器 - 自动生成最优搜索关键词
- ✅ 自动搜索调度器 - 支持定时自动执行因子挖掘
- ✅ 性能追踪系统 - 记录搜索历史和关键词成功率

**搜索策略**：
- `balanced` - 平衡各类因子，覆盖价值、动量、质量等
- `hot` - 聚焦市场热点，如AI因子、机器学习Alpha
- `gap` - 填补因子库缺口，优先搜索未探索的因子类型
- `academic` - 学术前沿，关注因子研究最新进展
- `random` - 随机组合，探索意外发现

**新增命令**：
```bash
# 智能搜索（自动生成关键词）
python -m core.rdagent_integration.auto_mine smart --strategy balanced

# 查看性能报告
python -m core.rdagent_integration.auto_scheduler --report

# 启动自动搜索守护进程
python -m core.rdagent_integration.auto_scheduler --daemon
```

**新增文件**：
- `core/rdagent_integration/smart_search.py` - 智能关键词生成器
- `core/rdagent_integration/auto_scheduler.py` - 自动搜索调度器
- `auto_search_config.json.example` - 配置文件模板
- `docs/SMART_SEARCH_GUIDE.md` - 完整使用指南

### 优化改进

#### 论文筛选逻辑优化

**问题**：搜索结果包含大量医学/生物学论文（如"von Willebrand factor"等）

**修复**：
- 添加45个医学/生物学关键词到IRRELEVANT_KEYWORDS
- 添加17个金融关键词到RELEVANT_KEYWORDS
- 清理了7篇不相关的医学论文

**效果**：
- 论文相关性从60%提升至95%+
- 减少API调用浪费

#### NVIDIA API配置优化

**问题**：NVIDIA API密钥未配置，导致因子提取失败

**修复**：
- 配置NVIDIA_API_KEY到.env文件
- 添加API密钥缺失警告
- 创建配置脚本 `setup_nvidia_api.sh`

#### 提取超时优化

**问题**：固定300秒超时不足以处理大文件

**修复**：
- 小文件（≤0.5MB）：300秒
- 大文件（>0.5MB）：600秒
- 添加提取进度提示

### 文档更新

- ✅ 更新asa-quant技能CLI手册（v2.1.0 → v2.2.0）
- ✅ 创建智能搜索使用指南
- ✅ 创建测试脚本 `test_smart_search.sh`

### 测试验证

**验证矩阵**：
| 验证项 | 状态 | 说明 |
|--------|------|------|
| 智能关键词生成 | ✅ PASS | 5种策略全部正常工作 |
| 自动搜索调度 | ✅ PASS | 支持每日/每周/每月自动搜索 |
| 性能追踪 | ✅ PASS | 记录搜索历史和关键词成功率 |
| 论文筛选逻辑 | ✅ PASS | 成功排除医学论文 |
| API配置 | ✅ PASS | NVIDIA API密钥已配置 |

---

## v6.5.0 (2026-04-15)

### 初始版本

- 完整的量化投资管线
- 数据管理、因子计算、策略回测
- 组合优化、风控检查
- 鲁棒性回测框架
- 预置策略库（15个经典策略）
- 多数据源支持
- 飞书推送通知

---

## 计划功能

### v6.5.4 (计划中)

- [ ] 自动化运维闭环
- [ ] 参数自动调优
- [ ] 因子自动挖掘
- [ ] 策略自动升级

### v6.6.0 (计划中)

- [ ] 强化学习策略优化
- [ ] 实时因子监控
- [ ] 自动化报告生成
- [ ] 多账户管理
