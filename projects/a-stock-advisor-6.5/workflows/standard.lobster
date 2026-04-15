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
      --args-json '{"max_stocks": {{max_stocks}}, "enable_quality_gate": {{enable_quality_gate}}, "quality_gate_strict": {{quality_gate_strict}}, "rebalance_threshold": {{rebalance_threshold}}, "factor_decay_threshold": {{factor_decay_threshold}}}'

  - id: data_update
    run: >
      python -m core.pipeline_step data_update
      --args-json '{"max_stocks": {{max_stocks}}, "enable_quality_gate": {{enable_quality_gate}}}'
    when: $position_check.ok

  - id: data_quality
    run: >
      python -m core.pipeline_step data_quality
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $data_update.ok

  - id: factor_calc
    run: >
      python -m core.pipeline_step factor_calc
      --args-json '{"max_factors": {{max_factors}}, "enable_quality_gate": {{enable_quality_gate}}}'
    when: $data_quality.ok

  - id: factor_validate
    run: >
      python -m core.pipeline_step factor_validate
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $factor_calc.ok

  - id: alpha_generate
    run: >
      python -m core.pipeline_step alpha_generate
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $factor_validate.ok

  - id: strategy_execute
    run: >
      python -m core.pipeline_step strategy_execute
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $alpha_generate.ok

  - id: portfolio_optimize
    run: >
      python -m core.pipeline_step portfolio_optimize
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $strategy_execute.ok

  - id: risk_check
    run: >
      python -m core.pipeline_step risk_check
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $portfolio_optimize.ok

  - id: report_generate
    run: >
      python -m core.pipeline_step report_generate
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $risk_check.ok

  - id: monitor_push
    run: >
      python -m core.pipeline_step monitor_push
      --args-json '{"enable_quality_gate": {{enable_quality_gate}}}'
    when: $report_generate.ok
