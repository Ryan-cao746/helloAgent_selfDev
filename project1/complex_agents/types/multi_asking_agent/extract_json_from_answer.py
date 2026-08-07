import json
import re


def extract_json_from_answer(text: str) -> dict:
    """
    从带有 <ANSWER> 标签的文本中提取 JSON 对象。
    假设 JSON 位于 <ANSWER> 和 </ANSWER> 之间。
    """
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
    """打印 operations 数组中的每条操作"""
    ops = data.get("operations", [])
    if not ops:
        print("没有找到 operations 数组")
        return

    print(f"共找到 {len(ops)} 条操作：\n")
    for idx, op in enumerate(ops, 1):
        print(f"--- 操作 {idx} ---")
        print(f"操作类型: {op.get('operation', 'N/A')}")
        print(f"摘要: {op.get('summary', 'N/A')}")
        print(f"目标记忆: {op.get('target_memory', 'N/A')}")
        print(f"推理: {op.get('reasoning', 'N/A')}")
        print()


def main():
    # 示例输入（就是您提供的文本）
    sample_text = """
你的回答（必须是一个合法的 JSON）：
<ANSWER>
{
  "operations": [
    {
      "operation": "UPDATE",
      "summary": "用户姓名从张三更新为张伟",
      "target_memory": "user: 我叫张三，今年28岁",
      "reasoning": "工作记忆明确改名，需修正旧姓名，年龄28岁保持不变（无需重复操作）。"
    },
    {
      "operation": "DELETE",
      "summary": "用户居住地由北京变更为杭州，删除旧地址",
      "target_memory": "user: 我住在北京",
      "reasoning": "新信息直接覆盖旧地址，旧地址失效。"
    },
    {
      "operation": "DELETE",
      "summary": "用户饮食由素食改为非素食，删除旧饮食限制",
      "target_memory": "user: 我是素食主义者",
      "reasoning": "新信息明确否定旧饮食习惯，直接删除。"
    },
    {
      "operation": "ADD",
      "summary": "用户当前位于杭州，寻求杭州火锅店推荐",
      "target_memory": "",
      "reasoning": "工作记忆产生了新的位置关联信息，历史无此记录。"
    },
    {
      "operation": "ADD",
      "summary": "用户虽不再素食但仍有花生过敏史，推荐火锅店需绝对避免花生及花生酱",
      "target_memory": "",
      "reasoning": "结合历史'对花生过敏'和当前'推荐火锅店'，联合推理衍生出安全警示记忆。"
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