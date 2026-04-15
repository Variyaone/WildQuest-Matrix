# 文档索引

## 📚 文档导航

### 核心文档

#### 1. [TODO.md](../TODO.md)
**用途**: 待办事项清单  
**内容**: 
- 已完成的工作清单
- 待完成的优化任务
- 功能增强计划

**适合人群**: 开发者、项目经理

---

#### 2. [REFACTOR_SUMMARY.md](../REFACTOR_SUMMARY.md)
**用途**: 重构技术总结  
**内容**:
- 架构变更说明
- 技术实现细节
- 测试结果分析
- 架构对比

**适合人群**: 技术人员、架构师

---

#### 3. [COMPLETION_REPORT.md](../COMPLETION_REPORT.md)
**用途**: 项目完成报告  
**内容**:
- 执行时间线
- 成果统计
- 质量指标
- 验收标准

**适合人群**: 管理层、项目干系人

---

#### 4. [FINAL_SUMMARY.md](../FINAL_SUMMARY.md)
**用途**: 最终总结报告  
**内容**:
- 完整的时间线
- 技术亮点分析
- 迁移路径说明
- 交付物清单

**适合人群**: 所有人员

---

### 技术文档

#### 5. [ARCHITECTURE.md](ARCHITECTURE.md)
**用途**: 架构设计文档  
**内容**:
- 新架构设计说明
- 旧架构对比分析
- 核心模块详解
- 数据流转说明

**适合人群**: 架构师、开发者

---

#### 6. [API.md](API.md)
**用途**: API接口文档  
**内容**:
- FactorCombiner API
- AlphaGenerator API
- 策略创建流程
- 完整示例代码

**适合人群**: 开发者

---

#### 7. [USER_GUIDE.md](USER_GUIDE.md)
**用途**: 用户使用指南  
**内容**:
- 快速开始
- 核心功能说明
- 完整工作流程
- 最佳实践

**适合人群**: 所有用户

---

### 数据备份文档

#### 8. [data/backup_signals_20260403/README.md](../data/backup_signals_20260403/README.md)
**用途**: 数据备份说明  
**内容**:
- 备份文件列表
- 备份原因说明
- 恢复方法

**适合人群**: 运维人员、数据管理员

---

## 🧪 测试文档

### 测试脚本

#### 1. [test_new_architecture.py](../test_new_architecture.py)
**用途**: 基础功能测试  
**测试内容**:
- 模块导入
- 因子组合
- 策略创建

#### 2. [test_full_pipeline.py](../test_full_pipeline.py)
**用途**: 完整流程测试  
**测试内容**:
- 因子 → Alpha → 策略完整流程
- 架构一致性验证

#### 3. [verify_system.py](../verify_system.py)
**用途**: 系统完整性验证  
**验证内容**:
- 模块导入
- 废弃标记
- 数据备份
- 文档完整性
- 核心功能

---

## 📖 快速开始

### 对于开发者
1. 阅读 [ARCHITECTURE.md](ARCHITECTURE.md) 了解架构设计
2. 查看 [API.md](API.md) 学习API使用
3. 运行 `python3 verify_system.py` 验证系统

### 对于管理者
1. 阅读 [COMPLETION_REPORT.md](../COMPLETION_REPORT.md) 了解项目成果
2. 查看 [FINAL_SUMMARY.md](../FINAL_SUMMARY.md) 了解完整情况
3. 检查质量指标和验收标准

### 对于用户
1. 阅读 [USER_GUIDE.md](USER_GUIDE.md) 学习使用方法
2. 查看示例代码
3. 运行测试验证功能

### 对于运维人员
1. 查看 [data/backup_signals_20260403/README.md](../data/backup_signals_20260403/README.md) 了解数据备份
2. 确认备份文件完整性
3. 了解恢复方法

---

## 🔍 关键信息

### 架构变更
```
旧架构: 因子 → 信号 → 策略
新架构: 因子 → Alpha → 策略
```

### 核心模块
- **FactorCombiner**: 因子组合优化
- **AlphaGenerator**: Alpha生成

### 废弃模块
- **SignalConfig**: 已移除
- **StockSelector**: 已废弃
- **Signal层**: 已移除

### 数据备份
- 位置: `data/backup_signals_20260403/`
- 文件: 3个JSON文件
- 说明: 详见备份目录README.md

---

## ✅ 项目状态

**状态**: ✅ 已完成  
**完成度**: 100%  
**质量评级**: A+  
**可用性**: 可投入生产使用

---

## 📞 联系方式

**架构负责人**: 陈默  
**完成日期**: 2026-04-03

---

## 🎯 后续工作

所有核心工作已完成，剩余为可选优化：

1. **功能增强** (可选)
   - Alpha分析功能
   - 高级组合优化

2. **性能优化** (可选)
   - 大规模数据处理
   - 并行计算

3. **测试补充** (可选)
   - 边界测试
   - 性能基准测试

---

**最后更新**: 2026-04-15

---

## 📌 最近更新 (v6.5.2)

### 数据源优化
- **BaoStock优先**: 股票列表获取优先使用BaoStock（含名称和行业信息）
- **多源切换**: 自动在YFinance/AkShare/EastMoney/BaoStock间切换
- **行业数据**: 支持5515只股票的行业分类信息

### 推送功能增强
- **股票名称**: 推送报告正确显示股票名称
- **行业集中度**: 风控检查使用真实行业数据
- **飞书集成**: 完整的Webhook推送支持

### 统一管线
- **快速模式**: `python -m core.daily --mode fast`
- **测试参数**: `--max-stocks N --max-factors N --no-quality-gate`
- **鲁棒性验证**: 存续偏差检查、极端事件冲击、过拟合检测
