name: scheduled-push
description: 定时推送工作流，每日收盘后自动执行标准量化流程，生成投资建议并推送

# 引用标准推送流程
base_workflow: standard.lobster

# 定时任务配置
schedule:
  cron: "0 16 * * 1-5"  # 工作日16:00执行（收盘后）
  timezone: "Asia/Shanghai"

# 工作流参数
args:
  max_stocks: null
  max_factors: null
  enable_quality_gate: true
  quality_gate_strict: true
  rebalance_threshold: 0.05
  factor_decay_threshold: 0.3

# 超时配置
timeout:
  position_check: 300      # 5分钟
  data_update: 600         # 10分钟
  data_quality: 300        # 5分钟
  factor_calc: 900         # 15分钟
  factor_validate: 600     # 10分钟
  alpha_generate: 600      # 10分钟
  strategy_execute: 900    # 15分钟
  portfolio_optimize: 600  # 10分钟
  risk_check: 300          # 5分钟
  report_generate: 600     # 10分钟
  daily_report_approval: 3600  # 1小时（等待人工审批）
  monitor_push: 300        # 5分钟
  total: 7200              # 2小时

# 重试策略
retry:
  max_retries: 2
  backoff: exponential
  initial_delay: 60  # 1分钟
  max_delay: 300    # 5分钟

# 失败处理
failure_handling:
  on_step_failure: retry
  on_all_retries_failed: notify
  notify_channels:
    - feishu
    - email

# 通知配置
notification:
  enabled: true
  channels:
    - feishu
    - email

  on_success:
    - type: feishu
      channel: user
      message: "✅ A股量化推送已完成，请查看结果"
    - type: email
      subject: "✅ A股量化推送完成"
      body: "量化推送已完成，请查看附件"

  on_failure:
    - type: feishu
      channel: user
      message: "❌ A股量化推送失败，请检查日志"
      priority: high
    - type: email
      subject: "❌ A股量化推送失败"
      body: "量化推送失败，请检查日志"
      priority: high

  on_approval_required:
    - type: feishu
      channel: user
      message: "⏳ 日报待审批，请审核后决定是否推送"
      priority: normal

  on_approval_rejected:
    - type: feishu
      channel: user
      message: "❌ 日报审批被拒绝，未推送"
      priority: high

  on_risk_alert:
    - type: feishu
      channel: user
      message: "🚨 风控告警：{alert_message}"
      priority: urgent

# 质量标准
quality_standards:
  - name: 数据完整性
    threshold: "≥ 99%"
    check: data_quality.completeness
  - name: 数据时效性
    threshold: "< 24小时"
    check: data_update.freshness
  - name: 因子IC
    threshold: "> 0.02"
    check: factor_validate.ic
  - name: 因子IR
    threshold: "> 0.25"
    check: factor_validate.ir
  - name: 风控合规
    threshold: "通过"
    check: risk_check.passed

# 监控配置
monitoring:
  enabled: true
  metrics:
    - name: step_duration
      type: histogram
      labels: [step_name]
    - name: step_success_rate
      type: gauge
      labels: [step_name]
    - name: total_duration
      type: gauge
    - name: data_quality_score
      type: gauge
    - name: factor_count
      type: gauge
    - name: risk_alert_count
      type: gauge
    - name: workflow_success_rate
      type: gauge
    - name: approval_rate
      type: gauge

# 日志配置
logging:
  level: info
  format: json
  output: /Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5/logs/scheduled-push-{date}.log

# 环境配置
environment:
  python_path: /Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5/.venv-rdagent/bin/python
  working_dir: /Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5

# 风险提示
risk_warnings:
  - "历史表现不代表未来"
  - "市场环境变化可能影响策略效果"
  - "数据延迟可能导致决策偏差"
  - "投资有风险，建议仅供参考"
  - "本推送仅供量化研究，不构成投资建议"

# 归档配置
archive:
  enabled: true
  destination: /Users/variya/.openclaw/workspace/projects/a-stock-advisor-6.5/archive/scheduled-push-{date}.json
  format: |
    {
      "date": "{date}",
      "start_time": "{start_time}",
      "end_time": "{end_time}",
      "result": "{result}",
      "data_quality_score": "{data_quality_score}",
      "factor_count": "{factor_count}",
      "risk_status": "{risk_status}",
      "portfolio_count": "{portfolio_count}",
      "approval_status": "{approval_status}",
      "push_status": "{push_status}"
    }
