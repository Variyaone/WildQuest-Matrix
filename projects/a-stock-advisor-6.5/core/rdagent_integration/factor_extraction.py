"""
Factor Extraction from Papers

Extract factors from academic papers automatically.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any


@dataclass
class ExtractedFactor:
    name: str
    description: str
    formulation: str
    variables: Dict[str, str]
    source_paper: str
    source_url: str
    confidence: float
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "formulation": self.formulation,
            "variables": self.variables,
            "source_paper": self.source_paper,
            "source_url": self.source_url,
            "confidence": self.confidence,
        }


class PaperFilter:
    """论文筛选器"""
    
    RELEVANT_KEYWORDS = [
        "factor",
        "alpha",
        "signal",
        "indicator",
        "predict",
        "return",
        "momentum",
        "reversal",
        "value",
        "quality",
        "volatility",
        "liquidity",
        "technical",
        "fundamental",
        "stock",
        "equity",
        "market",
        "portfolio",
        "asset pricing",
        "cross-sectional",
        "anomaly",
        "fama-french",
        "french",
        "carhart",
        "size factor",
        "value factor",
        "profitability",
        "investment factor",
        "risk premium",
        "factor model",
        "multi-factor",
        "factor investing",
        "smart beta",
        "quantitative",
        "quant",
        "trading strategy",
        "stock selection",
        "portfolio optimization",
    ]
    
    IRRELEVANT_KEYWORDS = [
        "cryptocurrency",
        "bitcoin",
        "blockchain",
        "nft",
        "defi",
        "decentralized finance",
        "automated market maker",
        "amm",
        "token",
        "ico",
        "high frequency trading",
        "hft",
        "option pricing",
        "derivatives pricing",
        "credit risk",
        "default risk",
        "medical",
        "biomedical",
        "clinical",
        "patient",
        "disease",
        "cancer",
        "tumor",
        "therapy",
        "treatment",
        "diagnosis",
        "drug",
        "medicine",
        "healthcare",
        "hospital",
        "biological",
        "biochemistry",
        "molecular biology",
        "genetics",
        "protein",
        "gene expression",
        "cell",
        "tissue",
        "organism",
        "physiology",
        "pathology",
        "pharmacology",
        "toxicology",
        "epidemiology",
        "vaccine",
        "virus",
        "bacteria",
        "infection",
        "immune system",
        "antibody",
        "antigen",
        "hemophilia",
        "coagulation",
        "blood clotting",
        "von willebrand",
        "factor viii",
        "factor ix",
        "christmas factor",
        "growth factor receptor",
        "epidermal growth",
        "insulin-like",
        "plasminogen",
        "hageman factor",
    ]
    
    @classmethod
    def calculate_relevance_score(cls, paper_info: dict) -> float:
        """
        计算论文相关性得分
        
        Args:
            paper_info: 论文信息字典
        
        Returns:
            相关性得分 (0-1)
        """
        title = paper_info.get("title", "") or ""
        abstract = paper_info.get("abstract", "") or ""
        title_lower = title.lower()
        abstract_lower = abstract.lower()
        text = f"{title_lower} {abstract_lower}"
        
        score = 0.0
        
        for kw in cls.RELEVANT_KEYWORDS:
            if kw in title_lower:
                score += 0.15
            elif kw in abstract_lower:
                score += 0.08
        
        for kw in cls.IRRELEVANT_KEYWORDS:
            if kw in title_lower:
                score -= 0.5
            elif kw in abstract_lower:
                score -= 0.3
        
        citation_count = paper_info.get("citation_count", 0)
        if citation_count:
            score += min(citation_count / 100, 0.2)
        
        return max(0.0, min(1.0, score))
    
    @classmethod
    def filter_papers(
        cls,
        papers: List[Any],
        min_score: float = 0.3,
        max_papers: int = 20,
    ) -> List[Any]:
        """
        筛选论文
        
        Args:
            papers: 论文列表
            min_score: 最小相关性得分
            max_papers: 最大返回数量
        
        Returns:
            筛选后的论文列表
        """
        scored_papers = []
        
        for paper in papers:
            if hasattr(paper, "to_dict"):
                paper_dict = paper.to_dict()
            else:
                paper_dict = paper
            
            score = cls.calculate_relevance_score(paper_dict)
            
            if score >= min_score:
                if hasattr(paper, "relevance_score"):
                    paper.relevance_score = score
                scored_papers.append((paper, score))
        
        scored_papers.sort(key=lambda x: x[1], reverse=True)
        
        return [p for p, s in scored_papers[:max_papers]]


class FactorExtractor:
    """因子提取器"""
    
    def __init__(self, rdagent_venv: str):
        """
        初始化因子提取器
        
        Args:
            rdagent_venv: RDAgent虚拟环境路径
        """
        self.rdagent_venv = rdagent_venv
        self.rdagent_cli = os.path.join(rdagent_venv, "bin", "rdagent")
        self.python_path = os.path.join(rdagent_venv, "bin", "python")
    
    def _preprocess_pdf(self, pdf_path: str, max_pages: int = 15) -> Optional[str]:
        """
        预处理PDF，提取关键部分
        
        Args:
            pdf_path: PDF文件路径
            max_pages: 最大提取页数
        
        Returns:
            预处理后的临时PDF路径，如果失败返回None
        """
        try:
            import fitz
        except ImportError:
            return None
        
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
            
            if total_pages <= max_pages:
                return pdf_path
            
            relevant_pages = []
            
            for page_num in range(min(20, total_pages)):
                text = doc[page_num].get_text()
                if any(keyword in text.lower() for keyword in ["factor", "alpha", "signal", "indicator", "formula"]):
                    relevant_pages.append(page_num)
            
            if not relevant_pages:
                relevant_pages = list(range(min(max_pages, total_pages)))
            
            relevant_pages = relevant_pages[:max_pages]
            relevant_pages.sort()
            
            new_doc = fitz.open()
            for page_num in relevant_pages:
                new_doc.insert_pdf(doc, from_page=page_num, to_page=page_num)
            
            temp_pdf = str(Path(pdf_path).parent / f"{Path(pdf_path).stem}_preprocessed.pdf")
            new_doc.save(temp_pdf)
            new_doc.close()
            doc.close()
            
            print(f"  已预处理PDF: {total_pages}页 → {len(relevant_pages)}页")
            return temp_pdf
        
        except Exception as e:
            return None
    
    def extract_from_pdf(self, pdf_path: str, max_file_size_mb: int = 10) -> List[ExtractedFactor]:
        """
        从PDF提取因子
        
        Args:
            pdf_path: PDF文件路径
            max_file_size_mb: 最大文件大小（MB），超过此大小将跳过
        
        Returns:
            提取的因子列表
        """
        factors = []
        
        try:
            pdf_size_mb = Path(pdf_path).stat().st_size / (1024 * 1024)
            if pdf_size_mb > max_file_size_mb:
                print(f"  ✗ 跳过大文件 ({pdf_size_mb:.1f}MB > {max_file_size_mb}MB)")
                return factors
            
            print(f"正在提取因子: {Path(pdf_path).name} ({pdf_size_mb:.1f}MB)")
            
            processed_pdf = self._preprocess_pdf(pdf_path)
            if processed_pdf and processed_pdf != pdf_path:
                pdf_path = processed_pdf
            
            cmd = [
                self.python_path,
                "-c",
                f"""
import json
import sys

from rdagent.scenarios.qlib.factor_experiment_loader.pdf_loader import FactorExperimentLoaderFromPDFfiles

try:
    loader = FactorExperimentLoaderFromPDFfiles()
    exp = loader.load("{pdf_path}")
    
    if exp and hasattr(exp, 'sub_tasks') and exp.sub_tasks:
        factors = []
        for task in exp.sub_tasks:
            factor = {{
                "name": task.factor_name,
                "description": task.factor_description,
                "formulation": task.factor_formulation,
                "variables": task.variables,
            }}
            factors.append(factor)
        
        sys.stdout.write("<<<JSON_START>>>\\n")
        sys.stdout.write(json.dumps(factors, ensure_ascii=False))
        sys.stdout.write("\\n<<<JSON_END>>>\\n")
        sys.stdout.flush()
    else:
        sys.stdout.write("<<<JSON_START>>>\\n")
        sys.stdout.write("[]")
        sys.stdout.write("\\n<<<JSON_END>>>\\n")
        sys.stdout.flush()
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"Error: {{e}}", file=sys.stderr)
    sys.stdout.write("<<<JSON_START>>>\\n")
    sys.stdout.write("[]")
    sys.stdout.write("\\n<<<JSON_END>>>\\n")
    sys.stdout.flush()
"""
            ]
            
            env = os.environ.copy()
            nvidia_key = os.getenv("NVIDIA_API_KEY") or os.getenv("NVIDIA_NIM_API_KEY")
            if nvidia_key and not os.getenv("OPENAI_API_KEY"):
                env["LITELLM_CHAT_MODEL"] = "nvidia_nim/meta/llama-3.1-70b-instruct"
                env["LITELLM_EMBEDDING_MODEL"] = "nvidia_nim/nvidia/embed-qa-4"
                env["NVIDIA_NIM_API_KEY"] = nvidia_key
                print(f"  使用 NVIDIA NIM API: {env['LITELLM_CHAT_MODEL']}")
            else:
                print(f"  ⚠️ 警告: 未找到NVIDIA API密钥，提取可能失败")
                print(f"  请运行: bash setup_nvidia_api.sh 配置API密钥")
            
            timeout = 600 if pdf_size_mb > 0.5 else 300
            
            print(f"  开始提取 (超时设置: {timeout}秒)...")
            print(f"  处理步骤:")
            print(f"    1/5 加载PDF文档...")
            print(f"    2/5 文档分类 (LLM调用)...")
            print(f"    3/5 提取因子 (LLM调用)...")
            print(f"    4/5 生成公式 (LLM调用)...")
            print(f"    5/5 验证因子...")
            print(f"  ⏳ 正在处理，请耐心等待...")
            
            import time
            start_time = time.time()
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )
            
            dots = 0
            while process.poll() is None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    process.kill()
                    raise subprocess.TimeoutExpired(cmd, timeout)
                
                dots = (dots + 1) % 4
                progress_dots = "." * dots + " " * (3 - dots)
                print(f"\r  ⏳ 处理中 [{int(elapsed)}s/{timeout}s]{progress_dots}", end="", flush=True)
                time.sleep(1)
            
            stdout, stderr = process.communicate()
            elapsed = time.time() - start_time
            print(f"\r  ✓ 处理完成 (耗时: {elapsed:.1f}秒)    ")
            
            class Result:
                def __init__(self, returncode, stdout, stderr):
                    self.returncode = returncode
                    self.stdout = stdout
                    self.stderr = stderr
            
            result = Result(process.returncode, stdout, stderr)
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                print(f"  ✗ 提取失败 (返回码={result.returncode}): {error_msg[:200]}")
                if result.stdout:
                    print(f"  stdout前200字符: {result.stdout[:200]}")
                return factors
            
            if not result.stdout.strip():
                print(f"  ✗ 提取失败: stdout为空")
                if result.stderr:
                    print(f"  stderr: {result.stderr[:200]}")
                return factors
            
            json_str = None
            if "<<<JSON_START>>>" in result.stdout and "<<<JSON_END>>>" in result.stdout:
                start_marker = "<<<JSON_START>>>"
                end_marker = "<<<JSON_END>>>"
                start_idx = result.stdout.find(start_marker) + len(start_marker)
                end_idx = result.stdout.find(end_marker)
                if start_idx < end_idx:
                    json_str = result.stdout[start_idx:end_idx].strip()
            
            if not json_str:
                lines = result.stdout.strip().split('\n')
                for line in reversed(lines):
                    line = line.strip()
                    if line.startswith('[') or line.startswith('{'):
                        json_str = line
                        break
            
            if not json_str:
                print(f"  ✗ 提取失败: 无法从stdout中提取JSON")
                print(f"  stdout前500字符: {result.stdout[:500]}")
                if result.stderr:
                    print(f"  stderr前200字符: {result.stderr[:200]}")
                return factors
            
            factors_data = json.loads(json_str)
            
            for f in factors_data:
                factor = ExtractedFactor(
                    name=f.get("name", ""),
                    description=f.get("description", ""),
                    formulation=f.get("formulation", ""),
                    variables=f.get("variables", {}),
                    source_paper=Path(pdf_path).stem,
                    source_url="",
                    confidence=0.8,
                )
                factors.append(factor)
            
            print(f"  ✓ 提取到 {len(factors)} 个因子")
        
        except json.JSONDecodeError as e:
            print(f"  ✗ JSON解析失败: {e}")
            print(f"  尝试解析的内容 (前200字符): {json_str[:200] if json_str else 'None'}")
            if result and hasattr(result, 'stdout'):
                print(f"  完整stdout长度: {len(result.stdout)} 字符")
                print(f"  stdout前500字符: {result.stdout[:500]}")
            if result and hasattr(result, 'stderr') and result.stderr:
                print(f"  stderr前200字符: {result.stderr[:200]}")
        except subprocess.TimeoutExpired:
            print(f"  ✗ 提取超时 (超过{timeout}秒)")
            print(f"  提示: 论文可能过大或复杂，建议：")
            print(f"    1. 使用更小的PDF文件")
            print(f"    2. 检查网络连接和API配额")
            print(f"    3. 尝试手动预处理PDF，只保留关键部分")
        except Exception as e:
            print(f"  ✗ 提取出错: {e}")
        
        return factors
    
    def extract_from_papers(
        self,
        pdf_paths: List[str],
        output_file: Optional[str] = None,
        prefer_small_files: bool = True,
    ) -> List[ExtractedFactor]:
        """
        从多篇论文提取因子
        
        Args:
            pdf_paths: PDF文件路径列表
            output_file: 输出文件路径
            prefer_small_files: 是否优先处理小文件
        
        Returns:
            提取的因子列表
        """
        all_factors = []
        
        if prefer_small_files:
            pdf_paths_with_size = []
            for pdf_path in pdf_paths:
                try:
                    size = Path(pdf_path).stat().st_size
                    pdf_paths_with_size.append((pdf_path, size))
                except Exception:
                    pdf_paths_with_size.append((pdf_path, float('inf')))
            
            pdf_paths_with_size.sort(key=lambda x: x[1])
            pdf_paths = [p[0] for p in pdf_paths_with_size]
            print(f"已按文件大小排序，优先处理小文件")
        
        total = len(pdf_paths)
        for i, pdf_path in enumerate(pdf_paths, 1):
            try:
                print(f"\n[{i}/{total}] 处理: {Path(pdf_path).name}")
                factors = self.extract_from_pdf(pdf_path)
                all_factors.extend(factors)
                
                if output_file and i % 3 == 0:
                    self._save_factors(all_factors, output_file)
                    print(f"  已缓存 {len(all_factors)} 个因子")
            
            except Exception as e:
                print(f"  ✗ 处理失败: {e}")
                print(f"  继续处理下一篇论文...")
                
                if output_file and all_factors:
                    self._save_factors(all_factors, output_file)
                    print(f"  已保存部分结果: {len(all_factors)} 个因子")
        
        if output_file:
            self._save_factors(all_factors, output_file)
            print(f"\n✓ 因子已保存到: {output_file}")
        
        return all_factors
    
    def _save_factors(self, factors: List[ExtractedFactor], output_file: str):
        """保存因子到文件"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [factor.to_dict() for factor in factors],
                f,
                ensure_ascii=False,
                indent=2,
            )


class AutoFactorMiningPipeline:
    """自动化因子挖掘管线"""
    
    def __init__(
        self,
        rdagent_venv: str,
        paper_output_dir: str = "papers",
        factor_output_file: str = "extracted_factors.json",
        tracker_file: str = "processed_papers.json",
    ):
        """
        初始化管线
        
        Args:
            rdagent_venv: RDAgent虚拟环境路径
            paper_output_dir: 论文输出目录
            factor_output_file: 因子输出文件
            tracker_file: 已处理论文追踪文件
        """
        from .paper_search import PaperSearcher, ProcessedPapersTracker
        
        self.paper_searcher = PaperSearcher()
        self.paper_filter = PaperFilter()
        self.factor_extractor = FactorExtractor(rdagent_venv)
        self.tracker = ProcessedPapersTracker(tracker_file)
        
        self.paper_output_dir = paper_output_dir
        self.factor_output_file = factor_output_file
    
    def run(
        self,
        query: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        max_papers: int = 10,
        min_relevance_score: float = 0.3,
        download_papers: bool = True,
        extract_factors: bool = True,
    ) -> Dict[str, Any]:
        """
        运行完整管线
        
        Args:
            query: 自定义查询字符串
            keywords: 关键词列表
            max_papers: 最大论文数量
            min_relevance_score: 最小相关性得分
            download_papers: 是否下载论文
            extract_factors: 是否提取因子
        
        Returns:
            执行结果
        """
        result = {
            "papers_found": 0,
            "papers_filtered": 0,
            "papers_skipped": 0,
            "papers_downloaded": 0,
            "factors_extracted": 0,
            "factors": [],
            "errors": [],
        }
        
        stats = self.tracker.get_stats()
        print("=" * 60)
        print("已处理论文统计")
        print("=" * 60)
        print(f"  已处理: {stats['total_processed']} 篇")
        print(f"  最近处理: {stats['last_processed']}")
        print()
        
        print("=" * 60)
        print("Step 1: 搜索论文")
        print("=" * 60)
        
        try:
            papers = self.paper_searcher.search(
                query=query,
                keywords=keywords,
            )
            result["papers_found"] = len(papers)
            print(f"找到 {len(papers)} 篇论文")
        except Exception as e:
            result["errors"].append(f"搜索失败: {e}")
            print(f"✗ 搜索失败: {e}")
            return result
        
        print("\n" + "=" * 60)
        print("Step 2: 筛选论文（排除已处理）")
        print("=" * 60)
        
        try:
            filtered_papers = self.paper_filter.filter_papers(
                papers,
                min_score=min_relevance_score,
                max_papers=max_papers * 2,
            )
            
            unprocessed_papers = []
            for paper in filtered_papers:
                paper_url = paper.url if hasattr(paper, "url") else paper.get("url", "")
                paper_title = paper.title if hasattr(paper, "title") else paper.get("title", "")
                
                if not self.tracker.is_processed(paper_url, paper_title):
                    unprocessed_papers.append(paper)
                else:
                    result["papers_skipped"] += 1
            
            unprocessed_papers = unprocessed_papers[:max_papers]
            result["papers_filtered"] = len(unprocessed_papers)
            
            print(f"筛选后保留 {len(filtered_papers)} 篇论文")
            print(f"排除已处理: {result['papers_skipped']} 篇")
            print(f"待处理: {len(unprocessed_papers)} 篇")
            
            for i, paper in enumerate(unprocessed_papers[:5]):
                if hasattr(paper, "title"):
                    print(f"  [{i+1}] {paper.title[:60]}...")
        except Exception as e:
            result["errors"].append(f"筛选失败: {e}")
            print(f"✗ 筛选失败: {e}")
            return result
        
        if not download_papers or not unprocessed_papers:
            if not unprocessed_papers:
                print("\n没有新的论文需要处理")
            return result
        
        filtered_papers = unprocessed_papers
        
        print("\n" + "=" * 60)
        print("Step 3: 下载论文")
        print("=" * 60)
        
        pdf_paths = []
        try:
            pdf_paths = self.paper_searcher.download_papers(
                filtered_papers,
                self.paper_output_dir,
                max_papers=max_papers,
            )
            result["papers_downloaded"] = len(pdf_paths)
        except Exception as e:
            result["errors"].append(f"下载失败: {e}")
            print(f"✗ 下载失败: {e}")
        
        if not extract_factors or not pdf_paths:
            if not pdf_paths:
                print("\n没有成功下载任何论文")
            return result
        
        print("\n" + "=" * 60)
        print("Step 4: 提取因子")
        print("=" * 60)
        
        try:
            factors = self.factor_extractor.extract_from_papers(
                pdf_paths,
                self.factor_output_file,
            )
            result["factors_extracted"] = len(factors)
            result["factors"] = [f.to_dict() for f in factors]
            
            for i, paper in enumerate(filtered_papers[:len(pdf_paths)]):
                paper_url = paper.url if hasattr(paper, "url") else paper.get("url", "")
                paper_title = paper.title if hasattr(paper, "title") else paper.get("title", "")
                self.tracker.mark_processed(
                    paper_url,
                    paper_title,
                    factors_count=len([f for f in factors if f.source_paper == Path(pdf_paths[i]).stem]) if i < len(pdf_paths) else 0
                )
            
            print(f"\n总计提取 {len(factors)} 个因子")
            print(f"已标记 {len(pdf_paths)} 篇论文为已处理")
        except Exception as e:
            result["errors"].append(f"提取失败: {e}")
            print(f"✗ 提取失败: {e}")
        
        return result


def import_factors_to_library(
    factors_file: str = "extracted_factors.json",
    auto_validate: bool = False,
    convert_latex: bool = True,
    llm_model: str = "gpt-4o-mini",
) -> Dict[str, Any]:
    """
    将提取的因子导入因子库
    
    Args:
        factors_file: 因子JSON文件路径
        auto_validate: 是否自动验证
        convert_latex: 是否自动转换LaTeX公式为Python代码
        llm_model: 用于转换的LLM模型
    
    Returns:
        导入结果
    """
    from core.factor.quick_entry import FactorQuickEntry
    from core.factor.registry import get_factor_registry
    from .latex_converter import is_latex_formula, convert_factor_to_code
    
    result = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
        "converted": 0,
        "factors": [],
        "errors": [],
    }
    
    factors_path = Path(factors_file)
    if not factors_path.exists():
        print(f"✗ 因子文件不存在: {factors_file}")
        return result
    
    with open(factors_path, "r", encoding="utf-8") as f:
        factors_data = json.load(f)
    
    result["total"] = len(factors_data)
    print(f"\n{'=' * 60}")
    print("导入因子到因子库")
    print("=" * 60)
    print(f"共 {len(factors_data)} 个因子待导入\n")
    
    quick_entry = FactorQuickEntry()
    registry = get_factor_registry()
    
    for i, factor_data in enumerate(factors_data):
        name = factor_data.get("name", f"Factor_{i+1}")
        formula = factor_data.get("formulation", "")
        description = factor_data.get("description", "")
        source_paper = factor_data.get("source_paper", "")
        variables = factor_data.get("variables", {})
        
        print(f"[{i+1}/{len(factors_data)}] 导入: {name}")
        
        if convert_latex and is_latex_formula(formula):
            print(f"  检测到LaTeX公式，正在转换为Python代码...")
            success, python_code, error = convert_factor_to_code(
                name, formula, description, variables, llm_model
            )
            if success:
                formula = python_code
                result["converted"] += 1
                print(f"  ✓ 转换成功")
            else:
                print(f"  ✗ 转换失败: {error}")
                result["failed"] += 1
                result["errors"].append(f"{name}: LaTeX转换失败 - {error}")
                continue
        
        var_desc = "; ".join([f"{k}: {v}" for k, v in variables.items()])
        full_description = f"{description}"
        if var_desc:
            full_description += f"\n变量: {var_desc}"
        if source_paper:
            full_description += f"\n来源论文: {source_paper}"
        
        try:
            entry_result = quick_entry.quick_add(
                name=name,
                formula=formula,
                description=full_description,
                source="学术论文",
                paper_title=source_paper,
                auto_validate=auto_validate,
            )
            
            if entry_result.success:
                result["success"] += 1
                result["factors"].append({
                    "id": entry_result.item_id,
                    "name": name,
                    "status": "success",
                })
                print(f"  ✓ 成功: {entry_result.item_id}")
            else:
                if "已存在" in entry_result.message:
                    result["skipped"] += 1
                    print(f"  - 跳过: {entry_result.message}")
                else:
                    result["failed"] += 1
                    result["errors"].append(f"{name}: {entry_result.message}")
                    print(f"  ✗ 失败: {entry_result.message}")
        
        except Exception as e:
            result["failed"] += 1
            result["errors"].append(f"{name}: {str(e)}")
            print(f"  ✗ 异常: {e}")
    
    print(f"\n{'=' * 60}")
    print("导入完成")
    print("=" * 60)
    print(f"总计: {result['total']} 个")
    print(f"成功: {result['success']} 个")
    print(f"转换: {result['converted']} 个")
    print(f"跳过: {result['skipped']} 个")
    print(f"失败: {result['failed']} 个")
    
    return result


def import_rdagent_factors_to_library(
    workspace_path: str = "git_ignore_folder/RD-Agent_workspace",
    output_file: str = "converted_rdagent_factors.json",
    auto_validate: bool = False,
) -> Dict[str, Any]:
    """
    导入RDAgent生成的因子到因子库
    
    这个函数会：
    1. 扫描RDAgent workspace中的因子脚本
    2. 将脚本转换为项目可用的格式
    3. 导入到因子库
    
    Args:
        workspace_path: RDAgent workspace路径
        output_file: 转换后的因子JSON文件路径
        auto_validate: 是否自动验证
    
    Returns:
        导入结果
    """
    from .rdagent_factor_converter import convert_rdagent_factors, import_converted_factors
    
    print("=" * 60)
    print("Step 1: 转换RDAgent因子脚本")
    print("=" * 60)
    
    factors = convert_rdagent_factors(workspace_path, output_file)
    
    if not factors:
        print("✗ 没有找到可转换的因子")
        return {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "factors": [],
            "errors": ["没有找到可转换的因子"],
        }
    
    print(f"\n✓ 成功转换 {len(factors)} 个因子")
    
    print("\n" + "=" * 60)
    print("Step 2: 导入因子到因子库")
    print("=" * 60)
    
    result = import_converted_factors(output_file, auto_validate)
    
    return result
