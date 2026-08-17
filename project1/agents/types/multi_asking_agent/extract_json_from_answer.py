"""解析摘要模型使用 ``<ANSWER>`` 标签包裹的 JSON 结果。"""

import json
import re


def extract_json_from_answer(text: str) -> dict:
    """提取 ``<ANSWER>`` 标签内的内容并解析为 JSON 对象。"""
    pattern = r'<ANSWER>\s*(.*?)\s*</ANSWER>'
    match = re.search(pattern, text, re.DOTALL)
    if not match:
        raise ValueError("未找到 <ANSWER> ... </ANSWER> 标签")

    json_str = match.group(1).strip()
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {e}\n原始内容: {json_str}")


def pretty_print_operations(data: dict):
    """以便于人工调试的格式打印每条记忆操作。"""
    ops = data.get("operations", [])
    if not ops:
        print("没有找到 operations 数组")
        return

    print(f"共找到 {len(ops)} 条操作：\n")
    for idx, op in enumerate(ops, 1):
        print(f"--- 操作 {idx} ---")
        print(f"操作类型: {op.get('operation', 'N/A')}")
        print(f"摘要: {op.get('summary', 'N/A')}")
        print(f"目标记忆ID: {op.get('target_id', 'N/A')}")   # 改为此字段
        print(f"推理: {op.get('reasoning', 'N/A')}")
        print()


def main():
    """使用内置示例演示摘要结果解析。"""
    sample_text = """
你的回答（必须是一个合法的 JSON）：
<ANSWER>
{
  "operations": [
    {
      "operation": "UPDATE",
      "summary": "用户姓名由李梅更正为王梅，姓改为王，名梅不变；职业平面设计师保持不变",
      "target_id": "simple_episodic-2026-08-08 17:54:27.093837",
      "reasoning": "工作记忆明确否定旧姓李，以新信息为准，修正姓名。"
    },
    {
      "operation": "UPDATE",
      "summary": "咖啡加奶偏好由燕麦奶更新为全脂牛奶",
      "target_id": "simple_episodic-2026-08-08 17:54:27.093912",
      "reasoning": "用户明确表示换回全脂牛奶，旧偏好被新偏好取代。"
    },
    {
      "operation": "ADD",
      "summary": "用户偏好安静的咖啡店",
      "target_id": "",
      "reasoning": "工作记忆中用户请求寻找安静咖啡店，隐含长期偏好。"
    },
    {
      "operation": "ADD",
      "summary": "用户对坚果过敏，推荐咖啡店时需注意避免含坚果成分的食品或饮品",
      "target_id": "",
      "reasoning": "结合历史过敏信息与当前咖啡店推荐请求，联合推理出安全注意事项。"
    }
  ]
}
</ANSWER>
    """

    try:
        parsed = extract_json_from_answer(sample_text)
        pretty_print_operations(parsed)
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    main()
