# 代码审查工作流 - Lobster

name: code-review
description: 代码审查工作流，包括代码分析、安全检查、性能测试、文档审查、最终审核

# 工作目录
working_dir: /Users/variya/.openclaw/workspace

# 步骤定义
steps:
  # 步骤1: 代码分析
  - id: code_analysis
    name: 代码分析
    agent: architect
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId architect
      --task "分析代码结构、逻辑正确性、代码风格、潜在bug，输出分析报告"
      --mode run
    timeout: 900  # 15分钟
    input: code_path
    output: code_analysis_report.json
    on_failure: retry 1

  # 步骤2: 安全检查
  - id: security_check
    name: 安全检查
    agent: critic
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId critic
      --task "检查代码安全性，包括：SQL注入、XSS、CSRF、权限控制、敏感信息泄露，输出安全检查报告"
      --mode run
    timeout: 600  # 10分钟
    depends_on: code_analysis
    input: code_analysis_report.json
    output: security_check_report.json
    on_failure: retry 1

  # 步骤3: 性能测试
  - id: performance_test
    name: 性能测试
    agent: architect
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId architect
      --task "测试代码性能，包括：响应时间、内存使用、CPU使用、并发性能，输出性能测试报告"
      --mode run
    timeout: 900  # 15分钟
    depends_on: security_check
    input: code_path
    output: performance_test_report.json
    on_failure: retry 1

  # 步骤4: 文档审查
  - id: documentation_review
    name: 文档审查
    agent: creator
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId creator
      --task "审查代码文档，包括：注释完整性、README文档、API文档、使用示例，输出文档审查报告"
      --mode run
    timeout: 600  # 10分钟
    depends_on: performance_test
    input: code_path
    output: documentation_review_report.json
    on_failure: retry 1

  # 步骤5: 最终审核
  - id: final_review
    name: 最终审核
    agent: critic
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId critic
      --task "综合所有报告，进行最终审核，给出：通过/不通过/需要修改，并附上详细意见"
      --mode run
    timeout: 600  # 10分钟
    depends_on: documentation_review
    input:
      - code_analysis_report.json
      - security_check_report.json
      - performance_test_report.json
      - documentation_review_report.json
    output: final_review_report.json
    on_failure: escalate

# 质量标准
quality_standards:
  - name: 代码质量
    threshold: "良好"
    check: code_analysis_report.json.code_quality
  - name: 安全性
    threshold: "无高危漏洞"
    check: security_check_report.json.security_level
  - name: 性能
    threshold: "满足要求"
    check: performance_test_report.json.performance_score
  - name: 文档完整性
    threshold: "完整"
    check: documentation_review_report.json.documentation_completeness

# 安全检查项
security_checklist:
  - SQL注入
  - XSS攻击
  - CSRF攻击
  - 权限控制
  - 敏感信息泄露
  - 输入验证
  - 输出编码
  - 会话管理
  - 加密存储
  - 日志安全

# 性能检查项
performance_checklist:
  - 响应时间
  - 内存使用
  - CPU使用
  - 并发性能
  - 数据库查询效率
  - 缓存命中率
  - 网络IO
  - 磁盘IO

# 文档检查项
documentation_checklist:
  - 代码注释
  - README文档
  - API文档
  - 使用示例
  - 安装说明
  - 配置说明
  - 常见问题
  - 更新日志

# 输出格式
output_format:
  type: markdown
  sections:
    - title: 代码分析
      content: code_analysis
    - title: 安全检查
      content: security_check
    - title: 性能测试
      content: performance_test
    - title: 文档审查
      content: documentation_review
    - title: 最终审核
      content: final_review

# 通知配置
notifications:
  on_success:
    - type: feishu
      channel: user
      message: "代码审查通过，可以合并"
  on_failure:
    - type: feishu
      channel: user
      message: "代码审查失败，需要修改"
  on_review_failed:
    - type: feishu
      channel: user
      message: "代码审查未通过，需要修改后重新提交"

# 归档配置
archive:
  enabled: true
  destination: /Users/variya/.openclaw/workspace/Sentinel/ARCHIVE.md
  format: |
    ### TASK-CODE-REVIEW-{date}: 代码审查
    - 代码路径: {code_path}
    - 执行时间: {start_time} - {end_time}
    - 执行者: main
    - 结果: {result}
    - 审查意见: {review_comments}

# 重试策略
retry_policy:
  max_retries: 1
  backoff: fixed
  delay: 60  # 1分钟

# 超时策略
timeout_policy:
  step_timeout: 900  # 15分钟
  total_timeout: 3600  # 60分钟
  on_timeout: fail

# 失败处理
failure_handling:
  on_step_failure: retry
  on_all_retries_failed: fail
  fail_message: "代码审查失败，需要人工修改"

# 监控配置
monitoring:
  enabled: true
  metrics:
    - name: code_quality_score
      type: gauge
    - name: security_score
      type: gauge
    - name: performance_score
      type: gauge
    - name: documentation_score
      type: gauge

# 日志配置
logging:
  level: info
  format: json
  output: /Users/variya/.openclaw/workspace/Sentinel/logs/code-review-{date}.log
