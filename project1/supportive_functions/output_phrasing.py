import re

# 两个字符串模式匹配的工具方法
def phrase_output(text:str):
    """提取thought和action"""
    # Thought要匹配到Action:或文本末尾
    thought_match = re.search(r"Thought:\s*(.*?)(?=Action:|$)", text, re.DOTALL) # 跳过 Thought: 后面可能存在的空白。非贪婪、条件地捕获内容直到Action:或文末。re.DOTALL指让正则表达式中的点号（.）匹配包括换行符（\n）在内的任意字符。

    # Action要匹配到文本末尾
    action_match = re.search(r"Action:\s*(.*?)$", text, re.DOTALL)
    thought = thought_match.group(1).strip() if thought_match else None
    action = action_match.group(1).strip() if action_match else None
    return thought, action

def phrase_action(action_text:str):
    """从action里提取tool_calls"""
    match = re.match(r"(\w+)\[(.*)]", action_text, re.DOTALL) # 方括号前和后的分别为两个捕获组
    if match:
        return match.group(1), match.group(2)
    return None, None