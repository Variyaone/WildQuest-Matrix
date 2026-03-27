"""
RDAgent Utility Functions

Helper functions for RDAgent integration.
"""

import subprocess
import sys
from typing import Optional


def check_rdagent_installed() -> tuple[bool, Optional[str]]:
    """
    Check if RDAgent is installed.
    
    Returns:
        tuple: (is_installed, version_or_error_message)
    """
    try:
        import rdagent
        version = getattr(rdagent, '__version__', 'unknown')
        return True, version
    except ImportError:
        return False, "RDAgent is not installed. Run: pip install rdagent"


def get_rdagent_version() -> Optional[str]:
    """
    Get RDAgent version if installed.
    
    Returns:
        str or None: Version string or None if not installed
    """
    is_installed, version_or_error = check_rdagent_installed()
    if is_installed:
        return version_or_error
    return None


def check_docker_available() -> tuple[bool, str]:
    """
    Check if Docker is available and running.
    
    Returns:
        tuple: (is_available, message)
    """
    try:
        result = subprocess.run(
            ["docker", "run", "--rm", "hello-world"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, "Docker is available and running"
        else:
            return False, f"Docker is installed but not running properly: {result.stderr}"
    except FileNotFoundError:
        return False, "Docker is not installed. Please install Docker first."
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    except Exception as e:
        return False, f"Error checking Docker: {str(e)}"


def check_port_available(port: int) -> tuple[bool, str]:
    """
    Check if a port is available.
    
    Args:
        port: Port number to check
        
    Returns:
        tuple: (is_available, message)
    """
    import socket
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True, f"Port {port} is available"
    except socket.error:
        return False, f"Port {port} is already in use"


def run_health_check() -> dict:
    """
    Run comprehensive health check for RDAgent.
    
    Returns:
        dict: Health check results
    """
    results = {
        "rdagent_installed": False,
        "rdagent_version": None,
        "docker_available": False,
        "docker_message": None,
        "port_available": False,
        "port_message": None,
        "all_checks_passed": False,
    }
    
    rdagent_ok, rdagent_msg = check_rdagent_installed()
    results["rdagent_installed"] = rdagent_ok
    results["rdagent_version"] = rdagent_msg if rdagent_ok else None
    
    docker_ok, docker_msg = check_docker_available()
    results["docker_available"] = docker_ok
    results["docker_message"] = docker_msg
    
    port_ok, port_msg = check_port_available(19899)
    results["port_available"] = port_ok
    results["port_message"] = port_msg
    
    results["all_checks_passed"] = rdagent_ok and docker_ok
    
    return results


def install_rdagent() -> tuple[bool, str]:
    """
    Install RDAgent package.
    
    Returns:
        tuple: (success, message)
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "rdagent"],
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode == 0:
            return True, "RDAgent installed successfully"
        else:
            return False, f"Installation failed: {result.stderr}"
    except subprocess.TimeoutExpired:
        return False, "Installation timed out"
    except Exception as e:
        return False, f"Installation error: {str(e)}"


def get_llm_status() -> dict:
    """
    Check LLM API configuration status.
    
    Returns:
        dict: Status of various LLM providers
    """
    import os
    
    status = {
        "openai": {
            "configured": bool(os.getenv("OPENAI_API_KEY")),
            "api_base": os.getenv("OPENAI_API_BASE", "default"),
        },
        "deepseek": {
            "configured": bool(os.getenv("DEEPSEEK_API_KEY")),
        },
        "azure": {
            "configured": bool(os.getenv("AZURE_API_KEY") and os.getenv("AZURE_API_BASE")),
            "api_base": os.getenv("AZURE_API_BASE"),
        },
        "siliconflow": {
            "configured": bool(os.getenv("LITELLM_PROXY_API_KEY")),
        },
    }
    
    return status


def format_health_report(health: dict) -> str:
    """
    Format health check results as a readable report.
    
    Args:
        health: Health check results dict
        
    Returns:
        str: Formatted report
    """
    lines = [
        "=" * 50,
        "RDAgent 环境检查报告",
        "=" * 50,
        "",
    ]
    
    if health["rdagent_installed"]:
        lines.append(f"✓ RDAgent 已安装 (版本: {health['rdagent_version']})")
    else:
        lines.append("✗ RDAgent 未安装")
        lines.append("  安装命令: pip install rdagent")
    
    if health["docker_available"]:
        lines.append("✓ Docker 可用")
    else:
        lines.append(f"✗ Docker 不可用: {health['docker_message']}")
    
    if health["port_available"]:
        lines.append(f"✓ 端口 19899 可用")
    else:
        lines.append(f"△ {health['port_message']}")
    
    lines.extend([
        "",
        "=" * 50,
    ])
    
    if health["all_checks_passed"]:
        lines.append("状态: ✓ 所有检查通过，可以使用 RDAgent")
    else:
        lines.append("状态: ✗ 部分检查未通过，请先解决上述问题")
    
    return "\n".join(lines)
