#!/usr/bin/env python3
"""
记忆强化训练 - 防止遗忘重要信息
"""

class MemoryTrainer:
    def __init__(self):
        self.config_index = '.commander/CONFIG_INDEX.md'

    def remind_okx_key(self):
        """
        记住：OKX模拟盘密钥在 okx-temp/okx_config.json
        这是模拟盘密钥，不是实盘！
        用途：资金费套利模拟盘测试，直接用API调用
        """
        return """
        ⚠️ 重要记忆：
        位置: okx-temp/okx_config.json
        用途: OKX模拟盘（simulated=true, sandbox=true）
        不要试图查找其他地方，密钥就在这里！
        """

    def remind_a_stock_issue(self):
        """
        记住：A股多因子回测发现过拟合
        样本内：29.76%，样本外：-4.95%
        原因：数据量太小（20只股票）
        解决：重新设计，接入真实数据
        """
        return """
        ⚠️ 重要记忆：
        A股项目发现严重过拟合
        当前状态：重新设计中
        不要再重复旧的回测结果！
        """

    def remind_okx_rule(self):
        """
        记住：OKX模拟盘必须用API
        回测：可本地
        模拟盘：必须用API（你的密钥就是模拟盘的）
        """
        return """
        ⚠️ 重要记忆：
        OKX模拟盘 = 直接用API调用
        不要建立线下模拟！
        你的密钥在: okx-temp/okx_config.json
        """

    def quick_check(self):
        """
        快速自查：避免混乱
        """
        print("\n=== 记忆强化自查 ===")
        print("1. OKX密钥位置？ -> okx-temp/okx_config.json ✅")
        print("2. 股项目状态？ -> 重新设计中（过拟合） ✅")
        print("3. OKX模拟盘规则？ -> 必须用API ✅")
        print("4. 配置目录？ -> CONFIG_INDEX.md ✅")
        print("===================\n")

if __name__ == "__main__":
    trainer = MemoryTrainer()
    trainer.quick_check()
