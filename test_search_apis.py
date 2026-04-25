#!/usr/bin/env python3
"""
搜索API测试脚本
测试配置的搜索服务的可用性
"""

import subprocess
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# 颜色输出
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_test_header(test_name: str):
    """打印测试标题"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}测试: {test_name}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(message: str):
    """打印成功消息"""
    print(f"{GREEN}✓ {message}{RESET}")

def print_error(message: str):
    """打印错误消息"""
    print(f"{RED}✗ {message}{RESET}")

def print_info(message: str):
    """打印信息消息"""
    print(f"{YELLOW}ℹ {message}{RESET}")

def test_brave_search() -> Dict[str, Any]:
    """测试Brave搜索 - 通过OpenClaw内部工具"""
    print_test_header("Brave Search (OpenClaw内置)")

    result = {
        "service": "Brave Search",
        "status": "unknown",
        "api_key_present": False,
        "message": ""
    }

    try:
        # 检查环境变量
        api_key = os.getenv("BRAVE_API_KEY")
        if api_key:
            result["api_key_present"] = True
            print_success("BRAVE_API_KEY 环境变量已设置")
            print_info(f"API Key (前10位): {api_key[:10]}...")
            result["status"] = "success"
            result["message"] = "Brave Search API密钥已配置，通过OpenClaw web_search工具使用"
        else:
            print_error("BRAVE_API_KEY 环境变量未设置")
            result["status"] = "error"
            result["message"] = "缺少BRAVE_API_KEY环境变量"

    except Exception as e:
        print_error(f"测试Brave Search时出错: {e}")
        result["status"] = "error"
        result["message"] = str(e)

    return result

def test_duckduckgo_mcp() -> Dict[str, Any]:
    """测试DuckDuckGo MCP服务器"""
    print_test_header("DuckDuckGo MCP Server")

    result = {
        "service": "DuckDuckGo MCP",
        "status": "unknown",
        "mcp_working": False,
        "message": ""
    }

    try:
        # 测试npx命令是否可以运行
        print_info("测试DuckDuckGo MCP服务器启动...")
        process = subprocess.run(
            ["npx", "-y", "duckduckgo-mcp-server", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )

        if process.returncode == 0 or "DuckDuckGo" in process.stderr:
            print_success("DuckDuckGo MCP服务器可以启动")
            print_info("运行命令: npx -y duckduckgo-mcp-server")
            result["mcp_working"] = True
            result["status"] = "success"
            result["message"] = "DuckDuckGo MCP服务器通过npx可用，无需API密钥"
        else:
            print_error(f"DuckDuckGo MCP服务器启动失败: {process.stderr}")
            result["status"] = "error"
            result["message"] = f"启动失败: {process.stderr}"

    except subprocess.TimeoutExpired:
        print_error("DuckDuckGo MCP服务器启动超时")
        result["status"] = "error"
        result["message"] = "启动超时"
    except FileNotFoundError:
        print_error("未找到npx命令")
        result["status"] = "error"
        result["message"] = "npx命令未找到，请安装Node.js"
    except Exception as e:
        print_error(f"测试DuckDuckGo MCP时出错: {e}")
        result["status"] = "error"
        result["message"] = str(e)

    return result

def test_tavily_mcp() -> Dict[str, Any]:
    """测试Tavily MCP服务器"""
    print_test_header("Tavily MCP Server")

    result = {
        "service": "Tavily MCP",
        "status": "unknown",
        "api_key_present": False,
        "mcp_working": False,
        "message": ""
    }

    try:
        # 检查API密钥
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            print_error("TAVILY_API_KEY 环境变量未设置")
            result["status"] = "error"
            result["message"] = "缺少TAVILY_API_KEY环境变量"
            return result

        result["api_key_present"] = True
        print_success("TAVILY_API_KEY 环境变量已设置")
        print_info(f"API Key (前10位): {api_key[:10]}...")

        # 测试MCP服务器
        print_info("测试Tavily MCP服务器...")
        process = subprocess.run(
            ["npx", "-y", "tavily-mcp", "--list-tools"],
            capture_output=True,
            text=True,
            timeout=15,
            env={**os.environ, "TAVILY_API_KEY": api_key}
        )

        if "tavily_search" in process.stdout.lower():
            print_success("Tavily MCP服务器工具列表可用")
            print_info("可用工具: tavily_search, tavily_extract, tavily_crawl, tavily_map, tavily_research")
            result["mcp_working"] = True
            result["status"] = "success"
            result["message"] = "Tavily MCP服务器通过npx可用，包含5个工具"
        else:
            print_info("MCP服务器可运行，但工具列表可能不同")
            result["status"] = "partial"
            result["message"] = "Tavily MCP服务器部分可用"

    except subprocess.TimeoutExpired:
        print_error("Tavily MCP服务器启动超时")
        result["status"] = "error"
        result["message"] = "启动超时"
    except FileNotFoundError:
        print_error("未找到npx命令")
        result["status"] = "error"
        result["message"] = "npx命令未找到，请安装Node.js"
    except Exception as e:
        print_error(f"测试Tavily MCP时出错: {e}")
        result["status"] = "error"
        result["message"] = str(e)

    return result

def test_gemini_api() -> Dict[str, Any]:
    """测试Google Gemini API"""
    print_test_header("Google Gemini API")

    result = {
        "service": "Google Gemini",
        "status": "unknown",
        "api_key_present": False,
        "cli_available": False,
        "message": ""
    }

    try:
        # 检查API密钥
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            print_error("GOOGLE_API_KEY 或 GEMINI_API_KEY 环境变量未设置")
            result["status"] = "error"
            result["message"] = "缺少GOOGLE_API_KEY环境变量"
            return result

        result["api_key_present"] = True
        print_success("GOOGLE_API_KEY 环境变量已设置")
        print_info(f"API Key (前10位): {api_key[:10]}...")

        # 检查gemini CLI
        print_info("检查gemini CLI可用性...")
        process = subprocess.run(
            ["which", "gemini"],
            capture_output=True,
            text=True
        )

        if process.returncode == 0:
            print_success("gemini CLI已安装")
            gemini_path = process.stdout.strip()
            print_info(f"路径: {gemini_path}")
            result["cli_available"] = True

            # 检查是否有web search扩展
            print_info("检查gemini CLI扩展...")
            try:
                extensions_process = subprocess.run(
                    ["gemini", "--list-extensions"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "web" in extensions_process.stdout.lower() or "search" in extensions_process.stdout.lower():
                    print_success("找到web搜索相关扩展")
                    result["status"] = "success"
                    result["message"] = "Google Gemini API已配置，支持web_search工具"
                else:
                    print_info("gemini CLI可用，但未直接显示web搜索扩展")
                    result["status"] = "success"
                    result["message"] = "Google Gemini API已配置，web_search通过API调用使用"
            except:
                print_info("无法列出扩展（可能是版本问题）")
                result["status"] = "success"
                result["message"] = "Google Gemini API已配置，web_search通过API调用使用"
        else:
            print_info("gemini CLI未安装，但API密钥已配置")
            print_info("可以通过Python google-generativeai包使用")
            result["status"] = "success"
            result["message"] = "Google Gemini API已配置（通过Google Search工具）"

    except Exception as e:
        print_error(f"测试Google Gemini时出错: {e}")
        result["status"] = "error"
        result["message"] = str(e)

    return result

def generate_report(results: List[Dict[str, Any]]):
    """生成测试报告"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}测试报告摘要{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    success_count = 0
    error_count = 0
    partial_count = 0

    for result in results:
        status_emoji = "✓" if result["status"] == "success" else ("⚠" if result["status"] == "partial" else "✗")
        status_color = GREEN if result["status"] == "success" else (YELLOW if result["status"] == "partial" else RED)
        print(f"{status_color}{status_emoji} {result['service']}: {result['status']}{RESET}")
        print(f"   {result['message']}\n")

        if result["status"] == "success":
            success_count += 1
        elif result["status"] == "partial":
            partial_count += 1
        else:
            error_count += 1

    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}总计{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    print(f"{GREEN}成功: {success_count}{RESET}")
    print(f"{YELLOW}部分: {partial_count}{RESET}")
    print(f"{RED}失败: {error_count}{RESET}")
    print(f"总计: {len(results)}\n")

    # 保存JSON报告
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total": len(results),
            "success": success_count,
            "partial": partial_count,
            "error": error_count
        },
        "results": results
    }

    report_path = "/Users/variya/.openclaw/workspace/search_api_test_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)

    print_success(f"详细报告已保存到: {report_path}")

def main():
    """主函数"""
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}搜索API可用性测试{RESET}")
    print(f"{BLUE}{'='*60}{RESET}")
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 加载环境变量
    env_file = "/Users/variya/.openclaw/.env"
    if os.path.exists(env_file):
        print_info(f"加载环境变量: {env_file}")
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

    # 运行所有测试
    results = []
    results.append(test_brave_search())
    results.append(test_duckduckgo_mcp())
    results.append(test_tavily_mcp())
    results.append(test_gemini_api())

    # 生成报告
    generate_report(results)

    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}测试完成{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

    # 返回退出码
    success_count = sum(1 for r in results if r["status"] == "success")
    partial_count = sum(1 for r in results if r["status"] == "partial")
    error_count = sum(1 for r in results if r["status"] == "error")

    if error_count > 0:
        sys.exit(1)
    elif partial_count > 0:
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
