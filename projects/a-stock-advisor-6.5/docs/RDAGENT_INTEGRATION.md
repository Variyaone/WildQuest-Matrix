# RDAgent 集成文档

## 概述

WildQuest Matrix 已成功集成微软 RDAgent（Gitee镜像版本），提供自动化的量化策略研发能力。

## 安装状态

✓ RDAgent 已安装到 `.venv-rdagent` 虚拟环境
✓ Python 版本: 3.10
✓ 版本来源: https://gitee.com/variyaone/RD-Agent

## 使用方式

### 方式1: 通过主菜单

```bash
python core/main.py
# 选择 [2] 因子管理 → [9] RDAgent智能挖掘
```

### 方式2: 通过Python API

```python
from core.rdagent_integration import RDAgentRunner, RDAgentScenario

runner = RDAgentRunner()

# 因子挖掘
result = runner.run_fin_factor()

# 模型设计
result = runner.run_fin_model()

# 因子-模型协同
result = runner.run_fin_quant()

# 从报告提取因子
result = runner.run_fin_factor_report("/path/to/reports")

# 从论文提取模型
result = runner.run_general_model("https://arxiv.org/pdf/xxxx.xxxxx")
```

## 可用场景

| 场景 | 命令 | 说明 |
|------|------|------|
| 因子挖掘 | `fin_factor` | LLM自动迭代提出和实现因子 |
| 模型设计 | `fin_model` | LLM自动迭代优化预测模型 |
| 因子-模型协同 | `fin_quant` | 联合优化因子和模型 |
| 报告因子提取 | `fin_factor_report` | 从金融报告PDF提取因子 |
| 论文模型提取 | `general_model` | 从学术论文提取模型架构 |
| 数据科学 | `data_science` | Kaggle竞赛自动优化 |

## 配置文件

配置文件位于: `.env.rdagent`

关键配置项:
- `CHAT_MODEL`: LLM模型（如 gpt-4o, deepseek-chat）
- `OPENAI_API_KEY`: API密钥
- `OPENAI_API_BASE`: API端点
- `EMBEDDING_MODEL`: 嵌入模型

## 架构说明

```
core/rdagent_integration/
├── __init__.py          # 模块入口
├── config.py            # 配置管理
├── runner.py            # 场景运行器
└── menu.py              # 菜单集成
```

## 测试

运行测试脚本验证集成:

```bash
python test_rdagent_integration_new.py
```

## 备份

旧版本已备份到: `backup/rdagent_20260404_174541/`

## 更新日志

### 2026-04-04
- 从 Gitee 克隆最新版本 RD-Agent
- 删除旧的集成代码
- 创建新的集成模块 `core/rdagent_integration`
- 更新主菜单集成
- 所有测试通过

## 参考资料

- [RDAgent官方文档](https://rdagent.readthedocs.io/)
- [Gitee镜像](https://gitee.com/variyaone/RD-Agent)
- [GitHub原版](https://github.com/microsoft/RD-Agent)
- [RDAgent论文](https://arxiv.org/abs/2505.14738)
- [RDAgent-Quant论文](https://arxiv.org/abs/2505.15155)
