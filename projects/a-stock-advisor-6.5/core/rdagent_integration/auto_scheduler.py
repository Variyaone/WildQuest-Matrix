"""
Auto Search Scheduler

Automatically schedules and runs paper searches with smart keywords.
"""

import json
import schedule
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict
import subprocess
import sys


class AutoSearchScheduler:
    """自动搜索调度器"""
    
    def __init__(
        self,
        config_file: str = "auto_search_config.json",
        log_file: str = "auto_search.log",
    ):
        self.config_file = Path(config_file)
        self.log_file = Path(log_file)
        self.config = self._load_config()
        
        from .smart_search import SmartKeywordGenerator
        self.keyword_generator = SmartKeywordGenerator()
    
    def _load_config(self) -> Dict:
        default_config = {
            "enabled": True,
            "schedule": {
                "daily": {
                    "enabled": True,
                    "time": "09:00",
                    "strategy": "balanced",
                    "keyword_count": 5,
                    "max_papers": 10,
                },
                "weekly": {
                    "enabled": True,
                    "day": "monday",
                    "time": "08:00",
                    "strategy": "gap",
                    "keyword_count": 8,
                    "max_papers": 20,
                },
                "monthly": {
                    "enabled": True,
                    "day": 1,
                    "time": "07:00",
                    "strategy": "hot",
                    "keyword_count": 10,
                    "max_papers": 30,
                },
            },
            "focus_areas": ["value", "momentum", "quality"],
            "include_china": True,
            "auto_import": True,
            "notification": {
                "enabled": False,
                "webhook": "",
            },
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception:
                pass
        
        return default_config
    
    def _save_config(self):
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def _log(self, message: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        print(log_entry.strip())
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry)
    
    def run_search(
        self,
        keywords: Optional[List[str]] = None,
        strategy: str = "balanced",
        keyword_count: int = 5,
        max_papers: int = 10,
    ):
        """执行搜索"""
        if keywords is None:
            keywords = self.keyword_generator.generate_keywords(
                strategy=strategy,
                count=keyword_count,
                focus_areas=self.config.get("focus_areas"),
                include_china=self.config.get("include_china", True),
            )
        
        self._log(f"开始自动搜索，关键词: {', '.join(keywords)}")
        
        try:
            cmd = [
                sys.executable,
                "-m",
                "core.rdagent_integration.auto_mine",
                "auto",
                "--keywords",
            ] + keywords + [
                "--max-papers",
                str(max_papers),
                "--output-dir",
                "papers",
                "--output-file",
                "extracted_factors.json",
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
            )
            
            if result.returncode == 0:
                self._log("搜索完成")
                
                factors = self._extract_factors_count(result.stdout)
                
                self.keyword_generator.record_search(
                    keywords=keywords,
                    papers_found=max_papers,
                    papers_downloaded=max_papers,
                    factors_extracted=factors,
                )
                
                if self.config.get("auto_import"):
                    self._import_factors()
                
                self._send_notification(
                    title="自动搜索完成",
                    message=f"关键词: {', '.join(keywords)}\n提取因子: {factors}个",
                )
            else:
                self._log(f"搜索失败: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            self._log("搜索超时")
        except Exception as e:
            self._log(f"搜索出错: {e}")
    
    def _extract_factors_count(self, output: str) -> int:
        try:
            if "提取因子:" in output:
                line = [l for l in output.split("\n") if "提取因子:" in l][0]
                return int(line.split(":")[1].strip().split()[0])
        except Exception:
            pass
        return 0
    
    def _import_factors(self):
        try:
            cmd = [
                sys.executable,
                "-m",
                "core.factor.quick_entry",
                "--file",
                "extracted_factors.json",
            ]
            
            subprocess.run(cmd, capture_output=True, timeout=300)
            self._log("因子已导入因子库")
        except Exception as e:
            self._log(f"导入因子失败: {e}")
    
    def _send_notification(self, title: str, message: str):
        if not self.config.get("notification", {}).get("enabled"):
            return
        
        webhook = self.config.get("notification", {}).get("webhook")
        if not webhook:
            return
        
        try:
            import requests
            
            payload = {
                "msg_type": "text",
                "content": {
                    "text": f"{title}\n\n{message}"
                }
            }
            
            requests.post(webhook, json=payload, timeout=10)
        except Exception as e:
            self._log(f"发送通知失败: {e}")
    
    def setup_schedule(self):
        """设置定时任务"""
        schedule_config = self.config.get("schedule", {})
        
        if schedule_config.get("daily", {}).get("enabled"):
            daily = schedule_config["daily"]
            schedule.every().day.at(daily["time"]).do(
                self.run_search,
                strategy=daily["strategy"],
                keyword_count=daily["keyword_count"],
                max_papers=daily["max_papers"],
            )
            self._log(f"已设置每日搜索: {daily['time']}")
        
        if schedule_config.get("weekly", {}).get("enabled"):
            weekly = schedule_config["weekly"]
            day = weekly["day"].lower()
            
            scheduler = getattr(schedule.every(), day, None)
            if scheduler:
                scheduler.at(weekly["time"]).do(
                    self.run_search,
                    strategy=weekly["strategy"],
                    keyword_count=weekly["keyword_count"],
                    max_papers=weekly["max_papers"],
                )
                self._log(f"已设置每周搜索: {weekly['day']} {weekly['time']}")
        
        if schedule_config.get("monthly", {}).get("enabled"):
            monthly = schedule_config["monthly"]
            schedule.every().month.at(
                f"{monthly['day']} {monthly['time']}"
            ).do(
                self.run_search,
                strategy=monthly["strategy"],
                keyword_count=monthly["keyword_count"],
                max_papers=monthly["max_papers"],
            )
            self._log(f"已设置每月搜索: 每月{monthly['day']}日 {monthly['time']}")
    
    def run_daemon(self):
        """运行守护进程"""
        if not self.config.get("enabled"):
            self._log("自动搜索已禁用")
            return
        
        self.setup_schedule()
        
        self._log("自动搜索调度器已启动")
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def run_once(self, strategy: str = "balanced"):
        """执行一次搜索"""
        self.run_search(strategy=strategy)
    
    def show_performance(self):
        """显示搜索性能报告"""
        report = self.keyword_generator.get_keyword_performance_report()
        
        print("\n" + "=" * 60)
        print("搜索性能报告")
        print("=" * 60)
        print(f"总搜索次数: {report.get('total_searches', 0)}")
        print(f"唯一关键词: {report.get('unique_keywords', 0)}")
        
        if "top_performers" in report:
            print("\n最佳关键词:")
            for i, kw in enumerate(report["top_performers"][:5], 1):
                print(f"  [{i}] {kw['keyword']}: 成功率 {kw['success_rate']:.2%}, "
                      f"因子数 {kw['total_factors']}")
        
        if "low_performers" in report:
            print("\n低效关键词:")
            for i, kw in enumerate(report["low_performers"][:5], 1):
                print(f"  [{i}] {kw['keyword']}: 成功率 {kw['success_rate']:.2%}, "
                      f"因子数 {kw['total_factors']}")
        
        print("\n推荐关键词组合:")
        combinations = self.keyword_generator.get_recommended_combinations()
        for i, combo in enumerate(combinations[:3], 1):
            print(f"  [{i}] {', '.join(combo)}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="自动搜索调度器")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="运行守护进程",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="执行一次搜索",
    )
    parser.add_argument(
        "--strategy",
        type=str,
        default="balanced",
        choices=["balanced", "hot", "gap", "academic", "random"],
        help="搜索策略",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="显示性能报告",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        nargs="+",
        help="自定义关键词",
    )
    parser.add_argument(
        "--max-papers",
        type=int,
        default=10,
        help="最大论文数",
    )
    
    args = parser.parse_args()
    
    scheduler = AutoSearchScheduler()
    
    if args.daemon:
        scheduler.run_daemon()
    elif args.once:
        scheduler.run_search(
            keywords=args.keywords,
            strategy=args.strategy,
            max_papers=args.max_papers,
        )
    elif args.report:
        scheduler.show_performance()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
