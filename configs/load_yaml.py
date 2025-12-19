import yaml
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass
class Card:
    """
    卡牌对象类
    """
    index: int  # [关键] 从0开始的自动分配ID，用于矩阵/Tensor索引
    id: str  # 原始字符串ID (如 BG20_102)
    name_zh: str  # 中文名
    tech_level: int  # 酒馆等级
    raw_data: Dict[str, Any] = field(default_factory=dict)  # 保留完整原始数据


class CardDatabase:
    def __init__(self, yaml_path: str):
        # 两个查找表，方便双向索引
        self.cards_by_index: List[Card] = []  # Int -> Card (O(1)查找)
        self.cards_by_str_id: Dict[str, Card] = {}  # String -> Card (O(1)查找)

        self._load_and_assign_ids(yaml_path)

    def _load_and_assign_ids(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                raw_list = yaml.safe_load(f)

            if not raw_list:
                print("警告: YAML 文件为空")
                return

            # === 核心逻辑：使用 enumerate 自动分配从0开始的索引 ===
            for idx, item in enumerate(raw_list):
                # 创建卡牌对象
                card = Card(
                    index=idx,  # 这里被赋值为 0, 1, 2...
                    id=item['id'],
                    name_zh=item['name']['zh'],
                    tech_level=item.get('tech_level', 0),
                    raw_data=item
                )

                # 存入数据库
                self.cards_by_index.append(card)
                self.cards_by_str_id[card.id] = card

            print(f"成功加载 {len(self.cards_by_index)} 张卡牌。")
            print(f"ID 范围: 0 ~ {len(self.cards_by_index) - 1}")

        except Exception as e:
            print(f"加载出错: {e}")

    def get_card_by_index(self, idx: int) -> Optional[Card]:
        """通过数字ID获取卡牌（用于模型输出解析）"""
        if 0 <= idx < len(self.cards_by_index):
            return self.cards_by_index[idx]
        return None

    def get_index_by_id(self, str_id: str) -> int:
        """通过字符串ID获取数字ID（用于生成One-hot Label）"""
        card = self.cards_by_str_id.get(str_id)
        return card.index if card else -1

    @property
    def total_cards(self) -> int:
        return len(self.cards_by_index)


# ==========================================
# 使用示例
# ==========================================
if __name__ == "__main__":
    # 假设你的配置文件叫 cards.yaml
    db = CardDatabase("cards.yaml")

    # 场景 1: 遍历检查 ID 分配情况
    print("\n=== ID 分配预览 ===")
    for card in db.cards_by_index[:3]:  # 只看前3个
        print(f"Index [{card.index}] -> {card.name_zh} (原ID: {card.id})")

    # 场景 2: 模拟神经网络输出
    # 假设模型输出了 index=1 的动作
    model_output_action_idx = 1
    selected_card = db.get_card_by_index(model_output_action_idx)
    if selected_card:
        print(f"\n模型选择了: {selected_card.name_zh}")
        # 访问深层 YAML 数据
        print(f"效果描述: {selected_card.raw_data['mechanics']['effect_config']['desc']}")
