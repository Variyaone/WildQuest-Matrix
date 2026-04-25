name: backtest
args:
  max_factors:
    default: null
  enable_quality_gate:
    default: true
  quality_gate_strict:
    default: true

steps:
  - id: factor_calc
    run: >
      python -m core.pipeline_step factor_calc
      --args-json '{"max_factors": {{max_factors}}, "enable_quality_gate": {{enable_quality_gate}}}'

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
