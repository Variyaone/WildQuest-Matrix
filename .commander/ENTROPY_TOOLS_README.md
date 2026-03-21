# 🔧 系统熵值降低工具集

快速维护系统整洁度的自动化工具集。

---

## 📦 工具列表

### 1. check_entropy.py - 熵值检查工具

检查系统文件冗余、配置分散、低效问题。

**使用方法**:
```bash
cd /Users/variya/.openclaw/workspace/.commander
python3 check_entropy.py
```

**输出**:
- 熵值评分 (0-100，越高越乱)
- 文件冗余分析
- 健康报告检查
- 任务备份检查
- 配置重复检查
- OKX临时目录检查
- JSON格式报告保存至 `entropy_reports/`

**评分标准**:
- 0-20: 系统良好
- 20-40: 可选择性优化
- 40-70: 建议优化
- 70-100: 需要紧急优化

---

### 2. cleanup_system.py - 自动化清理脚本

根据规则自动清理冗余文件。

**使用方法**:

预览模式（不实际修改）:
```bash
python3 cleanup_system.py
```

执行清理:
```bash
python3 cleanup_system.py --apply
```

自定义配置:
```bash
python3 cleanup_system.py --apply \
  --keep-health-reports 10 \
  --keep-backups 24 \
  --cleanup-sessions-days 30
```

**功能**:
- 归档健康报告（保留指定数量）
- 归档任务状态备份（保留指定数量）
- 清理OKX临时目录（删除venv）
- 清理已删除会话（超过指定天数）
- 生成清理报告（JSON格式）

**参数**:
- `--apply`: 实际执行清理（默认预览模式）
- `--keep-health-reports N`: 保留的健康报告数量（默认5）
- `--keep-backups N`: 保留的任务备份数量（默认10）
- `--cleanup-sessions-days N`: 清理超过N天的已删除会话（默认7）
- `--no-health-reports`: 跳过健康报告清理
- `--no-backups`: 跳过任务备份清理
- `--no-okx-temp`: 跳过OKX临时目录清理
- `--no-sessions`: 跳过已删除会话清理

---

## 🔄 自动化定时任务

### Cron配置

```bash
# 编辑crontab
crontab -e

# 每周一早上5点：自动清理系统
0 5 * * 1 cd /Users/variya/.openclaw/workspace/.commander && python3 cleanup_system.py --apply >> cleanup_weekly.log 2>&1

# 每周一早上9点：系统熵值检查
0 9 * * 1 cd /Users/variya/.openclaw/workspace/.commander && python3 check_entropy.py >> entropy_check_weekly.log 2>&1

# 每天凌晨2点：清理过期会话（>30天）
0 2 * * * cd /Users/variya/.openclaw/workspace/.commander && python3 cleanup_system.py --cleanup-sessions-days 30 --apply --no-health-reports --no-backups --no-okx-temp >> cleanup_daily.log 2>&1
```

---

## 📁 目录结构

```
.commander/
├── check_entropy.py                    # 熵值检查脚本
├── cleanup_system.py                   # 自动化清理脚本
├── entropy_reports/                    # 熵值检查报告
│   └── entropy_report_YYYYMMDD_HHMMSS.json
├── cleanup_reports/                    # 清理执行报告（执行后生成）
│   └── cleanup_report_YYYYMMDD_HHMMSS.json
├── archive/                            # 归档目录
│   ├── health_reports/
│   │   └── YYYY-MM-DD/
│   └── task_state_backups/
│       └── YYYY-MM-DD/
└── ENTROPY_TOOLS_README.md             # 本文档
```

---

## 💡 使用建议

### 日常维护
- 每周手动运行一次熵值检查：`python3 check_entropy.py`
- 每月查看清理报告：`cat cleanup_reports/*.json`

### 定期清理
- 配置Cron任务，每周自动清理
- 每月检查归档目录大小
- 每季度清理过期归档（>90天）

### 调整策略
- 根据实际情况调整保留数量
- 根据存储空间调整清理频率
- 根据使用习惯调整清理规则

---

## ⚙️ 配置调整

### 保守策略（保留更多）
```bash
python3 cleanup_system.py --apply \
  --keep-health-reports 24 \
  --keep-backups 48 \
  --cleanup-sessions-days 30
```

### 稳定策略（推荐，默认）
```bash
python3 cleanup_system.py --apply \
  --keep-health-reports 5 \
  --keep-backups 10 \
  --cleanup-sessions-days 7
```

### 激进策略（保留最少）
```bash
python3 cleanup_system.py --apply \
  --keep-health-reports 3 \
  --keep-backups 5 \
  --cleanup-sessions-days 3
```

---

## 📊 常见问题

### Q: 清理后数据丢失怎么办？
A: 所有清理的文件都归档在 `archive/` 目录中，随时可以恢复。

### Q: 如何查看清理历史？
A: 查看 `cleanup_reports/` 目录中的JSON报告。

### Q: 如何恢复归档的文件？
A: 从 `archive/` 相应目录复制文件回原位置即可。

### Q: 熵值检查分数高了怎么办？
A: 运行 `python3 cleanup_system.py --apply` 进行清理，然后重新检查。

---

## 🔗 相关文档

- `SYSTEM_ENTROPY_DIAGNOSIS.md` - 诊断报告
- `CLEANUP_EXECUTION_REPORT.md` - 执行报告
- `SYSTEM_OPTIMIZATION_SUMMARY.md` - 优化总结
- `CLEANUP_RULES.md` - 详细清理规则

---

**维护者**: Innovator
**版本**: 1.0
**更新时间**: 2026-02-27
