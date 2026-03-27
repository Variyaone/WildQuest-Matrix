"""
RDAgent Scenario Definitions

Defines scenarios for RDAgent integration with the stock advisor system.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ScenarioStatus(Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ScenarioResult:
    """Result of running an RDAgent scenario"""
    scenario_name: str
    status: ScenarioStatus
    factors_generated: int = 0
    models_generated: int = 0
    best_ic: Optional[float] = None
    best_ir: Optional[float] = None
    log_path: Optional[str] = None
    error_message: Optional[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class QlibFactorScenario:
    """
    Scenario for iterative factor evolution using RDAgent.
    
    This scenario uses LLM to propose new factor ideas based on
    market data and existing factor performance, then implements
    and validates them.
    """
    
    name = "Qlib Factor Evolution"
    description = "LLM-driven iterative factor proposal and implementation"
    
    def __init__(
        self,
        data_path: Optional[str] = None,
        max_iterations: int = 10,
        target_ic: float = 0.03,
        auto_register: bool = True,
    ):
        self.data_path = data_path
        self.max_iterations = max_iterations
        self.target_ic = target_ic
        self.auto_register = auto_register
        self._result: Optional[ScenarioResult] = None
    
    def get_config(self) -> dict:
        """Get scenario configuration"""
        return {
            "max_iterations": self.max_iterations,
            "target_ic": self.target_ic,
            "auto_register": self.auto_register,
            "data_path": self.data_path,
        }
    
    def to_result(self, **kwargs) -> ScenarioResult:
        """Create a scenario result"""
        return ScenarioResult(
            scenario_name=self.name,
            **kwargs
        )


class QlibModelScenario:
    """
    Scenario for iterative model evolution using RDAgent.
    
    This scenario uses LLM to propose new model architectures
    and training strategies for quantitative prediction models.
    """
    
    name = "Qlib Model Evolution"
    description = "LLM-driven iterative model architecture proposal and implementation"
    
    def __init__(
        self,
        data_path: Optional[str] = None,
        max_iterations: int = 10,
        target_metric: str = "ic",
        auto_save: bool = True,
    ):
        self.data_path = data_path
        self.max_iterations = max_iterations
        self.target_metric = target_metric
        self.auto_save = auto_save
        self._result: Optional[ScenarioResult] = None
    
    def get_config(self) -> dict:
        """Get scenario configuration"""
        return {
            "max_iterations": self.max_iterations,
            "target_metric": self.target_metric,
            "auto_save": self.auto_save,
            "data_path": self.data_path,
        }
    
    def to_result(self, **kwargs) -> ScenarioResult:
        """Create a scenario result"""
        return ScenarioResult(
            scenario_name=self.name,
            **kwargs
        )


class QlibQuantScenario:
    """
    Scenario for factor-model co-optimization using RDAgent.
    
    This is the most comprehensive scenario that jointly optimizes
    factors and prediction models together, achieving better
    trade-offs between predictive accuracy and strategy robustness.
    """
    
    name = "Qlib Quant Co-Optimization"
    description = "Joint factor-model co-optimization for quantitative strategies"
    
    def __init__(
        self,
        data_path: Optional[str] = None,
        max_iterations: int = 10,
        factor_budget: int = 20,
        model_budget: int = 5,
        target_arr: float = 0.15,
        auto_register: bool = True,
    ):
        self.data_path = data_path
        self.max_iterations = max_iterations
        self.factor_budget = factor_budget
        self.model_budget = model_budget
        self.target_arr = target_arr
        self.auto_register = auto_register
        self._result: Optional[ScenarioResult] = None
    
    def get_config(self) -> dict:
        """Get scenario configuration"""
        return {
            "max_iterations": self.max_iterations,
            "factor_budget": self.factor_budget,
            "model_budget": self.model_budget,
            "target_arr": self.target_arr,
            "auto_register": self.auto_register,
            "data_path": self.data_path,
        }
    
    def to_result(self, **kwargs) -> ScenarioResult:
        """Create a scenario result"""
        return ScenarioResult(
            scenario_name=self.name,
            **kwargs
        )


class FinancialReportScenario:
    """
    Scenario for extracting factors from financial reports.
    
    Reads financial reports (PDF, etc.) and extracts factor ideas
    based on the analysis and insights in the reports.
    """
    
    name = "Financial Report Factor Extraction"
    description = "Extract and implement factors from financial reports"
    
    def __init__(
        self,
        report_folder: str,
        max_factors: int = 10,
        auto_register: bool = True,
    ):
        self.report_folder = report_folder
        self.max_factors = max_factors
        self.auto_register = auto_register
        self._result: Optional[ScenarioResult] = None
    
    def get_config(self) -> dict:
        """Get scenario configuration"""
        return {
            "report_folder": self.report_folder,
            "max_factors": self.max_factors,
            "auto_register": self.auto_register,
        }
    
    def to_result(self, **kwargs) -> ScenarioResult:
        """Create a scenario result"""
        return ScenarioResult(
            scenario_name=self.name,
            **kwargs
        )


class PaperModelScenario:
    """
    Scenario for extracting models from research papers.
    
    Reads research papers and implements the model structures
    described in them.
    """
    
    name = "Paper Model Extraction"
    description = "Extract and implement models from research papers"
    
    def __init__(
        self,
        paper_url: str,
        auto_save: bool = True,
    ):
        self.paper_url = paper_url
        self.auto_save = auto_save
        self._result: Optional[ScenarioResult] = None
    
    def get_config(self) -> dict:
        """Get scenario configuration"""
        return {
            "paper_url": self.paper_url,
            "auto_save": self.auto_save,
        }
    
    def to_result(self, **kwargs) -> ScenarioResult:
        """Create a scenario result"""
        return ScenarioResult(
            scenario_name=self.name,
            **kwargs
        )


SCENARIO_REGISTRY = {
    "factor_evolution": QlibFactorScenario,
    "model_evolution": QlibModelScenario,
    "quant_co_optimization": QlibQuantScenario,
    "financial_report": FinancialReportScenario,
    "paper_model": PaperModelScenario,
}


def get_scenario(name: str, **kwargs):
    """
    Get a scenario by name.
    
    Args:
        name: Scenario name
        **kwargs: Arguments to pass to scenario constructor
        
    Returns:
        Scenario instance
    """
    if name not in SCENARIO_REGISTRY:
        raise ValueError(f"Unknown scenario: {name}. Available: {list(SCENARIO_REGISTRY.keys())}")
    
    return SCENARIO_REGISTRY[name](**kwargs)


def list_scenarios() -> dict:
    """
    List all available scenarios.
    
    Returns:
        dict: Scenario names and their descriptions
    """
    return {
        name: {
            "class": cls,
            "name": cls.name,
            "description": cls.description,
        }
        for name, cls in SCENARIO_REGISTRY.items()
    }
