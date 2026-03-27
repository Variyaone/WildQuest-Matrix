"""
RDAgent Runner Module

Executes RDAgent scenarios and manages the workflow.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from core.rdagent.config import RDAgentConfig, RDAgentScenario
from core.rdagent.utils import check_rdagent_installed, run_health_check


class RDAgentRunner:
    """
    Runner for Microsoft RDAgent scenarios.
    
    Provides a simplified interface to run various RDAgent scenarios
    including factor mining, model evolution, and quant strategy development.
    """
    
    def __init__(self, config: Optional[RDAgentConfig] = None):
        """
        Initialize RDAgent runner.
        
        Args:
            config: RDAgent configuration. If None, loads from environment.
        """
        self.config = config or RDAgentConfig()
        self._check_environment()
    
    def _check_environment(self) -> None:
        """Check if RDAgent environment is properly set up."""
        is_installed, version_or_error = check_rdagent_installed()
        if not is_installed:
            raise RuntimeError(
                f"RDAgent is not installed. {version_or_error}\n"
                "Please install it with: pip install rdagent"
            )
    
    def _setup_env(self) -> dict:
        """Set up environment variables for RDAgent."""
        env = os.environ.copy()
        env.update(self.config.to_env_dict())
        return env
    
    def run_fin_quant(self, log_dir: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run factor and model joint evolution scenario.
        
        This is the most comprehensive scenario that co-optimizes
        factors and models together.
        
        Args:
            log_dir: Directory for logs. Defaults to config setting.
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        cmd = ["rdagent", "fin_quant"]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        
        return subprocess.run(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def run_fin_factor(self, log_dir: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run iterative factor evolution scenario.
        
        LLM proposes new factor ideas and implements them iteratively.
        
        Args:
            log_dir: Directory for logs
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        cmd = ["rdagent", "fin_factor"]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        
        return subprocess.run(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def run_fin_model(self, log_dir: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run iterative model evolution scenario.
        
        LLM proposes new model architectures and implements them iteratively.
        
        Args:
            log_dir: Directory for logs
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        cmd = ["rdagent", "fin_model"]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        
        return subprocess.run(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def run_fin_factor_report(self, report_folder: str, log_dir: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run factor extraction from financial reports.
        
        Extracts factor ideas from financial reports and implements them.
        
        Args:
            report_folder: Path to folder containing financial reports
            log_dir: Directory for logs
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        cmd = ["rdagent", "fin_factor_report", "--report-folder", report_folder]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        
        return subprocess.run(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def run_general_model(self, paper_url: str, log_dir: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run model extraction from research paper.
        
        Reads a research paper and implements the model structure.
        
        Args:
            paper_url: URL to the paper (e.g., arxiv URL)
            log_dir: Directory for logs
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        cmd = ["rdagent", "general_model", paper_url]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        
        return subprocess.run(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def run_data_science(self, competition: str, log_dir: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Run data science / Kaggle competition scenario.
        
        Automatically tunes models and engineers features for competitions.
        
        Args:
            competition: Competition name
            log_dir: Directory for logs
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        cmd = ["rdagent", "data_science", "--competition", competition]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        
        return subprocess.run(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def start_ui(self, port: int = 19899, log_dir: Optional[str] = None, data_science: bool = False) -> subprocess.Popen:
        """
        Start the RDAgent Streamlit UI.
        
        Args:
            port: Port for the UI server
            log_dir: Directory containing logs to display
            data_science: Whether to show data science scenario logs
            
        Returns:
            Popen: Process object for the running server
        """
        cmd = ["rdagent", "ui", "--port", str(port)]
        if log_dir:
            cmd.extend(["--log-dir", log_dir])
        if data_science:
            cmd.append("--data-science")
        
        return subprocess.Popen(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def start_server_ui(self, port: int = 19899) -> subprocess.Popen:
        """
        Start the RDAgent Web UI server.
        
        Args:
            port: Port for the server
            
        Returns:
            Popen: Process object for the running server
        """
        cmd = ["rdagent", "server_ui", "--port", str(port)]
        
        return subprocess.Popen(
            cmd,
            env=self._setup_env(),
            cwd=os.getcwd()
        )
    
    def run_health_check(self) -> dict:
        """
        Run health check for RDAgent environment.
        
        Returns:
            dict: Health check results
        """
        return run_health_check()
    
    def run_scenario(self, scenario: RDAgentScenario, **kwargs) -> subprocess.CompletedProcess:
        """
        Run a specific scenario by enum.
        
        Args:
            scenario: The scenario to run
            **kwargs: Additional arguments for the scenario
            
        Returns:
            CompletedProcess: Result of the subprocess run
        """
        if scenario == RDAgentScenario.FIN_QUANT:
            return self.run_fin_quant(**kwargs)
        elif scenario == RDAgentScenario.FIN_FACTOR:
            return self.run_fin_factor(**kwargs)
        elif scenario == RDAgentScenario.FIN_MODEL:
            return self.run_fin_model(**kwargs)
        elif scenario == RDAgentScenario.FIN_FACTOR_REPORT:
            report_folder = kwargs.get("report_folder")
            if not report_folder:
                raise ValueError("report_folder is required for FIN_FACTOR_REPORT scenario")
            return self.run_fin_factor_report(report_folder, **kwargs)
        elif scenario == RDAgentScenario.GENERAL_MODEL:
            paper_url = kwargs.get("paper_url")
            if not paper_url:
                raise ValueError("paper_url is required for GENERAL_MODEL scenario")
            return self.run_general_model(paper_url, **kwargs)
        elif scenario == RDAgentScenario.DATA_SCIENCE:
            competition = kwargs.get("competition")
            if not competition:
                raise ValueError("competition is required for DATA_SCIENCE scenario")
            return self.run_data_science(competition, **kwargs)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
