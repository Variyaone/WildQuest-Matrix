#!/usr/bin/env python3
"""
策略评估框架 - 快速评估策略可行性
专注于低频低成本策略
"""

class StrategyEvaluator:
    def __init__(self):
        self.strategies = []

    def evaluate(self, name, description, frequency, cost_sensitivity, expected_return, risk, difficulty, data_needs):
        """
        评估策略可行性

        Args:
            name: 策略名称
            description: 策略描述
            frequency: 交易频率（日/周/月）
            cost_sensitivity: 成本敏感度（高/中/低）
            expected_return: 预期年化收益
            risk: 风险等级（1-5）
            difficulty: 技术难度（1-5）
            data_needs: 数据需求（高/中/低）
        """
        # 低频策略评分（权重）
        scores = {
            'frequency': self._score_frequency(frequency),
            'cost': self._score_cost(cost_sensitivity),
            'return': self._score_return(expected_return),
            'risk': self._score_risk(risk, expected_return),
            'difficulty': 5 - difficulty,  # 越简单越好
            'data': self._score_data(data_needs)
        }

        total_score = sum(scores.values()) / len(scores)

        strategy = {
            'name': name,
            'description': description,
            'frequency': frequency,
            'cost_sensitivity': cost_sensitivity,
            'expected_return': expected_return,
            'risk': risk,
            'difficulty': difficulty,
            'data_needs': data_needs,
            'scores': scores,
            'total_score': total_score
        }

        self.strategies.append(strategy)
        return strategy

    def _score_frequency(self, freq):
        """低频策略评分"""
        if freq >= 20:  # 每日>20次
            return 0
        elif freq >= 10:  # 每日>10次
            return 3
        elif freq >= 1:  # 每日>1次
            return 4
        else:  # 每周或更少
            return 5

    def _score_cost(self, sensitivity):
        """成本敏感度评分"""
        if sensitivity == '低':
            return 5
        elif sensitivity == '中':
            return 3
        else:  # 高
            return 1

    def _score_return(self, ret):
        """预期收益评分"""
        if ret >= 20:
            return 5
        elif ret >= 10:
            return 4
        elif ret >= 5:
            return 3
        else:
            return 2

    def _score_risk(self, risk, ret):
        """风险调整收益评分"""
        if risk == 1 and ret >= 10:
            return 5
        elif risk == 2 and ret >= 15:
            return 4
        elif risk == 3 and ret >= 20:
            return 4
        elif risk == 4 and ret >= 25:
            return 3
        elif risk == 5 and ret >= 30:
            return 2
        else:
            return 2 - (risk - 3) * 0.5

    def _score_data(self, needs):
        """数据需求评分"""
        if needs == '低':
            return 5
        elif needs == '中':
            return 3
        else:
            return 1

    def rank_strategies(self):
        """排序策略"""
        return sorted(self.strategies, key=lambda x: x['total_score'], reverse=True)

    def print_ranking(self):
        """打印排名"""
        ranked = self.rank_strategies()

        print("\n" + "="*80)
        print("📊 策略可行性排名（低频低成本）")
        print("="*80)

        for i, s in enumerate(ranked, 1):
            print(f"\n#{i} {s['name']} - 评分: {s['total_score']:.2f}")
            print(f"   描述: {s['description']}")
            print(f"   频率: {s['frequency']}次/天 | 成本敏感: {s['cost_sensitivity']} | 预期年化: {s['expected_return']}%")
            print(f"   风险: {s['risk']}/5 | 难度: {s['difficulty']}/5 | 数据需求: {s['data_needs']}")

        print("\n" + "="*80)

if __name__ == "__main__":
    # 评估框架已创建，等待调研数据填充
    print("策略评估框架就绪")
