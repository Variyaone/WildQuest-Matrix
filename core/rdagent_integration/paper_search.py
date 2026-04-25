"""
Paper Search Module

Automatically search academic papers from arXiv, Semantic Scholar, etc.
"""

import os
import requests
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import time
import json
import random


@dataclass
class PaperInfo:
    title: str
    authors: List[str]
    abstract: str
    url: str
    pdf_url: str
    published_date: str
    categories: List[str]
    citation_count: Optional[int] = None
    relevance_score: Optional[float] = None
    doi: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "published_date": self.published_date,
            "categories": self.categories,
            "citation_count": self.citation_count,
            "relevance_score": self.relevance_score,
            "doi": self.doi,
        }


class ProcessedPapersTracker:
    """已处理论文追踪器"""
    
    def __init__(self, tracker_file: str = "processed_papers.json"):
        self.tracker_file = Path(tracker_file)
        self.processed_papers = self._load()
    
    def _load(self) -> dict:
        """加载已处理论文记录"""
        if self.tracker_file.exists():
            try:
                with open(self.tracker_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"processed_urls": {}, "processed_titles": {}}
    
    def save(self):
        """保存记录"""
        with open(self.tracker_file, "w", encoding="utf-8") as f:
            json.dump(self.processed_papers, f, ensure_ascii=False, indent=2)
    
    def is_processed(self, paper_url: str = None, paper_title: str = None) -> bool:
        """检查论文是否已处理"""
        if paper_url and paper_url in self.processed_papers.get("processed_urls", {}):
            return True
        if paper_title and paper_title in self.processed_papers.get("processed_titles", {}):
            return True
        return False
    
    def mark_processed(self, paper_url: str, paper_title: str, factors_count: int = 0):
        """标记论文为已处理"""
        self.processed_papers["processed_urls"][paper_url] = {
            "title": paper_title,
            "factors_count": factors_count,
            "processed_at": datetime.now().isoformat()
        }
        self.processed_papers["processed_titles"][paper_title] = {
            "url": paper_url,
            "factors_count": factors_count,
            "processed_at": datetime.now().isoformat()
        }
        self.save()
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            "total_processed": len(self.processed_papers.get("processed_urls", {})),
            "last_processed": max(
                [v.get("processed_at", "") for v in self.processed_papers.get("processed_urls", {}).values()],
                default="从未"
            )
        }


class ArxivSearcher:
    """arXiv论文搜索器"""
    
    QUANT_KEYWORDS = [
        "quantitative finance",
        "factor investing",
        "stock prediction",
        "portfolio optimization",
        "alpha factor",
        "momentum factor",
        "value factor",
        "technical indicator",
        "trading strategy",
        "market prediction",
        "financial machine learning",
        "time series forecasting",
        "stock return",
        "asset pricing",
        "risk factor",
        "size factor",
        "quality factor",
        "low volatility",
        "dividend yield",
        "earnings momentum",
        "price momentum",
        "industry momentum",
        "cross-sectional",
        "panel data",
        "event study",
        "anomaly detection",
        "market microstructure",
        "order flow",
        "liquidity",
        "bid-ask spread",
        "market impact",
        "transaction cost",
        "execution algorithm",
        "smart beta",
        "factor timing",
        "factor rotation",
        "multi-factor model",
        "risk parity",
        "black-litterman",
        "mean-variance optimization",
        "efficient frontier",
        "CAPM",
        "Fama French",
        "Carhart four factor",
        "q-factor model",
        "behavioral finance",
        "investor sentiment",
        "herding behavior",
        "overreaction",
        "underreaction",
        "information asymmetry",
        "institutional investor",
        "mutual fund",
        "hedge fund",
        "activist investor",
        "short selling",
        "options strategy",
        "volatility trading",
        "derivatives pricing",
        "credit risk",
        "default risk",
        "sovereign risk",
        "systemic risk",
        "tail risk",
        "drawdown",
        "maximum drawdown",
        "Sharpe ratio",
        "information ratio",
        "Sortino ratio",
        "Calmar ratio",
        "alpha generation",
        "beta hedging",
        "factor exposure",
        "style drift",
        "tracking error",
        "benchmark",
        "index fund",
        "ETF",
        "passive investing",
        "active management",
        "quantitative strategy",
        "systematic trading",
        "algorithmic trading",
        "high frequency trading",
        "statistical arbitrage",
        "pairs trading",
        "cointegration",
        "mean reversion",
        "trend following",
        "breakout strategy",
        "support resistance",
        "moving average",
        "RSI",
        "MACD",
        "Bollinger bands",
        "KDJ",
        "OBV",
        "volume profile",
        "market breadth",
        "advance decline",
        "new high new low",
        "put call ratio",
        "VIX",
        "implied volatility",
        "realized volatility",
        "volatility surface",
        "term structure",
        "yield curve",
        "credit spread",
        "interest rate",
        "monetary policy",
        "macroeconomic factor",
        "business cycle",
        "economic indicator",
        "GDP growth",
        "inflation",
        "unemployment",
        "consumer sentiment",
        "PMI",
        "ISM index",
        "earnings surprise",
        "analyst forecast",
        "recommendation",
        "target price",
        "earnings quality",
        "accruals",
        "cash flow",
        "financial statement",
        "balance sheet",
        "income statement",
        "ratio analysis",
        "DuPont analysis",
        "ROE decomposition",
        "profitability",
        "leverage",
        "solvency",
        "efficiency",
        "growth",
        "valuation",
        "DCF",
        "PE ratio",
        "PB ratio",
        "PS ratio",
        "EV EBITDA",
        "PEG ratio",
        "dividend discount",
        "residual income",
        "economic value added",
        "market value added",
        "Tobin Q",
        "book to market",
        "enterprise value",
        "market capitalization",
        "float",
        "shares outstanding",
        "ownership structure",
        "corporate governance",
        "board composition",
        "executive compensation",
        "shareholder activism",
        "ESG factor",
        "sustainability",
        "carbon footprint",
        "social responsibility",
        "green finance",
        "climate risk",
        "transition risk",
        "physical risk",
        "TCFD",
        "SFDR",
        "EU taxonomy",
    ]
    
    QUANT_CATEGORIES = [
        "q-fin.PM",
        "q-fin.ST",
        "q-fin.CP",
        "q-fin.GN",
        "q-fin.MF",
        "q-fin.RM",
        "q-fin.TR",
        "cs.LG",
        "cs.AI",
        "stat.ML",
        "econ.EM",
        "econ.GN",
    ]
    
    def __init__(self, max_results: int = 50):
        self.max_results = max_results
    
    def search(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        categories: Optional[List[str]] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ):
        try:
            import arxiv
        except ImportError:
            print("警告: arxiv模块未安装，请运行: pip install arxiv")
            return []
        
        if query is None:
            if keywords is None:
                keywords = random.sample(self.QUANT_KEYWORDS, min(20, len(self.QUANT_KEYWORDS)))
                print(f"随机选择关键词: {', '.join(keywords[:5])}...")
            query = " OR ".join([f'"{kw}"' for kw in keywords])
        
        if categories is None:
            categories = self.QUANT_CATEGORIES[:4]
        
        if categories:
            cat_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query = f"({query}) AND ({cat_query})"
        
        papers = []
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending,
            )
            
            for result in search.results():
                if date_from or date_to:
                    pub_date = result.published.strftime("%Y-%m-%d")
                    if date_from and pub_date < date_from:
                        continue
                    if date_to and pub_date > date_to:
                        continue
                
                paper = PaperInfo(
                    title=result.title,
                    authors=[a.name for a in result.authors],
                    abstract=result.summary,
                    url=result.entry_id,
                    pdf_url=result.pdf_url,
                    published_date=result.published.strftime("%Y-%m-%d"),
                    categories=result.categories,
                )
                papers.append(paper)
        
        except Exception as e:
            print(f"arXiv搜索失败: {e}")
        
        return papers


class SemanticScholarSearcher:
    """Semantic Scholar论文搜索器"""
    
    API_BASE = "https://api.semanticscholar.org/graph/v1"
    
    QUANT_KEYWORDS = [
        "quantitative finance",
        "factor investing",
        "stock prediction",
        "portfolio optimization",
    ]
    
    def __init__(self, api_key: Optional[str] = None, max_results: int = 50):
        self.api_key = api_key
        self.max_results = max_results
        self.headers = {"x-api-key": api_key} if api_key else {}
    
    def search(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_citations: int = 0,
    ) -> List[PaperInfo]:
        """
        搜索Semantic Scholar论文
        
        Args:
            query: 自定义查询字符串
            keywords: 关键词列表
            year_from: 起始年份
            year_to: 结束年份
            min_citations: 最小引用数
        
        Returns:
            论文信息列表
        """
        if query is None:
            if keywords is None:
                keywords = self.QUANT_KEYWORDS
            query = " ".join(keywords)
        
        papers = []
        
        for attempt in range(3):
            try:
                url = f"{self.API_BASE}/paper/search"
                params = {
                    "query": query,
                    "limit": min(self.max_results, 20),
                    "fields": "title,authors,abstract,url,year,citationCount,openAccessPdf,publicationDate,venue",
                }
                
                if year_from:
                    params["year"] = f"{year_from}-"
                if year_to:
                    if "year" in params:
                        params["year"] = f"{year_from}-{year_to}"
                    else:
                        params["year"] = f"-{year_to}"
                
                if attempt > 0:
                    time.sleep(2 ** attempt)
                
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                
                if response.status_code == 429:
                    print(f"Semantic Scholar API限流，等待重试... (尝试 {attempt + 1}/3)")
                    time.sleep(5 * (attempt + 1))
                    continue
                
                response.raise_for_status()
                
                data = response.json()
                
                for item in data.get("data", []):
                    if item.get("citationCount", 0) < min_citations:
                        continue
                    
                    pdf_url = None
                    if item.get("openAccessPdf"):
                        pdf_url = item["openAccessPdf"].get("url")
                    
                    if not pdf_url:
                        continue
                    
                    paper = PaperInfo(
                        title=item.get("title", ""),
                        authors=[a.get("name", "") for a in item.get("authors", [])],
                        abstract=item.get("abstract", ""),
                        url=item.get("url", ""),
                        pdf_url=pdf_url,
                        published_date=item.get("publicationDate", ""),
                        categories=[],
                        citation_count=item.get("citationCount"),
                    )
                    papers.append(paper)
                
                break
            
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429:
                    continue
                print(f"Semantic Scholar搜索失败: {e}")
                break
            except Exception as e:
                print(f"Semantic Scholar搜索失败: {e}")
                break
        
        return papers


class OpenAlexSearcher:
    """OpenAlex论文搜索器 (免费开放获取)"""
    
    API_BASE = "https://api.openalex.org"
    
    def __init__(self, email: Optional[str] = None, max_results: int = 50):
        self.email = email
        self.max_results = max_results
        self.headers = {"mailto": email} if email else {}
    
    def search(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        min_citations: int = 0,
        is_oa: bool = True,
    ):
        if query is None:
            if keywords is None:
                keywords = ["factor investing", "stock prediction"]
            query = " ".join(keywords)
        
        papers = []
        
        try:
            url = f"{self.API_BASE}/works"
            params = {
                "search": query,
                "per_page": min(self.max_results, 50),
                "filter": "type:article",
            }
            
            filters = []
            if is_oa:
                filters.append("is_oa:true")
            if year_from:
                filters.append(f"from_publication_date:{year_from}-01-01")
            if year_to:
                filters.append(f"to_publication_date:{year_to}-12-31")
            if min_citations:
                filters.append(f"cited_by_count:>{min_citations}")
            
            if filters:
                params["filter"] = ",".join(filters)
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get("results", []):
                pdf_url = None
                oa = item.get("open_access", {})
                if oa.get("is_oa"):
                    pdf_url = oa.get("oa_url")
                
                if not pdf_url:
                    continue
                
                paper = PaperInfo(
                    title=item.get("title", ""),
                    authors=[a.get("author", {}).get("display_name", "") for a in item.get("authorships", [])],
                    abstract=item.get("abstract", "") or "",
                    url=item.get("id", ""),
                    pdf_url=pdf_url,
                    published_date=item.get("publication_date", ""),
                    categories=[c.get("display_name", "") for c in item.get("concepts", [])[:5]],
                    citation_count=item.get("cited_by_count"),
                )
                papers.append(paper)
        
        except Exception as e:
            print(f"OpenAlex搜索失败: {e}")
        
        return papers


class CORESearcher:
    """CORE论文搜索器 (开放获取论文聚合)"""
    
    API_BASE = "https://api.core.ac.uk/v3"
    
    def __init__(self, api_key: Optional[str] = None, max_results: int = 50):
        self.api_key = api_key
        self.max_results = max_results
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    
    def search(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
    ):
        if query is None:
            if keywords is None:
                keywords = ["factor investing", "stock prediction"]
            query = " ".join(keywords)
        
        papers = []
        
        try:
            url = f"{self.API_BASE}/search/works"
            params = {
                "q": query,
                "limit": min(self.max_results, 30),
            }
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 401:
                print("CORE API需要密钥，跳过...")
                return []
            
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get("results", []):
                pdf_url = item.get("downloadUrl")
                if not pdf_url:
                    continue
                
                paper = PaperInfo(
                    title=item.get("title", ""),
                    authors=item.get("authors", []),
                    abstract=item.get("abstract", "") or "",
                    url=item.get("id", ""),
                    pdf_url=pdf_url,
                    published_date=item.get("yearPublished", "") or "",
                    categories=[],
                )
                papers.append(paper)
        
        except Exception as e:
            print(f"CORE搜索失败: {e}")
        
        return papers


class CrossrefSearcher:
    """Crossref论文搜索器（仅开放获取）"""
    
    API_BASE = "https://api.crossref.org"
    
    PAID_PUBLISHERS = [
        "wiley.com",
        "elsevier.com",
        "springer.com",
        "tandfonline.com",
        "oup.com",
        "cambridge.org",
        "ieee.org",
        "emerald.com",
        "ssrn.com",
    ]
    
    def __init__(self, email: Optional[str] = None, max_results: int = 50):
        self.email = email
        self.max_results = max_results
        self.headers = {"User-Agent": f"FactorMiningBot (mailto:{email})"} if email else {}
    
    def search(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        year_from: Optional[int] = None,
        min_citations: int = 0,
    ):
        if query is None:
            if keywords is None:
                keywords = ["factor investing", "stock prediction"]
            query = " ".join(keywords)
        
        papers = []
        
        try:
            url = f"{self.API_BASE}/works"
            params = {
                "query": query,
                "rows": min(self.max_results, 50),
                "filter": "type:journal-article",
            }
            
            filters = []
            if year_from:
                filters.append(f"from-pub-date:{year_from}")
            if min_citations:
                filters.append(f"is-referenced-by-count:{min_citations}")
            
            if filters:
                params["filter"] += "," + ",".join(filters)
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            for item in data.get("message", {}).get("items", []):
                pdf_url = None
                links = item.get("link", [])
                if links:
                    pdf_url = links[0].get("URL")
                
                if not pdf_url:
                    continue
                
                if any(publisher in pdf_url.lower() for publisher in self.PAID_PUBLISHERS):
                    continue
                
                paper = PaperInfo(
                    title=item.get("title", [""])[0],
                    authors=[a.get("given", "") + " " + a.get("family", "") for a in item.get("author", [])],
                    abstract=item.get("abstract", "") or "",
                    url=item.get("URL", ""),
                    pdf_url=pdf_url,
                    published_date=item.get("published-print", {}).get("date-parts", [[None]])[0][0] or "",
                    categories=[],
                    citation_count=item.get("is-referenced-by-count"),
                )
                papers.append(paper)
        
        except Exception as e:
            print(f"Crossref搜索失败: {e}")
        
        return papers


class LLMQuantSearcher:
    """LLMQuant Data搜索器（专门针对量化金融）"""
    
    API_BASE = "https://api.llmquantdata.com"
    
    def __init__(self, api_key: Optional[str] = None, max_results: int = 30):
        self.api_key = api_key or os.getenv("LLMQUANT_API_KEY")
        self.max_results = max_results
        self.headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
    
    def search(
        self,
        prompt: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        top_k: Optional[int] = None,
    ) -> List[PaperInfo]:
        """
        语义搜索论文
        
        Args:
            prompt: 搜索提示（自然语言）
            keywords: 关键词列表（会转换为prompt）
            top_k: 返回数量
        
        Returns:
            论文列表
        """
        if not self.api_key:
            print("LLMQuant API需要密钥，跳过...")
            return []
        
        if prompt is None:
            if keywords is None:
                keywords = ["factor investing", "stock prediction"]
            prompt = " ".join(keywords)
        
        papers = []
        
        try:
            params = {
                "prompt": prompt,
                "topK": top_k or self.max_results,
            }
            
            response = requests.get(
                f"{self.API_BASE}/paper/search",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            
            if response.status_code == 401:
                print("LLMQuant API密钥无效，跳过...")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            for item in data.get("results", []):
                paper = PaperInfo(
                    title=item.get("title", ""),
                    authors=item.get("authors", []),
                    abstract=item.get("abstract", "") or "",
                    url=item.get("url", ""),
                    pdf_url=item.get("pdf_url", ""),
                    published_date=item.get("date", "") or "",
                    categories=["quantitative finance"],
                    citation_count=item.get("citations", 0),
                )
                papers.append(paper)
        
        except Exception as e:
            print(f"LLMQuant搜索失败: {e}")
        
        return papers


class PaperSearcher:
    """统一论文搜索接口"""
    
    SOURCES = ["arxiv", "semantic_scholar", "openalex", "llmquant"]
    
    def __init__(
        self,
        use_arxiv: bool = True,
        use_semantic_scholar: bool = True,
        use_openalex: bool = True,
        use_llmquant: bool = True,
        use_core: bool = False,
        use_crossref: bool = False,
        semantic_scholar_api_key: Optional[str] = None,
        llmquant_api_key: Optional[str] = None,
        core_api_key: Optional[str] = None,
        email: Optional[str] = None,
        max_results_per_source: int = 30,
    ):
        self.arxiv_searcher = ArxivSearcher(max_results=max_results_per_source) if use_arxiv else None
        self.ss_searcher = SemanticScholarSearcher(
            api_key=semantic_scholar_api_key,
            max_results=max_results_per_source
        ) if use_semantic_scholar else None
        self.openalex_searcher = OpenAlexSearcher(
            email=email,
            max_results=max_results_per_source
        ) if use_openalex else None
        self.llmquant_searcher = LLMQuantSearcher(
            api_key=llmquant_api_key,
            max_results=max_results_per_source
        ) if use_llmquant else None
        self.core_searcher = CORESearcher(
            api_key=core_api_key,
            max_results=max_results_per_source
        ) if use_core else None
        self.crossref_searcher = CrossrefSearcher(
            email=email,
            max_results=max_results_per_source
        ) if use_crossref else None
    
    def search(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        sources: Optional[List[str]] = None,
        **kwargs,
    ):
        all_papers = []
        
        if sources is None:
            sources = self.SOURCES
        
        if self.llmquant_searcher and "llmquant" in sources:
            papers = self.llmquant_searcher.search(prompt=query, keywords=keywords)
            all_papers.extend(papers)
            print(f"LLMQuant找到 {len(papers)} 篇论文")
        
        if self.arxiv_searcher and "arxiv" in sources:
            papers = self.arxiv_searcher.search(query=query, keywords=keywords, **kwargs)
            all_papers.extend(papers)
            print(f"arXiv找到 {len(papers)} 篇论文")
        
        if self.ss_searcher and "semantic_scholar" in sources:
            time.sleep(1)
            papers = self.ss_searcher.search(query=query, keywords=keywords, **kwargs)
            all_papers.extend(papers)
            print(f"Semantic Scholar找到 {len(papers)} 篇论文")
        
        if self.openalex_searcher and "openalex" in sources:
            time.sleep(1)
            papers = self.openalex_searcher.search(query=query, keywords=keywords, **kwargs)
            all_papers.extend(papers)
            print(f"OpenAlex找到 {len(papers)} 篇论文")
        
        if self.core_searcher and "core" in sources:
            time.sleep(1)
            papers = self.core_searcher.search(query=query, keywords=keywords, **kwargs)
            all_papers.extend(papers)
            print(f"CORE找到 {len(papers)} 篇论文")
        
        if self.crossref_searcher and "crossref" in sources:
            time.sleep(1)
            papers = self.crossref_searcher.search(query=query, keywords=keywords, **kwargs)
            all_papers.extend(papers)
            print(f"Crossref找到 {len(papers)} 篇论文")
        
        seen_urls = set()
        unique_papers = []
        for paper in all_papers:
            if paper.url not in seen_urls:
                seen_urls.add(paper.url)
                unique_papers.append(paper)
        
        return unique_papers
    
    def _get_open_access_url(self, doi: str) -> Optional[str]:
        """通过Unpaywall API获取开放获取PDF链接"""
        if not doi:
            return None
        
        try:
            email = os.getenv("UNPAYWALL_EMAIL", "research@example.com")
            url = f"https://api.unpaywall.org/v2/{doi}?email={email}"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("is_oa"):
                    locations = data.get("oa_locations", [])
                    for loc in locations:
                        pdf_url = loc.get("url_for_pdf")
                        if pdf_url:
                            return pdf_url
        except Exception as e:
            pass
        
        return None
    
    def download_papers(
        self,
        papers: List[PaperInfo],
        output_dir: str,
        max_papers: int = 10,
    ) -> List[str]:
        """
        下载论文PDF
        
        Args:
            papers: 论文信息列表
            output_dir: 输出目录
            max_papers: 最大下载数量
        
        Returns:
            下载的PDF文件路径列表
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        PAID_DOMAINS = [
            "wiley.com",
            "elsevier.com",
            "springer.com",
            "tandfonline.com",
            "oup.com",
            "academic.oup.com",
            "cambridge.org",
            "ieee.org",
            "emerald.com",
            "ssrn.com",
        ]
        
        def is_paid_journal(url: str) -> bool:
            return any(domain in url.lower() for domain in PAID_DOMAINS)
        
        arxiv_papers = [p for p in papers if "arxiv.org" in p.pdf_url.lower()]
        other_papers = [p for p in papers if "arxiv.org" not in p.pdf_url.lower()]
        sorted_papers = arxiv_papers + other_papers
        
        downloaded = []
        skipped_paid = 0
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
        
        for i, paper in enumerate(sorted_papers[:max_papers]):
            if not paper.pdf_url:
                continue
            
            print(f"下载 [{i+1}/{min(len(sorted_papers), max_papers)}]: {paper.title[:50]}...")
            
            pdf_url = paper.pdf_url
            is_arxiv = "arxiv.org" in pdf_url.lower()
            
            if is_paid_journal(pdf_url):
                if paper.doi:
                    open_url = self._get_open_access_url(paper.doi)
                    if open_url:
                        pdf_url = open_url
                        print(f"  → 使用开放获取源")
                    else:
                        print(f"  ✗ 跳过付费期刊（无开放获取版本）")
                        skipped_paid += 1
                        continue
                else:
                    print(f"  ✗ 跳过付费期刊")
                    skipped_paid += 1
                    continue
            
            for attempt in range(3):
                try:
                    response = requests.get(
                        pdf_url,
                        headers=headers,
                        timeout=60,
                        allow_redirects=True,
                    )
                    
                    if response.status_code == 200:
                        break
                    elif response.status_code == 403:
                        if attempt < 2:
                            wait_time = 2 ** attempt
                            print(f"  ⚠️ 403错误，等待{wait_time}秒后重试...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"  ✗ 403 Forbidden (重试{attempt+1}次后仍失败)")
                            break
                    elif response.status_code == 404:
                        print(f"  ✗ 404 Not Found (论文可能已移除)")
                        break
                    else:
                        if attempt < 2:
                            wait_time = 2 ** attempt
                            print(f"  ⚠️ HTTP {response.status_code}，等待{wait_time}秒后重试...")
                            time.sleep(wait_time)
                            continue
                        else:
                            print(f"  ✗ HTTP {response.status_code} (重试{attempt+1}次后仍失败)")
                            break
                
                except requests.exceptions.Timeout:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        print(f"  ⚠️ 连接超时，等待{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ✗ 连接超时 (重试{attempt+1}次后仍失败)")
                        break
                
                except requests.exceptions.ConnectionError as e:
                    if attempt < 2:
                        wait_time = 2 ** attempt
                        print(f"  ⚠️ 连接错误，等待{wait_time}秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ✗ 连接错误: {str(e)[:100]}")
                        break
            
            if response.status_code != 200:
                continue
            
            try:
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' not in content_type and not response.content.startswith(b'%PDF'):
                    print(f"  ✗ 不是有效的PDF文件 (Content-Type: {content_type})")
                    continue
                
                safe_title = "".join(c for c in paper.title[:50] if c.isalnum() or c in " -_")
                pdf_path = output_path / f"{safe_title}.pdf"
                
                with open(pdf_path, "wb") as f:
                    f.write(response.content)
                
                downloaded.append(str(pdf_path))
                print(f"  ✓ 保存到: {pdf_path}")
                
                time.sleep(2)
            
            except Exception as e:
                print(f"  ✗ 下载失败: {e}")
        
        if skipped_paid > 0:
            print(f"\n跳过 {skipped_paid} 篇付费期刊论文")
        print(f"\n总计下载 {len(downloaded)} 篇论文")
        return downloaded
