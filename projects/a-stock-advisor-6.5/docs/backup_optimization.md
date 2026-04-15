# 备份策略优化方案

## 问题分析

### 当前情况
- 磁盘使用率：81%（344G/460G）
- 可用空间：83G
- 每次daily备份：约287MB
- 保留策略：90天
- 预计空间需求：90 * 287MB = 25.8GB

### 问题
1. 每次全量备份，空间浪费严重
2. 保留90天太长，占用大量空间
3. 没有增量备份机制
4. 压缩率不够高

## 优化策略

### 1. 增量备份（每3天）
- **频率**：每3天一次
- **方式**：使用rsync硬链接实现增量备份
- **保留**：14天（约5个备份）
- **内容**：master、factors、signals
- **预计空间**：5 * 287MB = 1.4GB

### 2. 核心资产（每周）
- **频率**：每周一次
- **方式**：tar.xz高压缩
- **保留**：4周
- **内容**：因子库、策略库、组合配置
- **预计空间**：4 * 10MB = 40MB

### 3. 配置文件（每次变更）
- **频率**：每次变更时
- **方式**：tar.xz高压缩
- **保留**：5个版本
- **内容**：config.yaml、.env、requirements.txt
- **预计空间**：5 * 1MB = 5MB

### 4. 快照（每月）
- **频率**：每月一次
- **方式**：完整快照
- **保留**：3个月
- **内容**：完整数据目录
- **预计空间**：3 * 287MB = 861MB

## 空间对比

### 优化前
- Daily备份：90 * 287MB = 25.8GB
- Weekly备份：180天/7 * 287MB = 7.4GB
- Monthly备份：1095天/30 * 287MB = 10.5GB
- Core assets：永久保留（假设10个）= 2.9GB
- **总计**：约46.6GB

### 优化后
- 增量备份：1.4GB
- 核心资产：40MB
- 配置文件：5MB
- 快照：861MB
- **总计**：约2.3GB

**节省空间**：46.6GB - 2.3GB = 44.3GB（95%）

## 实施步骤

### 1. 备份当前数据
```bash
# 创建临时备份目录
mkdir -p /tmp/backup_migration

# 复制当前备份
cp -r /path/to/backups /tmp/backup_migration/
```

### 2. 清理旧备份
```bash
# 删除旧的daily备份（保留最近7天）
find /path/to/backups/daily -name "backup_daily_*.tar.gz" -mtime +7 -delete

# 删除旧的weekly备份（保留最近4周）
find /path/to/backups/weekly -name "backup_weekly_*.tar.gz" -mtime +28 -delete

# 删除旧的monthly备份（保留最近3个月）
find /path/to/backups/monthly -name "backup_monthly_*.tar.gz" -mtime +90 -delete
```

### 3. 启用新备份策略
```python
from core.daily.backup_optimized import OptimizedBackup

# 创建备份器
backup = OptimizedBackup()

# 执行增量备份
result = backup.backup_incremental()

# 执行核心资产备份
result = backup.backup_core_assets()

# 执行配置文件备份
result = backup.backup_config()

# 执行快照
result = backup.backup_snapshot()
```

### 4. 更新调度器
```python
# 修改scheduler.py中的备份任务
# 从每天一次改为每3天一次
# 添加每周核心资产备份任务
# 添加每月快照任务
```

## 风险评估

### 低风险
- 增量备份使用rsync硬链接，成熟稳定
- 保留14天足够应对大多数恢复场景
- 核心资产每周备份，数据安全有保障

### 中风险
- 需要测试rsync硬链接的兼容性
- 需要验证tar.xz的压缩效果
- 需要确保清理策略不会误删重要备份

### 缓解措施
1. 先在测试环境验证
2. 保留旧备份一段时间作为回退
3. 监控备份成功率和恢复测试

## 监控指标

### 备份成功率
- 目标：> 99%
- 监控：每次备份后检查success字段

### 备份大小
- 目标：增量备份 < 300MB
- 监控：backup_size字段

### 备份时间
- 目标：增量备份 < 5分钟
- 监控：duration_seconds字段

### 磁盘空间
- 目标：备份目录 < 3GB
- 监控：get_backup_stats()

## 回退方案

如果新策略出现问题，可以回退到旧策略：

```bash
# 恢复旧备份
cp -r /tmp/backup_migration/backups /path/to/

# 使用旧备份脚本
from core.daily.backup import DailyBackup
backup = DailyBackup()
result = backup.backup()
```

## 总结

优化后的备份策略：
- **节省空间**：95%（44.3GB）
- **备份频率**：更合理（增量3天，核心资产每周）
- **数据安全**：有保障（14天增量 + 4周核心资产 + 3个月快照）
- **实施风险**：低（使用成熟技术）

建议立即实施。
