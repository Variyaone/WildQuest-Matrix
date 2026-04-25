name: standard
args:
  max_stocks:
    default: null
  max_factors:
    default: null
  enable_quality_gate:
    default: true
  quality_gate_strict:
    default: true
  rebalance_threshold:
    default: 0.05
  factor_decay_threshold:
    default: 0.3

steps:
  - id: position_check
    run: >
      python -m core.pipeline_step position_check
      --args-json '{"max_stocks": "{{max_stocks}}", "enable_quality_gate": "{{enable_quality_gate}}", "quality_gate_strict": "{{quality_gate_strict}}", "rebalance_threshold": "{{rebalance_threshold}}", "factor_decay_threshold": "{{factor_decay_threshold}}"}'

  - id: data_update
    run: >
      python -m core.pipeline_step data_update
      --args-json '{"max_stocks": "{{max_stocks}}", "enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $position_check.ok

  - id: data_quality
    run: >
      python -m core.pipeline_step data_quality
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $data_update.ok

  - id: factor_calc
    run: >
      python -m core.pipeline_step factor_calc
      --args-json '{"max_factors": "{{max_factors}}", "enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $data_quality.ok

  - id: factor_validate
    run: >
      python -m core.pipeline_step factor_validate
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $factor_calc.ok

  - id: alpha_generate
    run: >
      python -m core.pipeline_step alpha_generate
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $factor_validate.ok

  - id: strategy_execute
    run: >
      python -m core.pipeline_step strategy_execute
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $alpha_generate.ok

  - id: portfolio_optimize
    run: >
      python -m core.pipeline_step portfolio_optimize
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $strategy_execute.ok

  - id: risk_check
    run: >
      python -m core.pipeline_step risk_check
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $portfolio_optimize.ok

  - id: report_generate
    run: >
      python -m core.pipeline_step report_generate
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $risk_check.ok

  - id: daily_report_approval
    approval: "📊 日报已生成，请审核后决定是否推送\n\n📈 关键指标：\n- 数据质量：{{data_quality_score}}%\n- 因子数量：{{factor_count}}个\n- 风控状态：{{risk_status}}\n- 推荐组合：{{portfolio_count}}只股票\n\n⚠️ 风险提示：\n- 历史表现不代表未来\n- 市场环境变化可能影响策略效果\n- 投资有风险，建议仅供参考\n\n请确认是否推送日报？"
    when: $report_generate.ok && $report_generate.json.details.quality_passed

  - id: monitor_push
    run: >
      python -m core.pipeline_step monitor_push
      --args-json '{"enable_quality_gate": "{{enable_quality_gate}}"}'
    when: $daily_report_approval.approved
