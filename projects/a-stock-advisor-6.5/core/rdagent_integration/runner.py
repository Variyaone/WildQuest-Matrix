"""
RDAgent Runner

Execute RDAgent scenarios.
"""

import subprocess
import os
from typing import Optional, List
from pathlib import Path

from .config import RDAgentConfig, RDAgentScenario


class RDAgentRunner:
    def __init__(self, config: Optional[RDAgentConfig] = None):
        self.config = config or RDAgentConfig()
        self.config.ensure_log_dir()
    
    def _get_env(self) -> dict:
        env = os.environ.copy()
        
        if self.config.env_file and Path(self.config.env_file).exists():
            env["DOTENV_PATH"] = self.config.env_file
        
        return env
    
    def _run_command(self, cmd: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            cmd,
            env=self._get_env(),
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True
        )
    
    def run_fin_factor(self, log_path: Optional[str] = None) -> subprocess.CompletedProcess:
        cmd = [self.config.get_rdagent_path(), "fin_factor"]
        if log_path:
            cmd.extend(["--path", log_path])
        else:
            cmd.extend(["--path", self.config.log_dir])
        
        return self._run_command(cmd)
    
    def run_fin_model(self, log_path: Optional[str] = None) -> subprocess.CompletedProcess:
        cmd = [self.config.get_rdagent_path(), "fin_model"]
        if log_path:
            cmd.extend(["--path", log_path])
        else:
            cmd.extend(["--path", self.config.log_dir])
        
        return self._run_command(cmd)
    
    def run_fin_quant(self, log_path: Optional[str] = None) -> subprocess.CompletedProcess:
        cmd = [self.config.get_rdagent_path(), "fin_quant"]
        if log_path:
            cmd.extend(["--path", log_path])
        else:
            cmd.extend(["--path", self.config.log_dir])
        
        return self._run_command(cmd)
    
    def run_fin_factor_report(
        self, 
        report_folder: str, 
        log_path: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        cmd = [self.config.get_rdagent_path(), "fin_factor_report", "--report-folder", report_folder]
        if log_path:
            cmd.extend(["--log-dir", log_path])
        else:
            cmd.extend(["--log-dir", self.config.log_dir])
        
        return self._run_command(cmd)
    
    def run_general_model(
        self, 
        paper_url: str, 
        log_path: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        cmd = [self.config.get_rdagent_path(), "general_model", paper_url]
        if log_path:
            cmd.extend(["--log-dir", log_path])
        else:
            cmd.extend(["--log-dir", self.config.log_dir])
        
        return self._run_command(cmd)
    
    def run_data_science(
        self, 
        competition: str, 
        log_path: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        cmd = [self.config.get_rdagent_path(), "data_science", "--competition", competition]
        if log_path:
            cmd.extend(["--log-dir", log_path])
        else:
            cmd.extend(["--log-dir", self.config.log_dir])
        
        return self._run_command(cmd)
    
    def run_scenario(
        self, 
        scenario: RDAgentScenario, 
        **kwargs
    ) -> subprocess.CompletedProcess:
        if scenario == RDAgentScenario.FIN_FACTOR:
            return self.run_fin_factor(**kwargs)
        elif scenario == RDAgentScenario.FIN_MODEL:
            return self.run_fin_model(**kwargs)
        elif scenario == RDAgentScenario.FIN_QUANT:
            return self.run_fin_quant(**kwargs)
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
    
    def health_check(self) -> dict:
        result = {
            "rdagent_installed": False,
            "venv_exists": False,
            "env_file_exists": False,
            "log_dir_exists": False,
        }
        
        try:
            check_result = self._run_command([self.config.get_rdagent_path(), "--help"])
            result["rdagent_installed"] = check_result.returncode == 0
        except Exception:
            pass
        
        if self.config.venv_path:
            result["venv_exists"] = Path(self.config.venv_path).exists()
        
        if self.config.env_file:
            result["env_file_exists"] = Path(self.config.env_file).exists()
        
        if self.config.log_dir:
            result["log_dir_exists"] = Path(self.config.log_dir).exists()
        
        return result
