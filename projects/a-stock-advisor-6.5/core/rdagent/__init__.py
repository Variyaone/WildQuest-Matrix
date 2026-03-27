"""
RDAgent Integration Module

Integration with Microsoft RDAgent - the first data-centric multi-agent framework
for quantitative finance that automates factor-model co-optimization.

GitHub: https://github.com/microsoft/RD-Agent
Paper: R&D-Agent-Quant: A Multi-Agent Framework for Data-Centric Factors and Model Joint Optimization
"""

from core.rdagent.scen import QlibFactorScenario, QlibModelScenario, QlibQuantScenario
from core.rdagent.runner import RDAgentRunner
from core.rdagent.config import RDAgentConfig
from core.rdagent.utils import check_rdagent_installed, get_rdagent_version

__all__ = [
    'RDAgentRunner',
    'RDAgentConfig',
    'QlibFactorScenario',
    'QlibModelScenario',
    'QlibQuantScenario',
    'check_rdagent_installed',
    'get_rdagent_version',
]
