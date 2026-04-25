# Git提交信息规范

**版本**: v1.0
**生效日期**: 2026-03-21
**适用范围**: A股量化系统项目（a-stock-adaptor 6）及所有子项目

---

## 📋 目录

- [规范目的](#规范目的)
- [基础格式](#基础格式)
- [Type类型定义](#type类型定义)
- [Subject格式规范](#subject格式规范)
- [Body格式规范](#body格式规范)
- [Footer格式规范](#footer格式规范)
- [示例模板](#示例模板)
- [提交前检查清单](#提交前检查清单)
- [常见错误和解决方案](#常见错误和解决方案)
- [工具配置建议](#工具配置建议)

---

## 规范目的

### 为什么需要规范？

1. **提高可读性**：统一的格式让Git历史更清晰，便于快速理解每次提交的作用
2. **提升追溯性**：关联Task ID，便于从代码追溯到具体任务或问题
3. **简化协作**：团队成员遵循统一规范，减少沟通成本
4. **自动化友好**：便于自动生成CHANGELOG、版本发布说明等文档

### 当前问题

- 约55%提交有类型前缀，45%缺失
- 分隔符混用（英文`:` vs 中文`：`）
- 缺少Task ID关联，难以追溯
- Body质量参差不齐

---

## 基础格式

### 标准格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 简化格式（可选）

对于简单修改，可以简化为：

```
<type>: <subject>
```

**示例**：
```
chore: 更新VERSION至6.4.1
```

### 完整格式（推荐）

对于重要修改，应使用完整格式：

```
feat(strategy): 添加因子有效性筛选器

核心更新:
- 新增FactorEffectivenessFilter类，基于IC/IR评估因子质量
- 实现A/B/C/D四级质量分级
- 支持历史回测数据验证

测试通过: test_factor_quality.py

关联任务: TASK-20260321-001
```

---

## Type类型定义

### Type类型列表

| Type | 说明 | 示例 |
|------|------|------|
| **feat** | 新功能 | 添加因子筛选模块 |
| **fix** | Bug修复 | 修复交易记录重复问题 |
| **docs** | 文档更新 | 更新用户手册 |
| **style** | 代码格式调整（不影响运行） | 统一缩进为2空格 |
| **refactor** | 代码重构（既不是新功能也不是修复） | 重构因子加载逻辑 |
| **perf** | 性能优化 | IC计算向量化优化 |
| **test** | 测试代码 | 添加单元测试 |
| **chore** | 构建/工具链/配置更新 | 更新依赖包版本 |

### Type使用规则

1. **单一类型**：每个提交只使用一个Type
2. **类型准确**：不要用`feat`代替`fix`，也不要用`refactor`代替`fix`
3. **保持简单**：不要创造新的Type类型

---

## Subject格式规范

### Subject要求

Subject（主题）是提交信息的第一行，必须满足以下要求：

1. **长度限制**：不超过50字符（含type和scope）
2. **祈使句**：使用祈使句（如"change"而非"changed"或"changes"）
3. **首字母小写**：除非是专有名词或缩写
4. **句尾不加标点**：不要以句号结尾
5. **简短明确**：准确描述改动内容

### Subject示例

✅ **正确**：
```
feat: 添加因子有效性筛选器
fix: 修复交易记录重复问题
docs: 更新用户手册
```

❌ **错误**：
```
feat: 添加了因子有效性筛选器  // ❌ "了"不是祈使句
Fix: 修复交易记录重复问题      // ❌ 首字母大写
feat: 添加因子有效性筛选器。   // ❌ 句尾有标点
feat: 添加一个新的功能         // ❌ 不够明确
```

### Scope（作用域）的使用

Scope用于说明改动影响的模块或区域，使用圆括号包裹：

```
<type>(<scope>): <subject>
```

**常用Scope**：

| Scope | 说明 |
|-------|------|
| strategy | 策略模块 |
| factor | 因子模块 |
| signal | 信号模块 |
| risk | 风险管理 |
| backtest | 回测引擎 |
| monitor | 监控报告 |
| config | 配置文件 |
| docs | 文档 |

**示例**：
```
feat(strategy): 添加因子有效性筛选器
fix(signal): 修复信号质量判断逻辑
docs(readme): 更新安装说明
```

---

## Body格式规范

### Body用途

Body部分（可选）用于详细描述改动的具体内容、原因和影响。

### Body格式要求

1. **分隔符**：Subject和Body之间空一行
2. **多行布局**：每行不超过72字符
3. **列表化**：使用列表条目说明多个改动点
4. **结构清晰**：可使用"核心更新"、"新增功能"、"改进项"等小标题

### Body内容建议

Body应包含以下内容（按重要性排序）：

1. **改动原因**：为什么做这个改动
2. **改动内容**：具体修改了什么
3. **影响范围**：影响了哪些模块或功能
4. **测试情况**：是否通过测试，如何测试
5. **注意事项**：后续需要注意的事项

### Body示例

**示例1：功能新增**
```
feat(strategy): 添加因子有效性筛选器

核心更新:
- 新增FactorEffectivenessFilter类，基于IC/IR评估因子质量
- 实现A/B/C/D四级质量分级
  - A级: IC>0.08, IR>1.5
  - B级: IC>0.05, IR>1.0
  - C级: IC>0.03, IR>0.7
  - D级: IC<0.03 或 IR<0.7
- 支持历史回测数据验证

测试通过: test_factor_quality.py

关联任务: TASK-20260321-001
```

**示例2：Bug修复**
```
fix(signal): 修复信号质量判断中的除零错误

问题描述:
在计算信号质量时，如果历史信号数量为0会导致除零错误
退出程序。

修复方案:
添加空值检查，当历史信号数量为0时返回默认质量评分0

影响范围:
- core/signals/signal_quality_filter.py
- 不会影响现有计算结果（已验证5次回测）

关联任务: TASK-20260321-002
```

**示例3：代码重构**
```
refactor(factor): 简化因子加载流程

重构内容:
- 移除冗余的try-except块（共5处）
- 统一异常处理机制
- 提取公共函数load_factor_file()

性能改进:
- 因子加载速度提升约15%
- 测试数据: 500个因子，加载时间从8.2s降至7.0s

测试验证:
- 所有现有单元测试通过
- 手动验证50个因子加载正常

关联任务: TASK-20260321-003
```

---

## Footer格式规范

### Footer用途

Footer部分（可选）用于关联 Issue、Task ID 或提供附加信息。

### Footer格式

1. **分隔符**：Body和Footer之间空一行
2. **Issue关联**：使用 `Closes`, `Fixes`, `Resolves` 等关键词
3. **Task关联**：使用 `关联任务:` 前缀
4. **其他信息**：如 `测试通过:`、`待后续优化:` 等

### Footer示例

**示例1：关联Issue**
```
feat: 添加用户认证功能

- 实现JWT token认证
- 支持用户注册和登录

Closes #123, #125
```

**示例2：关联Task**
```
fix: 修复交易记录重复问题

删除2026-03-20 00:13和00:14两笔相同交易

关联任务: TASK-20260321-001
```

**示例3：多种信息**
```
perf: IC计算向量化优化

使用numpy数组操作替代循环，提升计算速度

测试通过: benchmark_test.py
性能提升: 约40%（测试10000次IC计算）
关联任务: TASK-20260321-004
```

---

## 示例模板

### feat（新功能）

**示例1：复杂功能**
```
feat(strategy): 添加因子有效性筛选器

核心更新:
- 新增FactorEffectivenessFilter类，基于IC/IR评估因子质量
- 实现A/B/C/D四级质量分级
  - A级: IC>0.08, IR>1.5
  - B级: IC>0.05, IR>1.0
  - C级: IC>0.03, IR>0.7
  - D级: IC<0.03 或 IR<0.7
- 支持历史回测数据验证

新增文件:
- core/factor/validation/factor_effectiveness_filter.py
- test_factor_effectiveness_filter.py

测试通过: test_factor_effectiveness_filter.py

关联任务: TASK-20260321-001
```

**示例2：简单功能**
```
feat(config): 支持多配置文件合并

新增--merge-config选项，支持同时加载多个配置文件并合并

关联任务: TASK-20260321-002
```

### fix（Bug修复）

**示例1：复杂修复**
```
fix(signal): 修复信号质量判断中的除零错误

问题描述:
在计算信号质量时，如果历史信号数量为0会导致除零错误
退出程序。此问题在市场无交易数据时出现。

修复方案:
1. 添加空值检查，当历史信号数量为0时返回默认质量评分0
2. 添加日志警告，便于排查问题
3. 更新单元测试，覆盖边界情况

影响范围:
- core/signals/signal_quality_filter.py
- 不会影响现有计算结果（已验证5次回测）

测试验证:
- 新增测试用例：test_empty_signal_history()
- 所有现有单元测试通过

关联任务: TASK-20260321-003
```

**示例2：简单修复**
```
fix(docs): 修正安装命令中的拼写错误

将 "pip instal -r requirements.txt" 修正为 "pip install -r requirements.txt"

关联任务: TASK-20260321-004
```

### docs（文档更新）

```
docs: 添加快速参考章节

在README.md中添加关键路径速查表，包括：
- 配置文件路径
- 数据目录结构
- 常用命令示例

提升文档可读性，新用户上手时间从30分钟降至10分钟

关联任务: TASK-20260321-005
```

### refactor（代码重构）

```
refactor(factor): 简化因子加载流程

重构内容:
- 移除冗余的try-except块（共5处）
- 统一异常处理机制
- 提取公共函数load_factor_file()

性能改进:
- 因子加载速度提升约15%
- 测试数据: 500个因子，加载时间从8.2s降至7.0s

代码质量:
- Cyclomatic复杂度从8降至5
- 代码行数减少约40行

测试验证:
- 所有现有单元测试通过
- 手动验证50个因子加载正常

关联任务: TASK-20260321-006
```

### perf（性能优化）

```
perf(backtest): IC计算向量化优化

使用numpy数组操作替代循环，提升计算速度

性能提升:
- 约40%（测试10000次IC计算）
- 耗时从12.5s降至7.5s
- 内存占用增加约15%（可接受范围）

测试验证:
- 新增性能基准测试：benchmark_ic_calculation.py
- 确保计算结果与原方法完全一致

关联任务: TASK-20260321-007
```

### test（测试代码）

```
test(strategy): 添加因子筛选器单元测试

新增测试文件：
- test_factor_effectiveness_filter.py

测试覆盖：
- 正常情况测试（A/B/C/D四级因子）
- 边界情况测试（IC/IR为0、负值）
- 异常情况测试（空数据、None值）

测试通过率: 100% (20/20)

关联任务: TASK-20260321-008
```

### style（代码格式）

```
style: 统一缩进为2空格

使用autopep8自动格式化代码，统一缩进标准

影响范围:
- 整个项目约120个Python文件
- 不涉及逻辑改动

关联任务: TASK-20260321-009
```

### chore（工具链/配置）

```
chore: 更新依赖包至最新版本

更新内容:
- numpy: 1.24.0 → 2.0.0
- pandas: 2.0.0 → 2.2.0
- scikit-learn: 1.2.0 → 1.4.0

测试验证:
- 所有单元测试通过
- 手动验证回测功能正常

关联任务: TASK-20260321-010
```

---

## 提交前检查清单

### 快速检查（30秒）

在执行 `git commit` 之前，快速检查以下项目：

- [ ] **Type类型是否正确**：选择了最合适的type（feat/fix/docs/refactor/perf/test/style/chore）
- [ ] **Subject是否简短明确**：不超过50字符，使用祈使句
- [ ] **Subject是否清晰**：能准确表达改动的核心内容
- [ ] **Subject首字母小写**：除非是专有名词或缩写
- [ ] **Subject句尾无标点**：不要以句号结尾

### 详细检查（1分钟）

对于重要的提交，请额外检查：

- [ ] **Body是否详细**：说明了改动内容、原因和影响
- [ ] **Body结构清晰**：使用了列表化或小标题
- [ ] **是否关联Task ID**：便于追溯（格式：`关联任务: TASK-YYYYMMDD-XXX`）
- [ ] **测试情况是否说明**：是否通过测试，如何测试
- [ ] **语言一致**：遵循项目语言策略（本项目使用中文）
- [ ] **拼写检查**：提交信息无拼写错误

### 检查清单使用建议

**简单的修改**（如typo修复、小调整）：
- 只需快速检查（30秒）
- 使用简化格式（无Body）

**重要的修改**（如功能新增、Bug修复、重构）：
- 必须详细检查（1分钟）
- 使用完整格式（包含Body和Footer）

---

## 常见错误和解决方案

### 错误1：缺少Type类型

❌ **错误**：
```
添加因子有效性筛选器
```

✅ **正确**：
```
feat: 添加因子有效性筛选器
```

**解决方案**：选择最合适的type（feat/fix/docs/refactor/perf/test/style/chore）

---

### 错误2：Subject过长

❌ **错误**：
```
feat: 添加了一个新的因子有效性筛选功能，可以基于IC和IR指标评估因子质量
```

✅ **正确**：
```
feat: 添加因子有效性筛选器
```

或使用完整格式：
```
feat: 添加因子有效性筛选器

核心更新:
- 新增FactorEffectivenessFilter类，基于IC/IR评估因子质量
- 支持历史回测数据验证
```

**解决方案**：Subject保持在50字符内，详细信息放在Body

---

### 错误3：Subject使用陈述句或过去式

❌ **错误**：
```
feat: 添加了因子有效性筛选器
feat: Added factor effectiveness filter
```

✅ **正确**：
```
feat: 添加因子有效性筛选器
```

**解决方案**：使用祈使句（change而不是changed）

---

### 错误4：Subject首字母大写

❌ **错误**：
```
Feat: 添加因子有效性筛选器
Fix: 修复交易记录重复问题
```

✅ **正确**：
```
feat: 添加因子有效性筛选器
fix: 修复交易记录重复问题
```

**解决方案**：Type使用小写，除非是大专有名词（如API、JSON）

---

### 错误5：Subject句尾有标点

❌ **错误**：
```
feat: 添加因子有效性筛选器。
feat: 添加因子有效性筛选器，
```

✅ **正确**：
```
feat: 添加因子有效性筛选器
```

**解决方案**：Subject不要以任何标点结尾

---

### 错误6：分隔符混用

❌ **错误**：
```
feat：添加因子有效性筛选器   // 中文冒号
fix：修复交易记录重复问题   // 中文冒号
```

✅ **正确**：
```
feat: 添加因子有效性筛选器   // 英文冒号
fix: 修复交易记录重复问题   // 英文冒号
```

**解决方案**：统一使用英文冒号`:`

---

### 错误7：缺少Task ID关联

❌ **错误**：
```
fix: 修复交易记录重复问题

删除2026-03-20 00:13和00:14两笔相同交易
```

✅ **正确**：
```
fix: 修复交易记录重复问题

删除2026-03-20 00:13和00:14两笔相同交易

关联任务: TASK-20260321-001
```

**解决方案**：在Footer中添加关联任务

---

### 错误8：Body不清晰

❌ **错误**：
```
feat: 添加因子有效性筛选器

更新了一些代码，增加了新功能，修复了一些bug
```

✅ **正确**：
```
feat: 添加因子有效性筛选器

核心更新:
- 新增FactorEffectivenessFilter类，基于IC/IR评估因子质量
- 实现A/B/C/D四级质量分级
- 支持历史回测数据验证
```

**解决方案**：使用列表和小标题，详细说明改动内容

---

### 错误9：中英文混用

❌ **错误**：
```
feat: 添加factor effectiveness filter

Implemented FactorEffectivenessFilter class
```

✅ **正确**：
```
feat: 添加因子有效性筛选器

核心更新:
- 新增FactorEffectivenessFilter类，基于IC/IR评估因子质量
```

**解决方案**：本项目提交信息使用中文，保持一致性

---

### 错误10：一个提交包含多个不相关的修改

❌ **错误**：
```
fix: 修复两个问题

1. 修复交易记录重复问题
2. 修复信号质量判断错误
```

✅ **正确**：

提交1：
```
fix: 修复交易记录重复问题

删除2026-03-20 00:13和00:14两笔相同交易

关联任务: TASK-20260321-001
```

提交2：
```
fix: 修复信号质量判断中的除零错误

添加空值检查，当历史信号数量为0时返回默认质量评分0

关联任务: TASK-20260321-002
```

**解决方案**：将不相关的修改拆分为多个提交

---

## 工具配置建议

### Git Hook配置（推荐）

使用commitlint自动检查提交信息格式：

**安装commitlint**：
```bash
npm install -g @commitlint/cli @commitlint/config-conventional
```

**创建配置文件** `.commitlintrc.js`：
```javascript
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'docs', 'style', 'refactor', 'perf', 'test', 'chore']
    ],
    'subject-case': [0], // 允许使用中文
    'subject-max-length': [2, 'always', 50]
  }
};
```

**配置Git钩子**：
```bash
echo "npx --no -- commitlint --edit \$1" > .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
```

### Git别名配置（推荐）

方便快速创建提交信息：

```bash
# 查看最近5次提交（简化格式）
git config --global alias.last "log -5 --oneline"

# 查看最近5次提交（详细格式）
git config --global alias.l "log -5 --pretty=format:'%h %s%n%b' --stat"

# 编辑最后一次提交信息
git config --global alias.amend "commit --amend"
```

### IDE插件推荐

**VSCode**：
推荐插件：`Commitizen` 和 `Conventional Commits`
自动生成符合规范的提交信息

**PyCharm**：
插件：`Git Commit Msg Helper`
提供提交信息模板和格式检查

---

## 附录A：完整示例集

### 示例1：v6.4.1版本发布（复杂feat）

```
feat: v6.4.1 功能增强与质量优化

核心更新:
- 策略模块重构 (strategy.py +985行): 增强技术指标计算、信号生成、组合流程
- 回测引擎增强 (backtest.py +474行): 改进回测配置、结果分析、风险报告
- 菜单系统升级 (menus.yaml +363行): 新增因子质量验证、信号自动校验功能

新增功能:
- 因子有效性筛选器 (core/factor/validation/factor_effectiveness_filter.py)
  - 基于IC/IR的因子质量评估
  - 优秀因子(IC>0.05, IR>1.0)自动筛选
- 信号自动校验器 (core/signals/signal_auto_validator.py)
  - 信号质量多维度验证
  - 共振分析和置信度评分

改进项:
- 股票筛选器增强 (stock_selector.py): 记录每只股票的过滤原因
- 信号组合器优化 (signal_combiner.py): 改进因子+技术指标融合算法
- 风险监控完善 (portfolio_risk_monitor.py): 组合风险实时跟踪

Bug修复:
- exit_rules.py: 持仓天数计算增加空值检查

清理:
- 移除trading_records.json中的测试重复交易
- 版本号更新至6.4.1

测试通过: test_strategy_output.py验证数据-因子-策略流程正常

关联任务: TASK-20260321-001
```

### 示例2：简单配置更新（chore）

```
chore: 更新VERSION至6.4.1

关联任务: TASK-20260321-001
```

### 示例3：Bug修复（fix）

```
fix: 修复策略模块命令中的类型错误

TypeError: 'str' object is not callable

修复内容:
- 将策略名称的字符串引用改为函数引用
- 更新单元测试，覆盖此错误

影响范围:
- cli/commands/strategy.py
- 仅影响"策略执行"命令

关联任务: TASK-20260321-002
```

---

## 附录B：参考链接

- [Conventional Commits规范](https://www.conventionalcommits.org/)
- [Angular提交信息规范](https://github.com/angular/angular/blob/master/CONTRIBUTING.md#commit)
- [Git提交最佳实践](https://github.com/erlang/otp/wiki/Writing-good-commit-messages)

---

**文档维护者**: ✍️创作者
**最后更新**: 2026-03-21
**版本**: v1.0
