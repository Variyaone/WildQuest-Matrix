# 自动论文因子挖掘功能

## 概述

新增自动搜索学术论文并提取因子的功能，实现**论文搜索 → 筛选 → 下载 → 因子提取**的完整自动化流程。

## 功能特性

### 1. 多源论文搜索

| 数据源 | 说明 | 特点 |
|--------|------|------|
| **arXiv** | 学术预印本平台 | 免费、快速、量化金融分类 |
| **Semantic Scholar** | AI学术搜索引擎 | 引用数、开放获取PDF |
| **OpenAlex** | 开放学术图谱 | 免费、覆盖广、开放获取 |
| **Crossref** | DOI注册机构 | 权威、期刊论文、引用数 |
| **CORE** | 开放获取聚合 | 全球开放获取论文 |

### 2. 智能筛选
- 基于关键词相关性评分
- 引用数加权
- **自动去重**：排除已处理的论文

### 3. 自动下载
- 批量下载PDF
- 智能命名

### 4. 因子提取
- 复用RDAgent的PDF解析能力
- 自动提取因子公式
- 结构化输出

### 5. 论文去重追踪
- 自动记录已处理的论文
- 避免重复处理同一篇论文
- 追踪文件：`processed_papers.json`

---

## 搜索关键词

系统内置 **150+ 量化金融关键词**，覆盖：

| 类别 | 示例关键词 |
|------|-----------|
| **因子投资** | factor investing, momentum factor, value factor, size factor, quality factor, low volatility |
| **技术指标** | RSI, MACD, Bollinger bands, moving average, KDJ, OBV |
| **风险管理** | VaR, maximum drawdown, Sharpe ratio, tracking error, beta hedging |
| **策略类型** | statistical arbitrage, pairs trading, trend following, mean reversion |
| **资产定价** | CAPM, Fama French, Carhart four factor, q-factor model |
| **行为金融** | investor sentiment, herding behavior, overreaction, underreaction |
| **ESG因子** | ESG factor, sustainability, climate risk, carbon footprint |
| **估值模型** | DCF, PE ratio, PB ratio, dividend discount, residual income |
| **宏观经济** | GDP growth, inflation, monetary policy, yield curve |
| **机器学习** | financial machine learning, time series forecasting, anomaly detection |

> **注意**: 当不指定关键词时，系统会**随机选择20个关键词**进行搜索，每次搜索使用不同的关键词组合，扩大论文覆盖范围。

---

## 使用方式

### 方式一：完整自动化流程（推荐）

```bash
# 一键完成：搜索 → 筛选 → 下载 → 提取
python3 -m core.rdagent_integration.auto_mine auto \
  --keywords "factor investing" "momentum" "alpha" \
  --max-papers 10 \
  --output-dir papers \
  --output-file extracted_factors.json
```

### 方式二：分步执行

#### Step 1: 搜索论文

```bash
# 使用默认关键词
python3 -m core.rdagent_integration.auto_mine search \
  --max-results 30 \
  --output papers_search_results.json

# 自定义关键词
python3 -m core.rdagent_integration.auto_mine search \
  --keywords "stock prediction" "technical indicator" \
  --max-results 20 \
  --output papers_search_results.json

# 自定义查询
python3 -m core.rdagent_integration.auto_mine search \
  --query "momentum factor AND stock return" \
  --max-results 15 \
  --output papers_search_results.json
```

#### Step 2: 下载论文

```bash
python3 -m core.rdagent_integration.auto_mine download \
  --papers-file papers_search_results.json \
  --output-dir papers \
  --max-papers 10
```

#### Step 3: 提取因子

```bash
python3 -m core.rdagent_integration.auto_mine extract \
  --papers-dir papers \
  --output extracted_factors.json
```

---

## Python API

### 完整管线

```python
from core.rdagent_integration import AutoFactorMiningPipeline

# 初始化
pipeline = AutoFactorMiningPipeline(
    rdagent_venv=".venv-rdagent",
    paper_output_dir="papers",
    factor_output_file="extracted_factors.json"
)

# 运行
result = pipeline.run(
    keywords=["factor investing", "momentum", "alpha"],
    max_papers=10,
    min_relevance_score=0.3
)

print(f"找到论文: {result['papers_found']} 篇")
print(f"提取因子: {result['factors_extracted']} 个")
```

### 单独使用搜索器

```python
from core.rdagent_integration import PaperSearcher

# 创建搜索器
searcher = PaperSearcher(
    use_arxiv=True,
    use_semantic_scholar=True,
    max_results_per_source=30
)

# 搜索论文
papers = searcher.search(
    keywords=["momentum factor", "stock prediction"],
)

# 下载论文
pdf_paths = searcher.download_papers(
    papers,
    output_dir="papers",
    max_papers=10
)
```

### 单独使用筛选器

```python
from core.rdagent_integration import PaperFilter

# 计算相关性得分
score = PaperFilter.calculate_relevance_score(paper_dict)

# 筛选论文
filtered_papers = PaperFilter.filter_papers(
    papers,
    min_score=0.3,
    max_papers=20
)
```

### 单独使用因子提取器

```python
from core.rdagent_integration import FactorExtractor

# 创建提取器
extractor = FactorExtractor(rdagent_venv=".venv-rdagent")

# 从单个PDF提取
factors = extractor.extract_from_pdf("paper.pdf")

# 从多个PDF提取
factors = extractor.extract_from_papers(
    pdf_paths=["paper1.pdf", "paper2.pdf"],
    output_file="factors.json"
)
```

---

## 配置

### 默认搜索关键词

```python
QUANT_KEYWORDS = [
    "quantitative finance",
    "factor investing",
    "stock prediction",
    "portfolio optimization",
    "alpha factor",
    "momentum factor",
    "value factor",
    "technical indicator",
    "trading strategy",
    "market prediction",
    "financial machine learning",
    "time series forecasting",
    "stock return",
    "asset pricing",
    "risk factor",
]
```

### 筛选评分规则

| 因素 | 权重 |
|------|------|
| 相关关键词出现 | +0.1 |
| 不相关关键词出现 | -0.2 |
| 引用数（每100次） | +0.3 |

**通过阈值**: 0.3

---

## 输出格式

### 论文搜索结果 (papers_search_results.json)

```json
[
  {
    "title": "Factor Investing for the Long Run",
    "authors": ["Author A", "Author B"],
    "abstract": "This paper explores...",
    "url": "https://arxiv.org/abs/xxxx.xxxxx",
    "pdf_url": "https://arxiv.org/pdf/xxxx.xxxxx",
    "published_date": "2024-01-15",
    "categories": ["q-fin.PM", "q-fin.ST"],
    "citation_count": 42,
    "relevance_score": 0.75
  }
]
```

### 提取的因子 (extracted_factors.json)

```json
[
  {
    "name": "Momentum_20",
    "description": "20日动量因子",
    "formulation": "close_t / close_{t-20} - 1",
    "variables": {
      "close": "收盘价"
    },
    "source_paper": "Factor_Investing_Long_Run",
    "source_url": "https://arxiv.org/pdf/xxxx.xxxxx",
    "confidence": 0.8
  }
]
```

---

## 依赖安装

### 基础依赖

```bash
pip install arxiv requests
```

### RDAgent依赖 (因子提取)

因子提取功能依赖RDAgent，需要：

1. **RDAgent安装** (已集成到项目中)
   ```bash
   # RDAgent位于 /tmp/RD-Agent
   # 虚拟环境位于 .venv-rdagent
   ```

2. **LLM API配置**
   
   因子提取使用LLM解析PDF，需要配置OpenAI API：
   ```bash
   export OPENAI_API_KEY="your-api-key"
   # 或
   export AZURE_OPENAI_API_KEY="your-azure-key"
   ```

3. **RDAgent模块路径**
   
   正确的导入路径：
   ```python
   from rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader import FactorExperimentLoaderFromPDFfiles
   ```

> **注意**: 因子提取过程会调用LLM API解析PDF内容，可能产生API费用。每篇论文提取时间约1-5分钟。

---

## 使用示例

### 示例1：挖掘动量因子

```bash
python3 -m core.rdagent_integration.auto_mine auto \
  --keywords "momentum" "trend following" \
  --max-papers 5 \
  --output-dir papers/momentum \
  --output-file momentum_factors.json
```

### 示例2：挖掘价值因子

```bash
python3 -m core.rdagent_integration.auto_mine auto \
  --keywords "value investing" "fundamental factor" \
  --max-papers 5 \
  --output-dir papers/value \
  --output-file value_factors.json
```

### 示例3：挖掘技术指标

```bash
python3 -m core.rdagent_integration.auto_mine auto \
  --keywords "technical indicator" "price pattern" \
  --max-papers 5 \
  --output-dir papers/technical \
  --output-file technical_factors.json
```

---

## 注意事项

1. **API限流**: Semantic Scholar有API调用限制，建议配置API Key
2. **下载速度**: 批量下载时自动添加延迟，避免被封IP
3. **PDF解析**: 依赖RDAgent的PDF解析能力，确保已正确安装
4. **因子验证**: 提取的因子建议进一步验证后再使用

---

## 与现有功能集成

提取的因子可以直接导入到因子库：

```python
from core.factor import get_factor_quick_entry

quick_entry = get_factor_quick_entry()

# 从提取结果导入
for factor_data in extracted_factors:
    result = quick_entry.quick_add(
        name=factor_data["name"],
        formula=factor_data["formulation"],
        description=factor_data["description"],
        source=f"论文: {factor_data['source_paper']}",
        category="自动提取",
        direction="正向",
        tags=["论文提取", "RDAgent"]
    )
```

---

## 更新日志

### 2026-04-05
- 新增论文搜索模块（arXiv + Semantic Scholar）
- 新增论文筛选和排序功能
- 新增因子自动提取功能
- 新增完整自动化管线
- **新增论文去重功能**：自动记录已处理论文，避免重复处理
- **修复arxiv模块导入问题**：改为延迟导入，避免启动时报错
- 测试通过

---

## 论文去重功能

### 工作原理

系统会自动记录已处理的论文到 `processed_papers.json` 文件中，包括：
- 论文URL
- 论文标题
- 提取的因子数量
- 处理时间

### 去重流程

```
搜索论文 → 筛选相关性 → 排除已处理 → 下载新论文 → 提取因子 → 标记已处理
```

### 查看已处理论文

```python
from core.rdagent_integration import ProcessedPapersTracker

tracker = ProcessedPapersTracker()
stats = tracker.get_stats()

print(f"已处理论文: {stats['total_processed']} 篇")
print(f"最近处理: {stats['last_processed']}")
```

### 重置处理记录

如需重新处理所有论文，删除追踪文件即可：

```bash
rm processed_papers.json
```

### 追踪文件格式

```json
{
  "processed_urls": {
    "https://arxiv.org/abs/xxxx.xxxxx": {
      "title": "Factor Investing for the Long Run",
      "factors_count": 3,
      "processed_at": "2026-04-05T10:30:00"
    }
  },
  "processed_titles": {
    "Factor Investing for the Long Run": {
      "url": "https://arxiv.org/abs/xxxx.xxxxx",
      "factors_count": 3,
      "processed_at": "2026-04-05T10:30:00"
    }
  }
}
```
