#!/bin/bash
#
# 部署Agent监控系统的脚本
#
# 功能：
# 1. 创建必要的目录结构
# 2. 设置cron jobs
# 3. 测试监控脚本
# 4. 生成部署报告
#
# 使用方法：
#   bash deploy_monitoring.sh [--uninstall]
#

set -e  # 遇到错误立即退出

# 配置
WORKSPACE="${WORKSPACE:-/Users/variya/.openclaw/workspace/.commander}"
PYTHON="${PYTHON:-python3}"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 打印分隔线
print_separator() {
    echo "================================================================================"
}

# 检查Python
check_python() {
    log_info "检查Python环境..."
    if ! command -v ${PYTHON} &> /dev/null; then
        log_error "未找到Python: ${PYTHON}"
        return 1
    fi
    PYTHON_VERSION=$(${PYTHON} --version)
    log_success "找到 ${PYTHON_VERSION}"
    return 0
}

# 创建目录结构
create_directories() {
    log_info "创建必要的目录结构..."

    DIRS=(
        "${WORKSPACE}"
        "${WORKSPACE}/task_state_backups"
        "${WORKSPACE}/work_logs"
        "${WORKSPACE}/team_tasks"
    )

    for dir in "${DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            mkdir -p "$dir"
            log_success "创建目录: $dir"
        else
            log_info "目录已存在: $dir"
        fi
    done
}

# 设置文件权限
set_permissions() {
    log_info "设置文件权限..."

    chmod +x "${WORKSPACE}/agent_health_monitor.py" 2>/dev/null || true
    chmod +x "${WORKSPACE}/task_timeout_handler.py" 2>/dev/null || true
    chmod +x "${WORKSPACE}/deploy_monitoring.sh" 2>/dev/null || true

    log_success "文件权限设置完成"
}

# 测试健康监控脚本
test_health_monitor() {
    log_info "测试Agent健康监控脚本..."

    if [ ! -f "${WORKSPACE}/agent_health_monitor.py" ]; then
        log_error "健康监控脚本不存在"
        return 1
    fi

    cd "${WORKSPACE}"
    if ${PYTHON} agent_health_monitor.py; then
        log_success "健康监控脚本测试通过"
        return 0
    else
        log_warning "健康监控脚本运行完成（有告警）"
        return 0
    fi
}

# 测试超时处理脚本
test_timeout_handler() {
    log_info "测试任务超时处理脚本..."

    if [ ! -f "${WORKSPACE}/task_timeout_handler.py" ]; then
        log_error "超时处理脚本不存在"
        return 1
    fi

    cd "${WORKSPACE}"
    # 使用dry-run模式测试
    if ${PYTHON} task_timeout_handler.py --dry-run; then
        log_success "超时处理脚本测试通过"
        return 0
    else
        log_warning "超时处理脚本运行完成（有超时任务）"
        return 0
    fi
}

# 安装cron jobs
install_cron_jobs() {
    log_info "安装cron jobs..."

    # 获取当前crontab
    CURRENT_CRON=$(crontab -l 2>/dev/null || true)

    # 检查是否已经安装
    if echo "$CURRENT_CRON" | grep -q "agent_health_monitor.py"; then
        log_warning "Cron jobs已经安装"
        return 0
    fi

    # 生成新的crontab
    NEW_CRON="$CURRENT_CRON

# Agent健康监控（每5分钟）
*/5 * * * * cd ${WORKSPACE} && ${PYTHON} agent_health_monitor.py --config agent_monitor_config.json >> monitoring_cron.log 2>&1

# 任务超时处理（每10分钟）
*/10 * * * * cd ${WORKSPACE} && ${PYTHON} task_timeout_handler.py --config agent_monitor_config.json >> timeout_cron.log 2>&1
"

    # 安装新的crontab
    echo "$NEW_CRON" | crontab -

    log_success "Cron jobs安装成功"

    # 显示安装的cron jobs
    log_info "安装的Cron Jobs:"
    echo "$NEW_CRON" | grep -A 2 "Agent" || true
}

# 卸载cron jobs
uninstall_cron_jobs() {
    log_info "卸载cron jobs..."

    # 获取当前crontab
    CURRENT_CRON=$(crontab -l 2>/dev/null || true)

    # 移除监控相关的cron jobs
    NEW_CRON=$(echo "$CURRENT_CRON" | grep -v "agent_health_monitor.py" | grep -v "task_timeout_handler.py")

    # 安装新的crontab
    echo "$NEW_CRON" | crontab -

    log_success "Cron jobs卸载成功"
}

# 生成部署报告
generate_report() {
    log_info "生成部署报告..."

    REPORT_FILE="${WORKSPACE}/DEPLOYMENT_REPORT.md"

    cat > "$REPORT_FILE" << 'EOF'
# 部署报告 - Agent监控系统

**部署时间**: DEPLOY_TIME
**部署环境**: DEPLOY_ENV

---

## ✅ 部署内容

### 1. 文件结构
- `agent_health_monitor.py` - Agent健康监控器
- `task_timeout_handler.py` - 任务超时处理器
- `agent_monitor_config.json` - 配置文件
- `deploy_monitoring.sh` - 部署脚本

### 2. 目录结构
- `task_state_backups/` - 任务状态备份
- `work_logs/` - 工作日志
- `team_tasks/` - 团队任务

### 3. Cron Jobs
```cron
# Agent健康监控（每5分钟）
*/5 * * * * cd /path/to/.commander && python3 agent_health_monitor.py...

# 任务超时处理（每10分钟）
*/10 * * * * cd /path/to/.commander && python3 task_timeout_handler.py...
```

---

## 📊 监控指标

### Agent健康
- 告警阈值: 6小时无活动
- 严重告警: 12小时无活动
- 超时阈值: 24小时无活动

### 任务超时
- 告警超时: 2小时
- 严重超时: 4小时
- 致命超时: 8小时

---

## 📁 日志文件

- `AGENT_HEALTH_REPORT.md` - 健康监控报告
- `AGENT_ALERTS.log` - 告警日志
- `TASK_TIMEOUT_REPORT.md` - 超时处理报告
- `TASK_TIMEOUTS.log` - 超时日志
- `monitoring_cron.log` - 监控cron日志
- `timeout_cron.log` - 超时处理cron日志

---

## 🔧 维护命令

### 查看cron jobs
```bash
crontab -l
```

### 编辑cron jobs
```bash
crontab -e
```

### 查看实时日志
```bash
tail -f monitoring_cron.log
tail -f timeout_cron.log
```

### 手动运行监控
```bash
cd /path/to/.commander
python3 agent_health_monitor.py
python3 task_timeout_handler.py
```

### 测试模式（不修改文件）
```bash
python3 task_timeout_handler.py --dry-run
```

---

## 🔄 升级和回滚

### 升级
1. 备份当前文件
2. 替换新版本脚本
3. 测试新脚本
4. 更新cron jobs（如果需要）

### 回滚
1. 停止cron jobs: `crontab -e` (删除相关行)
2. 恢复备份文件
3. 手动测试
4. 重新安装cron jobs

---

## 📞 支持

如遇到问题，请检查：
1. Python环境是否正常
2. TASK_STATE.json是否存在
3. 日志文件中的错误信息
4. Cron服务是否运行

EOF

    # 替换占位符
    sed -i '' "s/DEPLOY_TIME/$(date '+%Y-%m-%d %H:%M:%S')/" "$REPORT_FILE"
    sed -i '' "s|DEPLOY_ENV|${WORKSPACE}|" "$REPORT_FILE"

    log_success "部署报告已生成: $REPORT_FILE"
}

# 显示摘要
print_summary() {
    print_separator
    echo -e "${GREEN}部署完成！${NC}"
    print_separator
    echo ""
    echo "📊 部署摘要:"
    echo "  - 工作目录: ${WORKSPACE}"
    echo "  - Python: ${PYTHON_VERSION}"
    echo "  - 健康监控: agent_health_monitor.py"
    echo "  - 超时处理: task_timeout_handler.py"
    echo ""
    echo "📁 日志位置:"
    echo "  - 健康报告: ${WORKSPACE}/AGENT_HEALTH_REPORT.md"
    echo "  - 超时报告: ${WORKSPACE}/TASK_TIMEOUT_REPORT.md"
    echo "  - 告警日志: ${WORKSPACE}/AGENT_ALERTS.log"
    echo "  - 超时日志: ${WORKSPACE}/TASK_TIMEOUTS.log"
    echo ""
    echo "🔍 验证部署:"
    echo "  查看cron: crontab -l"
    echo "  测试监控: cd ${WORKSPACE} && ${PYTHON} agent_health_monitor.py"
    echo "  查看日志: tail -f ${WORKSPACE}/monitoring_cron.log"
    echo ""
    print_separator
}

# 主函数
main() {
    print_separator
    echo -e "${BLUE}Agent监控系统部署脚本${NC}"
    print_separator
    echo ""

    # 检查参数
    UNINSTALL=false
    if [[ "$1" == "--uninstall" ]]; then
        UNINSTALL=true
    fi

    # 卸载模式
    if [ "$UNINSTALL" = true ]; then
        log_info "卸载模式..."
        uninstall_cron_jobs
        log_success "卸载完成"
        echo ""
        echo "提示: 文件和目录保留，如需清理请手动删除"
        return 0
    fi

    # 检查Python
    check_python || exit 1
    echo ""

    # 创建目录
    create_directories
    echo ""

    # 设置权限
    set_permissions
    echo ""

    # 测试脚本
    test_health_monitor || log_warning "健康监控测试失败"
    echo ""
    test_timeout_handler || log_warning "超时处理测试失败"
    echo ""

    # 安装cron jobs
    install_cron_jobs
    echo ""

    # 生成报告
    generate_report
    echo ""

    # 显示摘要
    print_summary
}

# 运行主函数
main "$@"
