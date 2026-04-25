"""
RDAgent Integration Module

Integration with Microsoft RDAgent for automated quantitative strategy development.
"""

from .runner import RDAgentRunner, RDAgentScenario
from .config import RDAgentConfig


def __getattr__(name):
    """延迟导入"""
    if name == "PaperSearcher":
        from .paper_search import PaperSearcher
        return PaperSearcher
    elif name == "ArxivSearcher":
        from .paper_search import ArxivSearcher
        return ArxivSearcher
    elif name == "SemanticScholarSearcher":
        from .paper_search import SemanticScholarSearcher
        return SemanticScholarSearcher
    elif name == "OpenAlexSearcher":
        from .paper_search import OpenAlexSearcher
        return OpenAlexSearcher
    elif name == "CORESearcher":
        from .paper_search import CORESearcher
        return CORESearcher
    elif name == "CrossrefSearcher":
        from .paper_search import CrossrefSearcher
        return CrossrefSearcher
    elif name == "PaperInfo":
        from .paper_search import PaperInfo
        return PaperInfo
    elif name == "ProcessedPapersTracker":
        from .paper_search import ProcessedPapersTracker
        return ProcessedPapersTracker
    elif name == "FactorExtractor":
        from .factor_extraction import FactorExtractor
        return FactorExtractor
    elif name == "PaperFilter":
        from .factor_extraction import PaperFilter
        return PaperFilter
    elif name == "AutoFactorMiningPipeline":
        from .factor_extraction import AutoFactorMiningPipeline
        return AutoFactorMiningPipeline
    elif name == "ExtractedFactor":
        from .factor_extraction import ExtractedFactor
        return ExtractedFactor
    elif name == "import_factors_to_library":
        from .factor_extraction import import_factors_to_library
        return import_factors_to_library
    elif name == "import_rdagent_factors_to_library":
        from .factor_extraction import import_rdagent_factors_to_library
        return import_rdagent_factors_to_library
    elif name == "RDAgentFactorConverter":
        from .rdagent_factor_converter import RDAgentFactorConverter
        return RDAgentFactorConverter
    elif name == "ConvertedFactor":
        from .rdagent_factor_converter import ConvertedFactor
        return ConvertedFactor
    elif name == "convert_rdagent_factors":
        from .rdagent_factor_converter import convert_rdagent_factors
        return convert_rdagent_factors
    elif name == "import_converted_factors":
        from .rdagent_factor_converter import import_converted_factors
        return import_converted_factors
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "RDAgentRunner",
    "RDAgentScenario",
    "RDAgentConfig",
    "PaperSearcher",
    "ArxivSearcher",
    "SemanticScholarSearcher",
    "OpenAlexSearcher",
    "CORESearcher",
    "CrossrefSearcher",
    "PaperInfo",
    "ProcessedPapersTracker",
    "FactorExtractor",
    "PaperFilter",
    "AutoFactorMiningPipeline",
    "ExtractedFactor",
    "import_factors_to_library",
    "import_rdagent_factors_to_library",
    "RDAgentFactorConverter",
    "ConvertedFactor",
    "convert_rdagent_factors",
    "import_converted_factors",
]
