# 🦞 心跳工作流 V3

## 锚定（每次必执行）

1. 读IDENTITY.md确认身份
2. 读SENTINEL_LOG.json确认模式（normal/maintenance/readonly）
3. **非normal模式立即返回**

---

## 🔁 Sentinel 10步心跳工作流

| 步骤 | 动作 |
|---|---|
| 1 自检 | 检查文件完整性、存储、JSON格式 |
| 2 T0监控 | 阻塞任务超时4小时二次提醒 |
| 3 输入 | 分析消息，生成任务写TASK_POOL.md |
| 4 压缩 | 对话>50轮或>10K token压缩摘要 |
| 5 领取 | 按优先级领取，检查负载和锁 |
| 6 执行 | 大任务原地分解 |
| 7 归档 | 更新状态，归档ARCHIVE.md，释放锁 |
| 8 探索 | 无P1任务时触发（延续/复盘/改进） |
| 9 清理 | 清理7天前任务 |
| 10 通知 | 按矩阵决策是否通知 |

---

## 核心检查

**Sentinel**: SENTINEL_LOG.json | LOCK_STATE.json | TASK_POOL.md

**A股**: portfolio_state.json | factor_dynamic_weights.json | selection_result.json

**🚨 新增T0级要求** (2026-03-19系统更新):
- **任务完成必须git提交** - 没有commit hash不算完成
- **任务必须原子化分解** - 每个任务 <5分钟，<200行代码
- **评审官默认怀疑态度** - 默认代码跑不通，必须实测验证


---

## 异常处理

| 异常 | 处理 |
|---|---|
| 任务停滞>2h | 重启或换agent |
| API限流 | 切换备用API |
| 推送失败 | 查日志重试 |
| 数据缺失 | 运行data_update_v2.py |
| 因子失效 | 查IC/IR，触发review |
| 模式异常 | 切readonly，通知用户 |

---

## 文件索引

TASK_POOL.md | REGISTRY.md | LOCK_STATE.json | SENTINEL_LOG.json | CONTEXT_SUMMARY.md | PATTERNS.md | ARCHIVE.md

---

## 规则

✅ 领任务前查锁 | 完成后释放锁归档 | 失败3次分析模式 | 空窗触发探索 | 长对话压缩

❌ readonly执行 | 跳锁检查 | 不归档 | 盲目重试

---

**间隔**: 30分钟（高峰15分钟）
