#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent权限管理器
用于自动化管理Agent的工具权限配置
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from copy import deepcopy

# 配置文件路径
OPENCLAW_CONFIG = Path.home() / ".openclaw" / "openclaw.json"
TEMPLATES_FILE = Path(__file__).parent / "template_definitions.json"
COMMANDER_DIR = Path(__file__).parent


# 权限模板定义
PERMISSION_TEMPLATES = {
    "full": {
        "name": "全功能",
        "description": "获得所有工具权限（session/system工具除外）",
        "tools": {
            "profile": "full"
        }
    },
    "researcher": {
        "name": "研究员",
        "description": "数据分析 + 网络研究",
        "tools": {
            "allow": [
                "read", "write", "edit", "exec", "process",
                "web_search", "web_fetch", "browser", "canvas",
                "memory_search", "memory_get"
            ]
        }
    },
    "architect": {
        "name": "架构师",
        "description": "架构设计 + 代码实现",
        "tools": {
            "profile": "coding",
            "allow": [
                "read", "write", "edit", "exec", "process",
                "web_search", "web_fetch"
            ]
        }
    },
    "creator": {
        "name": "创作者",
        "description": "文档 + 代码生成，继承architect",
        "inherits": "architect",
        "tools": {
            "allow": [
                "read", "write", "edit", "exec",
                "web_search", "web_fetch"
            ]
        }
    },
    "critic": {
        "name": "评审官",
        "description": "只读 + 审核，无执行权限",
        "tools": {
            "profile": "coding",
            "allow": [
                "read", "write", "edit", "web_search"
            ]
        }
    },
    "minimal": {
        "name": "最小权限",
        "description": "仅读 + 网络搜索（测试/临时使用）",
        "tools": {
            "allow": [
                "read", "web_search", "web_fetch"
            ]
        }
    }
}


class PermissionManager:
    """Agent权限管理器"""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or OPENCLAW_CONFIG
        self.config = None
        self.load_config()

    def load_config(self) -> bool:
        """加载配置文件"""
        if not self.config_path.exists():
            print(f"❌ 配置文件不存在: {self.config_path}")
            return False

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            print(f"✅ 配置文件加载成功: {self.config_path}")
            return True
        except json.JSONDecodeError as e:
            print(f"❌ 配置文件JSON格式错误: {e}")
            return False
        except Exception as e:
            print(f"❌ 加载配置文件失败: {e}")
            return False

    def save_config(self, backup: bool = True) -> bool:
        """保存配置文件"""
        if self.config is None:
            print("❌ 配置未加载")
            return False

        try:
            # 备份
            if backup:
                backup_path = self.config_path.with_suffix('.json.bak')
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    backup_path.write_text(f.read(), encoding='utf-8')
                print(f"💾 已备份配置文件: {backup_path}")

            # 保存
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置文件保存成功: {self.config_path}")
            return True
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
            return False

    def get_agents(self) -> List[Dict]:
        """获取所有Agent列表"""
        if self.config is None:
            return []
        return self.config.get('agents', {}).get('list', [])

    def get_agent_by_id(self, agent_id: str) -> Optional[Dict]:
        """根据ID获取Agent"""
        for agent in self.get_agents():
            if agent.get('id') == agent_id:
                return agent
        return None

    def resolve_template(self, template_name: str) -> Dict:
        """解析模板，处理继承关系"""
        if template_name not in PERMISSION_TEMPLATES:
            print(f"⚠️  模板不存在: {template_name}")
            return {}

        template = deepcopy(PERMISSION_TEMPLATES[template_name])

        # 处理继承
        while 'inherits' in template:
            parent_name = template['inherits']

            # 支持多继承（列表）
            if isinstance(parent_name, list):
                for pn in parent_name:
                    if pn in PERMISSION_TEMPLATES:
                        parent = deepcopy(PERMISSION_TEMPLATES[pn])
                        # 合并工具
                        parent_tools = parent.get('tools', {})
                        template_tools = template.get('tools', {})

                        # 合并allow列表
                        parent_allow = parent_tools.get('allow', [])
                        template_allow = template_tools.get('allow', [])

                        if parent_name[0] == parent_name:  # 第一个父模板作为主模板
                            template['tools'] = parent_tools
                            template['name'] = parent.get('name', template.get('name'))
                            template['description'] = parent.get('description', template.get('description'))

                        merged_allow = list(set(parent_allow + template_allow))
                        template['tools']['allow'] = merged_allow

                del template['inherits']
            else:
                parent = PERMISSION_TEMPLATES[parent_name]
                parent_tools = parent.get('tools', {})
                template_tools = template.get('tools', {})

                # 合并allow列表
                parent_allow = parent_tools.get('allow', [])
                template_allow = template_tools.get('allow', [])

                merged_allow = list(set(parent_allow + template_allow))

                # 子模板覆盖父模板
                template['tools'] = parent_tools
                template['tools']['allow'] = merged_allow

                # 添加元数据
                if 'name' not in template:
                    template['name'] = parent.get('name', '')
                if 'description' not in template:
                    template['description'] = parent.get('description', '')

                # 处理父模板的继承
                if 'inherits' in parent:
                    template['inherits'] = parent['inherits']
                else:
                    del template['inherits']

        return template

    def apply_template(self, agent_id: str, template_name: str,
                       additional_tools: Optional[List[str]] = None,
                       deny_tools: Optional[List[str]] = None) -> bool:
        """为Agent应用权限模板"""
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            print(f"❌ Agent不存在: {agent_id}")
            return False

        template = self.resolve_template(template_name)
        if not template:
            return False

        # 应用模板
        agent['tools'] = deepcopy(template['tools'])
        agent['_template'] = template_name  # 记录使用的模板

        # 添加额外工具
        if additional_tools:
            if 'allow' not in agent['tools']:
                agent['tools']['allow'] = []
            agent['tools']['allow'].extend(additional_tools)
            agent['tools']['allow'] = list(set(agent['tools']['allow']))

        # 移除工具（deny优先）
        if deny_tools:
            if 'allow' in agent['tools']:
                for tool in deny_tools:
                    if tool in agent['tools']['allow']:
                        agent['tools']['allow'].remove(tool)
            agent['tools']['deny'] = agent['tools'].get('deny', []) + deny_tools

        print(f"✅ 已为Agent '{agent_id}'应用模板 '{template_name}'")
        return True

    def list_permissions(self, agent_id: Optional[str] = None) -> None:
        """列出Agent权限"""
        agents = [self.get_agent_by_id(agent_id)] if agent_id else self.get_agents()
        agents = [a for a in agents if a is not None]

        if not agents:
            print("❌ 没有找到Agent")
            return

        print("\n" + "=" * 60)
        print("📋 Agent权限列表")
        print("=" * 60)

        for agent in agents:
            agent_id = agent.get('id')
            agent_name = agent.get('name')
            tools = agent.get('tools', {})
            template = agent.get('_template', '未设置')

            print(f"\n🤖 {agent_name} ({agent_id})")
            print(f"   模板: {template}")

            if 'profile' in tools:
                print(f"   配置: profile = {tools['profile']}")

            if 'allow' in tools:
                print(f"   允许: {', '.join(tools['allow'])}")

            if 'deny' in tools:
                print(f"   拒绝: {', '.join(tools['deny'])}")

            print("-" * 60)

    def validate_permissions(self) -> List[Dict]:
        """验证权限配置，返回问题列表"""
        issues = []

        for agent in self.get_agents():
            agent_id = agent.get('id')
            tools = agent.get('tools', {})

            # 检查工具有效性
            all_tools = tools.get('allow', [])
            deny_tools = tools.get('deny', [])

            # 检查deny中的工具是否在allow中
            for deny in deny_tools:
                if deny not in all_tools:
                    issues.append({
                        'agent': agent_id,
                        'type': 'redundant_deny',
                        'message': f"'{deny}'在deny列表中但不在allow列表中"
                    })

            # 检查profile和allow同时存在
            if 'profile' in tools and 'allow' in tools:
                issues.append({
                    'agent': agent_id,
                    'type': 'conflict',
                    'message': "profile和allow同时存在，profile可能被忽略"
                })

        return issues

    def migrate_to_template(self, agent_id: str, template_name: str,
                           dry_run: bool = True) -> bool:
        """将Agent迁移到模板引用（重构方案A）"""
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            print(f"❌ Agent不存在: {agent_id}")
            return False

        if template_name not in PERMISSION_TEMPLATES:
            print(f"❌ 模板不存在: {template_name}")
            return False

        original_tools = deepcopy(agent.get('tools', {}))

        if dry_run:
            print(f"\n🔍 迁移预览: {agent['name']} ({agent_id})")
            print(f"   原始配置: {json.dumps(original_tools, indent=6)}")
            print(f"   新配置:   {{\"template\": \"{template_name}\"}}")
            return True

        # 执行迁移
        agent['tools'] = {"template": template_name}
        agent['_template'] = template_name

        print(f"✅ 已迁移Agent '{agent_id}'到模板 '{template_name}'")
        return True

    def export_permissions(self) -> Dict:
        """导出当前所有Agent的权限配置（重构方案B）"""
        permissions = {
            "version": "1.0",
            "templates": deepcopy(PERMISSION_TEMPLATES),
            "agents": {}
        }

        for agent in self.get_agents():
            agent_id = agent.get('id')
            tools = agent.get('tools', {})
            template = agent.get('_template', 'custom')

            permissions['agents'][agent_id] = {
                "template": template,
                "tools": tools
            }

        return permissions

    def import_permissions(self, permissions: Dict, dry_run: bool = True) -> bool:
        """导入权限配置（重构方案B）"""
        print("\n🔍 导入权限配置")
        print(f"   版本: {permissions.get('version', 'unknown')}")
        print(f"   Agent数: {len(permissions.get('agents', {}))}")

        if dry_run:
            print("   🔍 预览模式（不实际修改）")
            for agent_id, config in permissions.get('agents', {}).items():
                print(f"   - {agent_id}: template={config.get('template')}")
            return True

        # 执行导入
        for agent_id, config in permissions.get('agents', {}).items():
            agent = self.get_agent_by_id(agent_id)
            if agent:
                agent['tools'] = config['tools']
                if 'template' in config:
                    agent['_template'] = config['template']
                print(f"   ✅ 已更新: {agent_id}")

        return True

    def compare_with_template(self, agent_id: str, template_name: str) -> bool:
        """比较Agent当前工具与模板的差异"""
        agent = self.get_agent_by_id(agent_id)
        if not agent:
            print(f"❌ Agent不存在: {agent_id}")
            return False

        template = self.resolve_template(template_name)
        if not template:
            return False

        current_tools = set(agent.get('tools', {}).get('allow', []))
        template_tools = set(template.get('tools', {}).get('allow', []))

        # 计算差异
        missing = template_tools - current_tools
        extra = current_tools - template_tools

        print(f"\n🔍 权限对比: {agent_id} vs {template_name}")
        print(f"   当前工具数: {len(current_tools)}")
        print(f"   模板工具数: {len(template_tools)}")

        if missing:
            print(f"\n   ❌ 缺失工具 ({len(missing)}):")
            for tool in sorted(missing):
                print(f"      - {tool}")

        if extra:
            print(f"\n   ⚠️  额外工具 ({len(extra)}):")
            for tool in sorted(extra):
                print(f"      + {tool}")

        if not missing and not extra:
            print("\n   ✅ 权限完全一致")
            return True

        return False


def main():
    """命令行入口"""
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    manager = PermissionManager()
    command = sys.argv[1].lower()

    if command == "list":
        agent_id = sys.argv[2] if len(sys.argv) > 2 else None
        manager.list_permissions(agent_id)

    elif command == "apply":
        if len(sys.argv) < 3:
            print("❌ 参数不足: apply <agent_id> <template> [additional_tools...]")
            sys.exit(1)
        agent_id = sys.argv[2]
        template = sys.argv[3]
        additional_tools = sys.argv[4:] if len(sys.argv) > 4 else None
        manager.apply_template(agent_id, template, additional_tools)
        manager.save_config()

    elif command == "validate":
        issues = manager.validate_permissions()
        if not issues:
            print("✅ 权限配置验证通过")
        else:
            print(f"⚠️  发现 {len(issues)} 个问题:")
            for issue in issues:
                print(f"   - {issue['agent']}: {issue['message']}")

    elif command == "migrate":
        if len(sys.argv) < 3:
            print("❌ 参数不足: migrate <agent_id> <template> [--apply]")
            sys.exit(1)
        agent_id = sys.argv[2]
        template = sys.argv[3]
        dry_run = "--apply" not in sys.argv
        manager.migrate_to_template(agent_id, template, dry_run)
        if not dry_run:
            manager.save_config()

    elif command == "compare":
        if len(sys.argv) < 3:
            print("❌ 参数不足: compare <agent_id> <template>")
            sys.exit(1)
        agent_id = sys.argv[2]
        template = sys.argv[3]
        manager.compare_with_template(agent_id, template)

    elif command == "export":
        permissions = manager.export_permissions()
        output_path = COMMANDER_DIR / "agent_permissions.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(permissions, f, indent=2, ensure_ascii=False)
        print(f"✅ 权限配置已导出: {output_path}")

    elif command == "import":
        if len(sys.argv) < 3:
            print("❌ 参数不足: import <config.json> [--apply]")
            sys.exit(1)
        input_path = Path(sys.argv[2])
        if not input_path.exists():
            print(f"❌ 文件不存在: {input_path}")
            sys.exit(1)
        with open(input_path, 'r', encoding='utf-8') as f:
            permissions = json.load(f)
        dry_run = "--apply" not in sys.argv
        manager.import_permissions(permissions, dry_run)
        if not dry_run:
            manager.save_config()

    else:
        print(f"❌ 未知命令: {command}")
        print_usage()
        sys.exit(1)


def print_usage():
    """打印使用说明"""
    print("""
🔐 Agent权限管理器

用法:
  agent_permission_manager.py <command> [args...]

命令:
  list [agent_id]              列出Agent权限（可选指定agent_id）
  apply <agent_id> <template>  为Agent应用权限模板
  validate                     验证权限配置
  migrate <agent_id> <template> 迁移Agent到模板引用 [--apply执行]
  compare <agent_id> <template> 比较Agent与模板的差异
  export                       导出权限配置到JSON文件
  import <config.json>         导入权限配置 [--apply执行]

可用模板:
  full     - 全功能（系统管理员）
  researcher - 研究员（数据分析+网络研究）
  architect - 架构师（架构设计+代码）
  creator  - 创作者（文档+代码生成）
  critic   - 评审官（只读+审核）
  minimal  - 最小权限（测试使用）

示例:
  python agent_permission_manager.py list
  python agent_permission_manager.py apply researcher researcher
  python agent_permission_manager.py validate
  python agent_permission_manager.py compare researcher researcher
""")


if __name__ == "__main__":
    main()
