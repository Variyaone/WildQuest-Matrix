"""
Smart Keyword Generator for Paper Search

Automatically generates optimal search keywords based on:
1. Market trends and hot topics
2. Factor library gaps
3. Academic research trends
4. User preferences and history
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import Counter


@dataclass
class KeywordCategory:
    name: str
    keywords: List[str]
    weight: float = 1.0
    last_used: Optional[datetime] = None
    success_rate: float = 0.5


class SmartKeywordGenerator:
    """智能关键词生成器"""
    
    MARKET_TRENDS = {
        "hot_2026": [
            "AI factor investing",
            "machine learning alpha",
            "deep learning stock prediction",
            "LLM financial analysis",
            "transformer time series",
            "reinforcement learning trading",
            "alternative data factor",
            "ESG factor investing",
            "climate risk factor",
            "sentiment analysis factor",
        ],
        "emerging": [
            "quantum finance",
            "graph neural network stock",
            "attention mechanism factor",
            "multi-modal financial data",
            "federated learning finance",
            "explainable AI factor",
            "causal inference factor",
            "factor timing strategy",
            "dynamic factor model",
            "adaptive factor selection",
        ],
    }
    
    FACTOR_TYPES = {
        "value": [
            "value factor",
            "book to market",
            "earnings yield",
            "cash flow yield",
            "dividend yield",
            "PE ratio factor",
            "PB ratio factor",
        ],
        "momentum": [
            "momentum factor",
            "price momentum",
            "earnings momentum",
            "industry momentum",
            "residual momentum",
            "time series momentum",
            "cross-sectional momentum",
        ],
        "quality": [
            "quality factor",
            "profitability factor",
            "ROE factor",
            "ROA factor",
            "accruals factor",
            "earnings quality",
            "financial strength",
        ],
        "low_volatility": [
            "low volatility factor",
            "minimum variance",
            "volatility anomaly",
            "beta factor",
            "idiosyncratic volatility",
        ],
        "size": [
            "size factor",
            "small cap premium",
            "market capitalization factor",
            "SMB factor",
        ],
        "liquidity": [
            "liquidity factor",
            "turnover factor",
            "bid-ask spread factor",
            "amihud illiquidity",
            "trading volume factor",
        ],
        "sentiment": [
            "sentiment factor",
            "investor sentiment",
            "analyst sentiment",
            "news sentiment factor",
            "social media factor",
        ],
        "technical": [
            "technical factor",
            "RSI factor",
            "MACD factor",
            "moving average factor",
            "Bollinger bands factor",
            "volume factor",
        ],
    }
    
    CHINA_SPECIFIC = [
        "China A-share factor",
        "Chinese stock market",
        "A-share anomaly",
        "China factor model",
        "Shanghai Shenzhen factor",
        "Chinese investor behavior",
        "China market microstructure",
        "A-share momentum",
        "China value premium",
        "Chinese institutional investor",
    ]
    
    ACADEMIC_FRONTIERS = [
        "factor zoo",
        "factor replication",
        "factor decay",
        "factor crowding",
        "factor timing",
        "factor combination",
        "factor selection",
        "factor robustness",
        "factor out-of-sample",
        "p-hacking factor",
        "multiple testing factor",
        "factor publication bias",
    ]
    
    def __init__(self, history_file: str = "search_history.json"):
        self.history_file = Path(history_file)
        self.search_history = self._load_history()
        self.keyword_stats = self._load_stats()
    
    def _load_history(self) -> List[Dict]:
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def _save_history(self):
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(self.search_history[-100:], f, ensure_ascii=False, indent=2)
    
    def _load_stats(self) -> Dict:
        stats_file = self.history_file.parent / "keyword_stats.json"
        if stats_file.exists():
            try:
                with open(stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}
    
    def _save_stats(self):
        stats_file = self.history_file.parent / "keyword_stats.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.keyword_stats, f, ensure_ascii=False, indent=2)
    
    def record_search(
        self,
        keywords: List[str],
        papers_found: int,
        papers_downloaded: int,
        factors_extracted: int,
    ):
        record = {
            "timestamp": datetime.now().isoformat(),
            "keywords": keywords,
            "papers_found": papers_found,
            "papers_downloaded": papers_downloaded,
            "factors_extracted": factors_extracted,
            "success_rate": factors_extracted / max(papers_downloaded, 1),
        }
        
        self.search_history.append(record)
        self._save_history()
        
        for kw in keywords:
            if kw not in self.keyword_stats:
                self.keyword_stats[kw] = {
                    "total_searches": 0,
                    "total_papers": 0,
                    "total_factors": 0,
                    "avg_success_rate": 0.0,
                }
            
            stats = self.keyword_stats[kw]
            stats["total_searches"] += 1
            stats["total_papers"] += papers_found
            stats["total_factors"] += factors_extracted
            stats["avg_success_rate"] = (
                stats["avg_success_rate"] * (stats["total_searches"] - 1) + record["success_rate"]
            ) / stats["total_searches"]
        
        self._save_stats()
    
    def generate_keywords(
        self,
        strategy: str = "balanced",
        count: int = 5,
        focus_areas: Optional[List[str]] = None,
        include_china: bool = True,
        prefer_recent: bool = True,
    ) -> List[str]:
        """
        生成搜索关键词
        
        Args:
            strategy: 生成策略
                - "balanced": 平衡各类因子
                - "hot": 聚焦市场热点
                - "gap": 填补因子库缺口
                - "academic": 学术前沿
                - "random": 随机组合
            count: 关键词数量
            focus_areas: 重点关注的因子类型
            include_china: 是否包含中国市场关键词
            prefer_recent: 是否偏好最近未使用的关键词
        
        Returns:
            关键词列表
        """
        keywords = []
        
        if strategy == "hot":
            keywords = self._generate_hot_keywords(count, include_china)
        elif strategy == "gap":
            keywords = self._generate_gap_keywords(count, focus_areas)
        elif strategy == "academic":
            keywords = self._generate_academic_keywords(count)
        elif strategy == "random":
            keywords = self._generate_random_keywords(count, include_china)
        else:
            keywords = self._generate_balanced_keywords(count, focus_areas, include_china)
        
        if prefer_recent:
            keywords = self._prefer_unused_keywords(keywords, count)
        
        return keywords[:count]
    
    def _generate_hot_keywords(self, count: int, include_china: bool) -> List[str]:
        hot = self.MARKET_TRENDS["hot_2026"].copy()
        emerging = self.MARKET_TRENDS["emerging"].copy()
        
        keywords = random.sample(hot, min(3, count))
        
        if include_china and len(keywords) < count:
            china_hot = [f"{kw} China" for kw in keywords[:2]]
            keywords.extend(china_hot[:count - len(keywords)])
        
        if len(keywords) < count:
            keywords.extend(random.sample(emerging, count - len(keywords)))
        
        return keywords
    
    def _generate_gap_keywords(
        self,
        count: int,
        focus_areas: Optional[List[str]],
    ) -> List[str]:
        if focus_areas is None:
            focus_areas = list(self.FACTOR_TYPES.keys())
        
        gap_keywords = []
        
        for area in focus_areas:
            if area in self.FACTOR_TYPES:
                area_keywords = self.FACTOR_TYPES[area]
                
                unused = [
                    kw for kw in area_keywords
                    if kw not in self.keyword_stats or 
                    self.keyword_stats[kw]["total_searches"] < 2
                ]
                
                if unused:
                    gap_keywords.extend(random.sample(unused, min(2, len(unused))))
        
        if len(gap_keywords) < count:
            all_keywords = []
            for kws in self.FACTOR_TYPES.values():
                all_keywords.extend(kws)
            
            remaining = [kw for kw in all_keywords if kw not in gap_keywords]
            gap_keywords.extend(random.sample(remaining, count - len(gap_keywords)))
        
        return gap_keywords[:count]
    
    def _generate_academic_keywords(self, count: int) -> List[str]:
        keywords = random.sample(self.ACADEMIC_FRONTIERS, min(3, count))
        
        if len(keywords) < count:
            all_factor_keywords = []
            for kws in self.FACTOR_TYPES.values():
                all_factor_keywords.extend(kws)
            
            keywords.extend(random.sample(all_factor_keywords, count - len(keywords)))
        
        return keywords
    
    def _generate_random_keywords(self, count: int, include_china: bool) -> List[str]:
        all_keywords = []
        
        for kws in self.FACTOR_TYPES.values():
            all_keywords.extend(kws)
        
        all_keywords.extend(self.MARKET_TRENDS["hot_2026"])
        all_keywords.extend(self.ACADEMIC_FRONTIERS)
        
        if include_china:
            all_keywords.extend(self.CHINA_SPECIFIC)
        
        return random.sample(all_keywords, min(count, len(all_keywords)))
    
    def _generate_balanced_keywords(
        self,
        count: int,
        focus_areas: Optional[List[str]],
        include_china: bool,
    ) -> List[str]:
        keywords = []
        
        if focus_areas:
            for area in focus_areas[:2]:
                if area in self.FACTOR_TYPES:
                    area_kw = random.choice(self.FACTOR_TYPES[area])
                    keywords.append(area_kw)
        else:
            random_areas = random.sample(list(self.FACTOR_TYPES.keys()), min(2, count))
            for area in random_areas:
                keywords.append(random.choice(self.FACTOR_TYPES[area]))
        
        if len(keywords) < count:
            hot_kw = random.choice(self.MARKET_TRENDS["hot_2026"])
            keywords.append(hot_kw)
        
        if len(keywords) < count:
            academic_kw = random.choice(self.ACADEMIC_FRONTIERS)
            keywords.append(academic_kw)
        
        if include_china and len(keywords) < count:
            china_kw = random.choice(self.CHINA_SPECIFIC)
            keywords.append(china_kw)
        
        return keywords
    
    def _prefer_unused_keywords(self, keywords: List[str], count: int) -> List[str]:
        recent_used = set()
        
        for record in self.search_history[-20:]:
            recent_used.update(record.get("keywords", []))
        
        unused = [kw for kw in keywords if kw not in recent_used]
        used = [kw for kw in keywords if kw in recent_used]
        
        return unused + used
    
    def get_recommended_combinations(self) -> List[List[str]]:
        combinations = [
            ["value factor", "momentum factor", "China A-share"],
            ["machine learning alpha", "factor selection", "stock prediction"],
            ["ESG factor", "quality factor", "sustainability"],
            ["sentiment factor", "alternative data", "news analysis"],
            ["low volatility factor", "risk factor", "portfolio optimization"],
            ["factor timing", "factor decay", "dynamic factor"],
            ["liquidity factor", "market microstructure", "trading cost"],
            ["earnings momentum", "analyst forecast", "earnings surprise"],
        ]
        
        scored_combinations = []
        for combo in combinations:
            avg_success = 0.0
            for kw in combo:
                if kw in self.keyword_stats:
                    avg_success += self.keyword_stats[kw]["avg_success_rate"]
            avg_success /= len(combo)
            
            recent_use = any(
                kw in record.get("keywords", [])
                for record in self.search_history[-10:]
                for kw in combo
            )
            
            score = avg_success * (0.5 if recent_use else 1.0)
            scored_combinations.append((combo, score))
        
        scored_combinations.sort(key=lambda x: x[1], reverse=True)
        
        return [combo for combo, score in scored_combinations[:5]]
    
    def get_keyword_performance_report(self) -> Dict:
        if not self.keyword_stats:
            return {"message": "暂无搜索历史数据"}
        
        sorted_keywords = sorted(
            self.keyword_stats.items(),
            key=lambda x: x[1]["avg_success_rate"],
            reverse=True,
        )
        
        top_performers = sorted_keywords[:10]
        low_performers = sorted_keywords[-10:]
        
        return {
            "total_searches": len(self.search_history),
            "unique_keywords": len(self.keyword_stats),
            "top_performers": [
                {
                    "keyword": kw,
                    "success_rate": stats["avg_success_rate"],
                    "total_factors": stats["total_factors"],
                }
                for kw, stats in top_performers
            ],
            "low_performers": [
                {
                    "keyword": kw,
                    "success_rate": stats["avg_success_rate"],
                    "total_factors": stats["total_factors"],
                }
                for kw, stats in low_performers
            ],
        }
