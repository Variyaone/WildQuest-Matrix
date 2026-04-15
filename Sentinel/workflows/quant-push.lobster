# 量化推送工作流 - Lobster

name: quant-push
description: 生成完全可信的量化交易推送，包含策略概述、因子说明、回测结果、交易建议和风险提示

# 工作目录
working_dir: /Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5

# 步骤定义
steps:
  # 步骤1: 数据更新
  - id: data_update
    name: 数据更新
    agent: researcher
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId researcher
      --task "更新市场数据到最新日期，使用asa-quant CLI执行数据更新命令"
      --mode run
    timeout: 600  # 10分钟
    output: data_update_result.json
    on_failure: retry 2

  # 步骤2: 因子计算
  - id: factor_calculation
    name: 因子计算
    agent: researcher
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId researcher
      --task "基于更新后的市场数据，计算所有技术因子，筛选有效因子（IC>0.05, IR>0.5），输出有效因子列表"
      --mode run
    timeout: 900  # 15分钟
    depends_on: data_update
    input: data_update_result.json
    output: effective_factors.json
    on_failure: retry 2

  # 步骤3: 策略设计
  - id: strategy_design
    name: 策略设计
    agent: architect
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId architect
      --task "基于有效因子列表，设计量化策略，确保满足盈利标准：年化收益率>15%，最大回撤<20%，夏普比率>1.0，信息比率>0.5"
      --mode run
    timeout: 1200  # 20分钟
    depends_on: factor_calculation
    input: effective_factors.json
    output: strategy_design.json
    on_failure: retry 2

  # 步骤4: 回测验证
  - id: backtest
    name: 回测验证
    agent: architect
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId architect
      --task "对设计的策略进行完整回测验证，时间范围：2024-01-01至2026-03-30，记录详细交易记录，生成绩效指标"
      --mode run
    timeout: 900  # 15分钟
    depends_on: strategy_design
    input: strategy_design.json
    output: backtest_report.json
    on_failure: retry 2

  # 步骤5: 推送生成
  - id: push_generation
    name: 推送生成
    agent: creator
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId creator
      --task "基于回测报告，生成量化推送内容（Markdown格式），包含：策略概述、因子说明、回测结果、交易建议、风险提示、免责声明"
      --mode run
    timeout: 600  # 10分钟
    depends_on: backtest
    input: backtest_report.json
    output: push_content.md
    on_failure: retry 2

  # 步骤6: 质量审核
  - id: quality_review
    name: 质量审核
    agent: critic
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId critic
      --task "审核推送内容，检查：数据准确性、逻辑清晰性、风险提示充分性、格式规范性，必须实测验证所有指标"
      --mode run
    timeout: 600  # 10分钟
    depends_on: push_generation
    input: push_content.md
    output: review_result.json
    on_failure: escalate  # 升级为T0

# 质量标准
quality_standards:
  - name: 年化收益率
    threshold: "> 15%"
    check: backtest_report.json.annual_return
  - name: 最大回撤
    threshold: "< 20%"
    check: backtest_report.json.max_drawdown
  - name: 夏普比率
    threshold: "> 1.0"
    check: backtest_report.json.sharpe_ratio
  - name: 信息比率
    threshold: "> 0.5"
    check: backtest_report.json.information_ratio
  - name: 数据来源
    threshold: "可靠"
    check: push_content.md.data_source
  - name: 风险提示
    threshold: "充分"
    check: push_content.md.risk_warning
  - name: 逻辑清晰
    threshold: "是"
    check: review_result.json.logic_clarity
  - name: 格式规范
    threshold: "是"
    check: review_result.json.format_standard

# 风险提示
risk_warnings:
  - "历史表现不代表未来"
  - "市场环境变化可能影响策略效果"
  - "数据延迟可能导致决策偏差"
  - "投资有风险，建议仅供参考"

# 输出格式
output_format:
  type: markdown
  sections:
    - title: 策略概述
      content: strategy_overview
    - title: 因子说明
      content: factor_description
    - title: 回测结果
      content: backtest_results
    - title: 交易建议
      content: trading_recommendations
    - title: 风险提示
      content: risk_warnings
    - title: 免责声明
      content: disclaimer

# 通知配置
notifications:
  on_success:
    - type: feishu
      channel: user
      message: "量化推送已完成，请查看结果"
  on_failure:
    - type: feishu
      channel: user
      message: "量化推送失败，请检查日志"
  on_review_failed:
    - type: feishu
      channel: user
      message: "质量审核未通过，需要重新执行"

# 归档配置
archive:
  enabled: true
  destination: /Users/variya/.openclaw/workspace/Sentinel/ARCHIVE.md
  format: |
    ### TASK-QUANT-PUSH-{date}: 量化推送
    - 执行时间: {start_time} - {end_time}
    - 执行者: main
    - 结果: {result}
    - 审查: {review_result}
    - 数据: {data_summary}

# 重试策略
retry_policy:
  max_retries: 2
  backoff: exponential
  initial_delay: 60  # 1分钟
  max_delay: 300  # 5分钟

# 超时策略
timeout_policy:
  step_timeout: 1200  # 20分钟
  total_timeout: 3600  # 60分钟
  on_timeout: retry 1

# 失败处理
failure_handling:
  on_step_failure: retry
  on_all_retries_failed: escalate
  escalate_to: T0
  escalate_message: "量化推送工作流失败，需要人工干预"

# 监控配置
monitoring:
  enabled: true
  metrics:
    - name: step_duration
      type: histogram
    - name: step_success_rate
      type: gauge
    - name: total_duration
      type: gauge
    - name: quality_score
      type: gauge

# 日志配置
logging:
  level: info
  format: json
  output: /Users/variya/.openclaw/workspace/Sentinel/logs/quant-push-{date}.log
