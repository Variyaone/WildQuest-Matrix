# 文档生成工作流 - Lobster

name: doc-gen
description: 文档生成工作流，包括需求分析、内容撰写、格式检查、质量审核

# 工作目录
working_dir: /Users/variya/.openclaw/workspace

# 步骤定义
steps:
  # 步骤1: 需求分析
  - id: requirement_analysis
    name: 需求分析
    agent: researcher
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId researcher
      --task "分析文档需求，明确：目标读者、文档类型、内容范围、风格要求，输出需求分析报告"
      --mode run
    timeout: 600  # 10分钟
    input: user_requirement
    output: requirement_analysis_report.json
    on_failure: retry 1

  # 步骤2: 内容撰写
  - id: content_writing
    name: 内容撰写
    agent: creator
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId creator
      --task "基于需求分析报告，撰写文档内容，包括：标题、目录、正文、示例、图表，输出初稿"
      --mode run
    timeout: 1200  # 20分钟
    depends_on: requirement_analysis
    input: requirement_analysis_report.json
    output: content_draft.md
    on_failure: retry 2

  # 步骤3: 格式检查
  - id: format_check
    name: 格式检查
    agent: critic
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId critic
      --task "检查文档格式，包括：Markdown语法、标题层级、列表格式、代码块、链接、图片，输出格式检查报告"
      --mode run
    timeout: 600  # 10分钟
    depends_on: content_writing
    input: content_draft.md
    output: format_check_report.json
    on_failure: retry 1

  # 步骤4: 质量审核
  - id: quality_review
    name: 质量审核
    agent: critic
    command: >-
      openclaw sessions_spawn
      --runtime subagent
      --agentId critic
      --task "审核文档质量，包括：内容准确性、逻辑清晰性、语言表达、完整性，给出：通过/不通过/需要修改"
      --mode run
    timeout: 600  # 10分钟
    depends_on: format_check
    input:
      - content_draft.md
      - format_check_report.json
    output: quality_review_report.json
    on_failure: escalate

# 质量标准
quality_standards:
  - name: 内容准确性
    threshold: "准确"
    check: quality_review_report.json.accuracy
  - name: 逻辑清晰性
    threshold: "清晰"
    check: quality_review_report.json.logic_clarity
  - name: 语言表达
    threshold: "流畅"
    check: quality_review_report.json.language_quality
  - name: 完整性
    threshold: "完整"
    check: quality_review_report.json.completeness

# 文档类型
document_types:
  - type: 技术文档
    sections:
      - 概述
      - 安装
      - 配置
      - 使用
      - API
      - 示例
      - FAQ
  - type: 用户手册
    sections:
      - 简介
      - 快速开始
      - 功能说明
      - 操作指南
      - 常见问题
      - 联系方式
  - type: 设计文档
    sections:
      - 背景
      - 目标
      - 架构
      - 模块
      - 接口
      - 数据流
      - 扩展性
  - type: 测试文档
    sections:
      - 测试范围
      - 测试环境
      - 测试用例
      - 测试结果
      - 问题记录
      - 结论

# 格式检查项
format_checklist:
  - Markdown语法
  - 标题层级
  - 列表格式
  - 代码块
  - 链接有效性
  - 图片引用
  - 表格格式
  - 引用格式

# 质量检查项
quality_checklist:
  - 内容准确性
  - 逻辑清晰性
  - 语言表达
  - 完整性
  - 可读性
  - 实用性
  - 时效性

# 输出格式
output_format:
  type: markdown
  sections:
    - title: 标题
      content: title
    - title: 目录
      content: table_of_contents
    - title: 正文
      content: body
    - title: 示例
      content: examples
    - title: 附录
      content: appendix

# 通知配置
notifications:
  on_success:
    - type: feishu
      channel: user
      message: "文档生成完成，请查看结果"
  on_failure:
    - type: feishu
      channel: user
      message: "文档生成失败，请检查日志"
  on_review_failed:
    - type: feishu
      channel: user
      message: "文档质量审核未通过，需要修改"

# 归档配置
archive:
  enabled: true
  destination: /Users/variya/.openclaw/workspace/Sentinel/ARCHIVE.md
  format: |
    ### TASK-DOC-GEN-{date}: 文档生成
    - 文档类型: {document_type}
    - 执行时间: {start_time} - {end_time}
    - 执行者: main
    - 结果: {result}
    - 审查意见: {review_comments}

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
  on_all_retries_failed: fail
  fail_message: "文档生成失败，需要人工修改"

# 监控配置
monitoring:
  enabled: true
  metrics:
    - name: content_quality_score
      type: gauge
    - name: format_score
      type: gauge
    - name: writing_duration
      type: gauge
    - name: review_duration
      type: gauge

# 日志配置
logging:
  level: info
  format: json
  output: /Users/variya/.openclaw/workspace/Sentinel/logs/doc-gen-{date}.log
