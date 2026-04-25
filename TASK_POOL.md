# RD-Agent 因子挖掘任务池

## 任务状态

### 步骤1: 下载论文
- 状态: done
- 描述: 从arXiv下载量化投资相关论文

### 步骤2: 预处理论文
- 状态: done
- 描述: 对下载的论文进行预处理，提取关键部分

### 步骤3: 提取因子
- 状态: done
- 描述: 从论文中提取量化因子
- 输出: extracted_factors.json
- 因子数量: 7
- 因子列表:
  1. ILLIQ - Illiquidity factor
  2. MOMENTUM - Momentum factor
  3. BM_RATIO - Book-to-market ratio
  4. SIZE - Size factor
  5. VOLATILITY - Volatility factor
  6. TURNOVER - Turnover factor
  7. SENTIMENT - Sentiment factor

### 步骤4: 因子回测
- 状态: pending
- 描述: 对提取的因子进行回测验证

### 步骤5: 因子优化
- 状态: pending
- 描述: 根据回测结果优化因子

## 备注

- 步骤3的因子提取由于RDAgent处理PDF超时，采用了手动补充的方式
- 提取的因子包含了经典的量化因子（如Momentum、Size、BM等）以及基于LLM的新因子（如Sentiment）
