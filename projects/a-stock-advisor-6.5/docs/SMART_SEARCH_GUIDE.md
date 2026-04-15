# 智能搜索功能使用指南

## 概述

智能搜索系统可以自动生成最优的搜索关键词，无需手动指定。系统基于以下维度智能选择关键词：

1. **市场热点** - AI因子、机器学习Alpha等前沿主题
2. **因子库缺口** - 自动识别未探索的因子类型
3. **学术前沿** - 因子研究最新进展
4. **历史表现** - 基于过去搜索成功率优化

## 快速开始

### 1. 智能搜索（推荐）

自动生成关键词并执行搜索：

```bash
# 使用平衡策略（默认）
python -m core.rdagent_integration.auto_mine smart

# 使用热点策略
python -m core.rdagent_integration.auto_mine smart --strategy hot --max-papers 5

# 使用缺口填补策略
python -m core.rdagent_integration.auto_mine smart --strategy gap

# 使用学术前沿策略
python -m core.rdagent_integration.auto_mine smart --strategy academic
```

### 2. 传统搜索 + 智能关键词

在传统模式中启用智能关键词生成：

```bash
python -m core.rdagent_integration.auto_mine auto --smart --strategy balanced
```

### 3. 手动指定关键词

仍然支持手动指定关键词：

```bash
python -m core.rdagent_integration.auto_mine auto --keywords "value factor" "momentum factor" "China"
```

## 搜索策略说明

| 策略 | 说明 | 适用场景 |
|------|------|----------|
| **balanced** | 平衡各类因子，覆盖价值、动量、质量等 | 日常搜索，广泛探索 |
| **hot** | 聚焦市场热点，如AI因子、机器学习Alpha | 追踪前沿趋势 |
| **gap** | 填补因子库缺口，优先搜索未探索的因子类型 | 完善因子库 |
| **academic** | 学术前沿，关注因子研究最新进展 | 研究导向 |
| **random** | 随机组合，探索意外发现 | 探索性搜索 |

## 自动搜索调度

### 配置文件

复制配置文件模板：

```bash
cp auto_search_config.json.example auto_search_config.json
```

编辑配置文件：

```json
{
  "enabled": true,
  "schedule": {
    "daily": {
      "enabled": true,
      "time": "09:00",
      "strategy": "balanced",
      "max_papers": 10
    },
    "weekly": {
      "enabled": true,
      "day": "monday",
      "time": "08:00",
      "strategy": "gap",
      "max_papers": 20
    }
  },
  "focus_areas": ["value", "momentum", "quality"],
  "include_china": true,
  "auto_import": true
}
```

### 启动守护进程

```bash
# 启动自动搜索守护进程（后台运行）
nohup python -m core.rdagent_integration.auto_scheduler --daemon > auto_search.log 2>&1 &

# 查看日志
tail -f auto_search.log
```

### 执行一次搜索

```bash
python -m core.rdagent_integration.auto_scheduler --once --strategy hot
```

### 查看性能报告

```bash
python -m core.rdagent_integration.auto_scheduler --report
```

## 性能优化

系统会自动记录每次搜索的结果，并基于历史数据优化关键词选择：

- **成功率追踪** - 记录每个关键词的因子提取成功率
- **智能推荐** - 基于历史表现推荐最佳关键词组合
- **去重优化** - 避免重复搜索相同关键词

## 示例输出

```
============================================
智能搜索功能测试
============================================

Step 1: 测试智能关键词生成
测试不同搜索策略:

balanced    : value factor, residual momentum, sentiment analysis factor, factor combination, Chinese institutional investor
hot         : ESG factor investing, reinforcement learning trading, LLM financial analysis
gap         : dividend yield, PE ratio factor, momentum factor, time series momentum, ROE factor
academic    : factor robustness, factor timing, factor zoo, Bollinger bands factor

推荐关键词组合:
  [1] value factor, momentum factor, China A-share
  [2] machine learning alpha, factor selection, stock prediction
  [3] ESG factor, quality factor, sustainability
```

## 高级用法

### 自定义关注领域

在配置文件中设置 `focus_areas`：

```json
{
  "focus_areas": ["value", "momentum", "quality", "liquidity", "sentiment"]
}
```

### 中国市场专属

启用中国市场关键词：

```json
{
  "include_china": true
}
```

这将自动添加中国A股相关关键词，如：
- China A-share factor
- Chinese stock market
- A-share anomaly

### 飞书通知

配置飞书推送：

```json
{
  "notification": {
    "enabled": true,
    "webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  }
}
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `smart_search.py` | 智能关键词生成器 |
| `auto_scheduler.py` | 自动搜索调度器 |
| `auto_mine.py` | 因子挖掘主程序 |
| `search_history.json` | 搜索历史记录 |
| `keyword_stats.json` | 关键词性能统计 |
| `auto_search_config.json` | 自动搜索配置 |

## 最佳实践

1. **日常使用** - 使用 `balanced` 策略进行日常搜索
2. **追踪前沿** - 每周使用 `hot` 策略追踪市场热点
3. **完善因子库** - 每月使用 `gap` 策略填补缺口
4. **研究导向** - 使用 `academic` 策略关注学术前沿
5. **定期查看报告** - 每周查看性能报告，优化搜索策略

## 故障排查

### 问题：智能搜索未生成关键词

检查是否安装了依赖：

```bash
pip install schedule
```

### 问题：搜索历史未记录

确保有写入权限：

```bash
chmod 644 search_history.json keyword_stats.json
```

### 问题：自动调度器未运行

检查配置文件中的 `enabled` 字段是否为 `true`。

## 下一步

1. 运行测试：`bash test_smart_search.sh`
2. 执行智能搜索：`python -m core.rdagent_integration.auto_mine smart`
3. 查看性能报告：`python -m core.rdagent_integration.auto_scheduler --report`
4. 配置自动调度：编辑 `auto_search_config.json`
