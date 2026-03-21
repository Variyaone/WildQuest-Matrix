# 🚀 自主任务启动机制

**建立时间**: 2026-02-27 21:43
**目标**: 心跳循环自动发现并启动非T0任务，最大化并行效率

---

## 核心原则

> **不要等待！自主发现！立即启动！**

---

## 📊 项目任务自动发现规则

### A股量化项目

**当前状态**: Phase 1 完成 → Phase 2 待启动

**心跳检查规则**：
```
如果 Phase 1 完成 (6因子组合已生成)
    → 自动启动 Phase 2: 多因子回测验证
    → Agent: architect
```

**Phase 2 任务队列**：
1. 接入真实股价数据（AkShare）
2. 样本内回测（2023-2024）
3. 样本外回测（2025-2026）
4. 生成回测报告

---

### 资金费套利项目

**当前状态**: 研发完成 → 参数优化待启动

**心跳检查规则**：
```
如果 真实历史数据已获取
    → 自动启动: 基于真实数据的参数优化
    → Agent: researcher
```

**任务队列**：
1. 使用真实数据重新回测
2. 优化参数（阈值、仓位、风控）
3. 验证目标（年化>20%）
4. 生成优化报告

---

## 🔁 心跳循环新机制

### 每次心跳执行流程

```
1. 检查活跃任务
    ├─ 如果 >30分钟停滞 → 标记异常/重启
    └─ 如果 all done → 进入下一步

2. 项目状态扫描
    ├─ A股项目 → 检查Phase → 启动下一阶段
    ├─ 资金费套利 → 检查数据状态 → 启动优化
    └─ OKX模拟盘 → 检查运行状态 → 启动/报告

3. 任务发现与启动
    ├─ 识别可并行任务
    ├─ 选择合适的agent
    └─ 立即启动（不等待）

4. 资源管理
    ├─ 确保多个agents并行
    └─ 避免单agent串行

5. 汇报结果
    └─ 仅在关键节点汇报（成功/失败）
```

---

## 📋 心动决策表

| 检测条件 | 自动动作 | Agent | 说明 |
|---------|---------|-------|------|
| A股 Phase 1 完成（6因子） | 启动 Phase 2 | architect | 接入数据+回测 |
| A股 Phase 2 完成 | 启动 行业中性化优化 | architect | 剔除行业β |
| 真实资金费数据就绪 | 启动 参数优化 | researcher | 重新回测 |
| OKX模拟盘API就绪 | 启动 模拟盘测试 | architect | 2-3天运行 |
| 回测报告完成 | 启动 综合评估 | researcher | 风险收益分析 |
| 所有就绪 | 汇报 实盘建议 | main | T0决策 |

---

## 🚀 立即执行的待启动任务

### 1. A股项目回测验证（立即启动）
**Agent**: architect
**任务**: 多因子回测框架构建
**输入**: 6因子组合 + 实时数据接入

### 2. 资金费套利参数优化（立即启动）
**Agent**: researcher
**任务**: 基于真实数据优化年化至20%+
**输入**: BTC/ETH真实历史数据

### 3. OKX模拟盘监控（立即启动）
**Agent**: architect
**任务**: 状态监控 + 日志分析
**输入**: 模拟盘运行日志

---

## 💻 实施脚本

**文件**: `.commander/auto_task_launcher.py`

```python
class AutoTaskLauncher:
    def heartbeat_check(self):
        """心跳循环：自动发现并启动任务"""
        # 1. 检查项目状态
        a_stock_phase = check_a_stock_phase()
        funding_data_ready = check_funding_data()
        okx_sim_ready = check_okx_simulation()

        # 2. 根据状态启动任务
        if a_stock_phase == "phase1_complete":
            start_multi_factor_backtest(architect)

        if funding_data_ready:
            start_funding_rate_optimization(researcher)

        if okx_sim_ready:
            start_simulation_monitor(architect)
```

---

**立即生效！心跳循环现在会自动发现并启动任务！**

---
*由小龙虾指挥官建立*
