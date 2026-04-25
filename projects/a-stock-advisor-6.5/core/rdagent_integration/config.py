"""
RDAgent Configuration

Configuration for RDAgent integration.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import os
from pathlib import Path


class RDAgentScenario(Enum):
    FIN_FACTOR = "fin_factor"
    FIN_MODEL = "fin_model"
    FIN_QUANT = "fin_quant"
    FIN_FACTOR_REPORT = "fin_factor_report"
    GENERAL_MODEL = "general_model"
    DATA_SCIENCE = "data_science"


@dataclass
class RDAgentConfig:
    log_dir: Optional[str] = None
    venv_path: Optional[str] = None
    env_file: Optional[str] = None
    
    def __post_init__(self):
        if self.venv_path is None:
            project_root = Path(__file__).parent.parent.parent
            self.venv_path = str(project_root / ".venv-rdagent")
        
        if self.log_dir is None:
            project_root = Path(__file__).parent.parent.parent
            self.log_dir = str(project_root / "log" / "rdagent")
        
        if self.env_file is None:
            project_root = Path(__file__).parent.parent.parent
            self.env_file = str(project_root / ".env.rdagent")
    
    def get_python_path(self) -> str:
        if self.venv_path:
            return os.path.join(self.venv_path, "bin", "python")
        return "python3"
    
    def get_rdagent_path(self) -> str:
        if self.venv_path:
            return os.path.join(self.venv_path, "bin", "rdagent")
        return "rdagent"
    
    def ensure_log_dir(self):
        Path(self.log_dir).mkdir(parents=True, exist_ok=True)
