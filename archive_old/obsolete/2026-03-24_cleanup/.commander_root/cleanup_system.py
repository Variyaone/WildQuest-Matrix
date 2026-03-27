#!/usr/bin/env python3
"""
自动化系统清理脚本
根据规则自动清理冗余文件
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
from argparse import ArgumentParser

# 配置
WORKSPACE = Path("/Users/variya/.openclaw/workspace")
COMMANDER_DIR = WORKSPACE / ".commander"
ARCHIVE_DIR = COMMANDER_DIR / "archive"

# 颜色输出
class Colors:
    RED = '\033[91m'
    YELLOW = '\033[93m'
    GREEN = '\033[92m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")

def check_age(file_path, days=7):
    """检查文件年龄是否超过指定天数"""
    if not file_path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
    return age.days >= days

def cleanup_health_reports(apply=False, keep=5):
    """清理健康报告"""
    print_header("🦞 清理健康报告")

    health_reports_dir = COMMANDER_DIR / "health_reports"
    if not health_reports_dir.exists():
        print_info("健康报告目录不存在")
        return 0, 0

    reports = sorted(health_reports_dir.glob("AGENT_HEALTH_REPORT_*.md"),
                    key=lambda p: p.stat().st_mtime, reverse=True)

    if len(reports) <= keep:
        print_success(f"健康报告数量正常: {len(reports)} 个")
        return 0, 0

    # 需要归档的报告
    to_archive = reports[keep:]

    print_info(f"保留最新: {keep} 个报告")
    print_info(f"归档旧报告: {len(to_archive)} 个")

    if not apply:
        print_warning("预览模式：未执行实际操作（使用 --apply 应用更改）")
        for report in to_archive[:5]:
            print(f"  - {report.name}")
        if len(to_archive) > 5:
            print(f"  ... 还有 {len(to_archive) - 5} 个")
        return len(to_archive), 0

    # 创建归档目录
    today = datetime.now().strftime("%Y-%m-%d")
    archive_subdir = ARCHIVE_DIR / "health_reports" / today
    archive_subdir.mkdir(parents=True, exist_ok=True)

    # 归档报告
    archived_count = 0
    for report in to_archive:
        try:
            shutil.move(str(report), str(archive_subdir / report.name))
            archived_count += 1
        except Exception as e:
            print_error(f"归档失败 {report.name}: {e}")

    print_success(f"已归档: {archived_count} 个健康报告")

    return archived_count, 0

def cleanup_task_state_backups(apply=False, keep=10):
    """清理任务状态备份"""
    print_header("💾 清理任务状态备份")

    backup_dir = COMMANDER_DIR / "task_state_backups"
    if not backup_dir.exists():
        print_info("任务状态备份目录不存在")
        return 0, 0

    backups = sorted(backup_dir.glob("TASK_STATE_*.json"),
                    key=lambda p: p.stat().st_mtime, reverse=True)

    if len(backups) <= keep:
        print_success(f"任务备份数量正常: {len(backups)} 个")
        return 0, 0

    # 需要归档的备份
    to_archive = backups[keep:]

    print_info(f"保留最新: {keep} 个备份")
    print_info(f"归档旧备份: {len(to_archive)} 个")

    if not apply:
        print_warning("预览模式：未执行实际操作（使用 --apply 应用更改）")
        for backup in to_archive[:5]:
            print(f"  - {backup.name}")
        if len(to_archive) > 5:
            print(f"  ... 还有 {len(to_archive) - 5} 个")
        return len(to_archive), 0

    # 创建归档目录
    today = datetime.now().strftime("%Y-%m-%d")
    archive_subdir = ARCHIVE_DIR / "task_state_backups" / today
    archive_subdir.mkdir(parents=True, exist_ok=True)

    # 归档备份
    archived_count = 0
    for backup in to_archive:
        try:
            shutil.move(str(backup), str(archive_subdir / backup.name))
            archived_count += 1
        except Exception as e:
            print_error(f"归档失败 {backup.name}: {e}")

    print_success(f"已归档: {archived_count} 个任务备份")

    return archived_count, 0

def cleanup_okx_temp(apply=False):
    """清理OKX临时目录"""
    print_header("📂 清理OKX临时目录")

    okx_temp = WORKSPACE / "okx-temp"

    if not okx_temp.exists():
        # 检查是否已归档
        archived_okx = WORKSPACE / "archive"
        if archived_okx.exists():
            okx_archives = list(archived_okx.glob("okx-temp-archive-*"))
            if okx_archives:
                print_success(f"OKX临时目录已归档: {len(okx_archives)} 个归档")
                return 0, 1
        print_info("OKX临时目录不存在（已清理或不存在）")
        return 0, 0

    # 检查venv目录
    venv_dir = okx_temp / "venv"
    venv_size = 0
    if venv_dir.exists():
        venv_size = sum(f.stat().st_size for f in venv_dir.rglob("*") if f.is_file())
        venv_mb = venv_size / (1024 * 1024)
        print_warning(f"发现venv目录: {venv_mb:.1f} MB")

    # 归档整个okx-temp目录
    if not apply:
        print_warning("预览模式：未执行实际操作（使用 --apply 应用更改）")
        print("  - 归档 okx-temp/ 到 archive/okx-temp-archive-YYYYMMDD/")
        print("  - 删除 venv/ 目录")
        return 1, 0

    # 创建归档目录
    today = datetime.now().strftime("%Y%m%d")
    archive_okx = WORKSPACE / "archive" / f"okx-temp-archive-{today}"

    # 移动整个目录
    try:
        shutil.move(str(okx_temp), str(archive_okx))
        print_success(f"已归档: okx-temp/ → archive/okx-temp-archive-{today}/")
    except Exception as e:
        print_error(f"归档失败: {e}")
        return 0, 0

    # 删除venv目录
    if venv_dir.exists():
        try:
            shutil.rmtree(archive_okx / "venv")
            print_success(f"已删除venv目录: 释放 {venv_mb:.1f} MBB")
        except Exception as e:
            print_error(f"删除venv失败: {e}")

    return 1, 1

def cleanup_deleted_sessions(apply=False, days=7):
    """清理已删除的会话"""
    print_header("🗑️  清理已删除会话")

    agents_dir = WORKSPACE.parent / "agents"
    if not agents_dir.exists():
        print_info("agents目录不存在")
        return 0, 0

    # 查找所有.deleted.* 文件
    deleted_sessions = []
    for agent_dir in agents_dir.iterdir():
        if agent_dir.is_dir():
            sessions_dir = agent_dir / "sessions"
            if sessions_dir.exists():
                deleted_sessions.extend(
                    f for f in sessions_dir.glob("*.deleted.*")
                    if check_age(f, days)
                )

    if not deleted_sessions:
        print_success(f"未发现过期的已删除会话（>{days}天）")
        return 0, 0

    print_info(f"发现过期已删除会话: {len(deleted_sessions)} 个")

    if not apply:
        print_warning("预览模式：未执行实际操作（使用 --apply 应用更改）")
        for session in deleted_sessions[:5]:
            print(f"  - {session.relative_to(agents_dir)}")
        if len(deleted_sessions) > 5:
            print(f"  ... 还有 {len(deleted_sessions) - 5} 个")
        return len(deleted_sessions), 0

    # 创建备份目录
    backup_dir = ARCHIVE_DIR / "deleted_sessions"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # 备份并删除
    deleted_count = 0
    for session in deleted_sessions:
        try:
            # 备份
            backup_path = backup_dir / session.name
            shutil.copy2(session, backup_path)

            # 删除原文件
            session.unlink()
            deleted_count += 1
        except Exception as e:
            print_error(f"清理失败 {session.name}: {e}")

    print_success(f"已清理: {deleted_count} 个过期已删除会话")

    return deleted_count, 0

def generate_report(actions, archived_count, deleted_count):
    """生成清理报告"""
    header = "\n"
    header += f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n"
    header += f"{Colors.BOLD}{Colors.GREEN}📊 清理报告{Colors.RESET}\n"
    header += f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n"

    summary = "\n"
    summary += f"清理时间: {datetime.now():%Y-%m-%d %H:%M:%S}\n"
    summary += f"操作模式: {'执行清理' if apply else '预览模式'}\n"

    actions_report = "\n📝 操作列表:\n"
    for action in actions:
        actions_report += f"  - {action}\n"

    stats_report = "\n📈 清理统计:\n"
    stats_report += f"  - 归档文件: {archived_count} 个\n"
    stats_report += f"  - 删除文件: {deleted_count} 个\n"
    stats_report += f"  - 总计: {archived_count + deleted_count} 个文件\n"

    footer = "\n"
    footer += f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n"
    footer += f"{Colors.BOLD}{Colors.GREEN}✨ 清理完成{Colors.RESET}\n"
    footer += f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n"

    return header + summary + actions_report + stats_report + footer

def main():
    parser = ArgumentParser(description="自动化系统清理脚本")
    parser.add_argument("--apply", action="store_true", help="实际执行清理操作")
    parser.add_argument("--keep-health-reports", type=int, default=5, help="保留的健康报告数量")
    parser.add_argument("--keep-backups", type=int, default=10, help="保留的任务备份数量")
    parser.add_argument("--cleanup-sessions-days", type=int, default=7, help="清理超过N天的已删除会话")
    parser.add_argument("--no-health-reports", action="store_true", help="跳过健康报告清理")
    parser.add_argument("--no-backups", action="store_true", help="跳过任务备份清理")
    parser.add_argument("--no-okx-temp", action="store_true", help="跳过OKX临时目录清理")
    parser.add_argument("--no-sessions", action="store_true", help="跳过已删除会话清理")

    args = parser.parse_args()
    global apply
    apply = args.apply

    print(f"\n{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}🧹 自动化系统清理工具{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.GREEN}{'='*60}{Colors.RESET}\n")

    print_info(f"工作目录: {WORKSPACE}")
    print_info(f"清理模式: {'执行清理' if apply else '预览模式'}")
    if not apply:
        print_warning("预览模式：不会对系统产生实际修改")
    print("")

    actions = []
    archived_total = 0
    deleted_total = 0

    # 清理健康报告
    if not args.no_health_reports:
        archived, deleted = cleanup_health_reports(apply, args.keep_health_reports)
        if archived > 0:
            actions.append(f"归档健康报告: {archived} 个")
            archived_total += archived

    # 清理任务状态备份
    if not args.no_backups:
        archived, deleted = cleanup_task_state_backups(apply, args.keep_backups)
        if archived > 0:
            actions.append(f"归档任务备份: {archived} 个")
            archived_total += archived

    # 清理OKX临时目录
    if not args.no_okx_temp:
        archived, deleted = cleanup_okx_temp(apply)
        if deleted > 0:
            actions.append(f"清理OKX临时目录: 删除venv")

    # 清理已删除会话
    if not args.no_sessions:
        archived, deleted = cleanup_deleted_sessions(apply, args.cleanup_sessions_days)
        if deleted > 0:
            actions.append(f"清理已删除会话: {deleted} 个")
            deleted_total += deleted

    # 生成报告
    print(generate_report(actions, archived_total, deleted_total))

    # 保存报告
    if apply:
        report_dir = COMMANDER_DIR / "cleanup_reports"
        report_dir.mkdir(exist_ok=True)

        report_file = report_dir / f"cleanup_report_{datetime.now():%Y%m%d_%H%M%S}.json"
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "archived_count": archived_total,
            "deleted_count": deleted_total,
            "actions": actions
        }
        with open(report_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print_success(f"报告已保存: {report_file}")

    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())
