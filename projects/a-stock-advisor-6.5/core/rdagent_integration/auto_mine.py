"""
Auto Factor Mining from Papers

Automatically search papers and extract factors.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.rdagent_integration.factor_extraction import (
    AutoFactorMiningPipeline,
    PaperFilter,
)
from core.rdagent_integration.config import RDAgentConfig


def search_papers(
    query: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    max_results: int = 30,
    output_file: str = "papers_search_results.json",
):
    """搜索论文"""
    from core.rdagent_integration.paper_search import PaperSearcher
    
    print("=" * 60)
    print("论文搜索")
    print("=" * 60)
    
    searcher = PaperSearcher()
    papers = searcher.search(query=query, keywords=keywords)
    
    print(f"\n找到 {len(papers)} 篇论文")
    
    filtered_papers = PaperFilter.filter_papers(papers, min_score=0.3, max_papers=max_results)
    
    print(f"筛选后保留 {len(filtered_papers)} 篇")
    
    papers_data = []
    for paper in filtered_papers:
        if hasattr(paper, "to_dict"):
            papers_data.append(paper.to_dict())
        else:
            papers_data.append(paper)
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(papers_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n结果已保存到: {output_file}")
    
    print("\n论文列表:")
    for i, paper in enumerate(filtered_papers[:10]):
        title = paper.title if hasattr(paper, "title") else paper.get("title", "")
        print(f"  [{i+1}] {title[:60]}...")
    
    return filtered_papers


def download_papers(
    papers_file: str,
    output_dir: str = "papers",
    max_papers: int = 10,
):
    """下载论文"""
    from core.rdagent_integration.paper_search import PaperSearcher, PaperInfo
    
    print("=" * 60)
    print("下载论文")
    print("=" * 60)
    
    with open(papers_file, "r", encoding="utf-8") as f:
        papers_data = json.load(f)
    
    papers = []
    for p in papers_data:
        paper = PaperInfo(
            title=p.get("title", ""),
            authors=p.get("authors", []),
            abstract=p.get("abstract", ""),
            url=p.get("url", ""),
            pdf_url=p.get("pdf_url", ""),
            published_date=p.get("published_date", ""),
            categories=p.get("categories", []),
            citation_count=p.get("citation_count"),
        )
        papers.append(paper)
    
    searcher = PaperSearcher()
    pdf_paths = searcher.download_papers(papers, output_dir, max_papers)
    
    print(f"\n下载完成: {len(pdf_paths)} 篇论文")
    return pdf_paths


def extract_factors(
    papers_dir: str,
    output_file: str = "extracted_factors.json",
):
    """提取因子"""
    print("=" * 60)
    print("提取因子")
    print("=" * 60)
    
    config = RDAgentConfig()
    
    from core.rdagent_integration.factor_extraction import FactorExtractor
    
    extractor = FactorExtractor(config.venv_path)
    
    papers_path = Path(papers_dir)
    pdf_paths = list(papers_path.glob("*.pdf"))
    
    print(f"找到 {len(pdf_paths)} 个PDF文件")
    
    factors = extractor.extract_from_papers([str(p) for p in pdf_paths], output_file)
    
    print(f"\n提取完成: {len(factors)} 个因子")
    return factors


def auto_mine(
    query: Optional[str] = None,
    keywords: Optional[List[str]] = None,
    max_papers: int = 10,
    output_dir: str = "papers",
    output_file: str = "extracted_factors.json",
    smart_search: bool = False,
    search_strategy: str = "balanced",
):
    """完整自动化流程"""
    print("=" * 60)
    print("自动化因子挖掘管线")
    print("=" * 60)
    print()
    
    if smart_search and keywords is None:
        from .smart_search import SmartKeywordGenerator
        
        generator = SmartKeywordGenerator()
        keywords = generator.generate_keywords(
            strategy=search_strategy,
            count=5,
            include_china=True,
        )
        print(f"智能生成关键词: {', '.join(keywords)}")
        print()
    
    config = RDAgentConfig()
    
    pipeline = AutoFactorMiningPipeline(
        rdagent_venv=config.venv_path,
        paper_output_dir=output_dir,
        factor_output_file=output_file,
    )
    
    result = pipeline.run(
        query=query,
        keywords=keywords,
        max_papers=max_papers,
    )
    
    print("\n" + "=" * 60)
    print("执行结果汇总")
    print("=" * 60)
    print(f"找到论文: {result['papers_found']} 篇")
    print(f"筛选论文: {result['papers_filtered']} 篇")
    print(f"下载论文: {result['papers_downloaded']} 篇")
    print(f"提取因子: {result['factors_extracted']} 个")
    
    if result["errors"]:
        print(f"\n错误: {len(result['errors'])} 个")
        for err in result["errors"]:
            print(f"  - {err}")
    
    if smart_search and keywords:
        try:
            from .smart_search import SmartKeywordGenerator
            generator = SmartKeywordGenerator()
            generator.record_search(
                keywords=keywords,
                papers_found=result['papers_found'],
                papers_downloaded=result['papers_downloaded'],
                factors_extracted=result['factors_extracted'],
            )
        except Exception:
            pass
    
    return result


def main():
    parser = argparse.ArgumentParser(description="自动化论文因子挖掘")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    search_parser = subparsers.add_parser("search", help="搜索论文")
    search_parser.add_argument("--query", type=str, help="自定义查询")
    search_parser.add_argument("--keywords", type=str, nargs="+", help="关键词")
    search_parser.add_argument("--max-results", type=int, default=30, help="最大结果数")
    search_parser.add_argument("--output", type=str, default="papers_search_results.json", help="输出文件")
    
    download_parser = subparsers.add_parser("download", help="下载论文")
    download_parser.add_argument("--papers-file", type=str, required=True, help="论文列表文件")
    download_parser.add_argument("--output-dir", type=str, default="papers", help="输出目录")
    download_parser.add_argument("--max-papers", type=int, default=10, help="最大下载数")
    
    extract_parser = subparsers.add_parser("extract", help="提取因子")
    extract_parser.add_argument("--papers-dir", type=str, required=True, help="论文目录")
    extract_parser.add_argument("--output", type=str, default="extracted_factors.json", help="输出文件")
    
    auto_parser = subparsers.add_parser("auto", help="完整自动化流程")
    auto_parser.add_argument("--query", type=str, help="自定义查询")
    auto_parser.add_argument("--keywords", type=str, nargs="+", help="关键词")
    auto_parser.add_argument("--max-papers", type=int, default=10, help="最大论文数")
    auto_parser.add_argument("--output-dir", type=str, default="papers", help="论文输出目录")
    auto_parser.add_argument("--output-file", type=str, default="extracted_factors.json", help="因子输出文件")
    auto_parser.add_argument("--smart", action="store_true", help="启用智能搜索")
    auto_parser.add_argument(
        "--strategy",
        type=str,
        default="balanced",
        choices=["balanced", "hot", "gap", "academic", "random"],
        help="智能搜索策略 (仅当--smart时生效)",
    )
    
    smart_parser = subparsers.add_parser("smart", help="智能搜索（自动生成关键词）")
    smart_parser.add_argument(
        "--strategy",
        type=str,
        default="balanced",
        choices=["balanced", "hot", "gap", "academic", "random"],
        help="搜索策略",
    )
    smart_parser.add_argument("--max-papers", type=int, default=10, help="最大论文数")
    smart_parser.add_argument("--output-dir", type=str, default="papers", help="论文输出目录")
    smart_parser.add_argument("--output-file", type=str, default="extracted_factors.json", help="因子输出文件")
    
    args = parser.parse_args()
    
    if args.command == "search":
        search_papers(
            query=args.query,
            keywords=args.keywords,
            max_results=args.max_results,
            output_file=args.output,
        )
    elif args.command == "download":
        download_papers(
            papers_file=args.papers_file,
            output_dir=args.output_dir,
            max_papers=args.max_papers,
        )
    elif args.command == "extract":
        extract_factors(
            papers_dir=args.papers_dir,
            output_file=args.output,
        )
    elif args.command == "auto":
        auto_mine(
            query=args.query,
            keywords=args.keywords,
            max_papers=args.max_papers,
            output_dir=args.output_dir,
            output_file=args.output_file,
            smart_search=args.smart,
            search_strategy=args.strategy,
        )
    elif args.command == "smart":
        auto_mine(
            query=None,
            keywords=None,
            max_papers=args.max_papers,
            output_dir=args.output_dir,
            output_file=args.output_file,
            smart_search=True,
            search_strategy=args.strategy,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
