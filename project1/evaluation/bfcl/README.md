# BFCL 轻量评估工具

这个模块把项目当前的 `HelloAgentsLLM.decide()` / `AgentDecision` 协议适配到 BFCL 单轮函数调用评估。它只测试模型是否生成正确的函数调用，不会注册或执行项目里的真实工具。

## 运行生成

```powershell
python -m project1.evaluation.bfcl run --dataset path\to\BFCL_v4_simple_python.json --category simple_python --model-name helloagent_prompt --output-root .bfcl_runs --limit 100 --temperature 0
```

输出文件：

- `.bfcl_runs/result/<model-name>/<dataset-stem>_result.json`
- `.bfcl_runs/traces/<model-name>/<dataset-stem>_trace.jsonl`
- `.bfcl_runs/summaries/<model-name>/<dataset-stem>_summary.json`

结果文件使用 BFCL 官方工具常见的 JSONL 内容格式，但保留 `.json` 后缀。

## 本地校验

```powershell
python -m project1.evaluation.bfcl validate --results .bfcl_runs\result\helloagent_prompt\BFCL_v4_simple_python_result.json
```

校验只检查 `id` / `result` 字段和 Python AST 表达式是否合法，不替代官方评分。

## 官方评分

官方评估器是可选依赖，不加入项目主 `requirements.txt`。

```powershell
pip install bfcl-eval
python -m project1.evaluation.bfcl official-command --model-name helloagent_prompt --category simple_python --output-root .bfcl_runs
```

把打印出的命令复制到已安装 `bfcl-eval` 的环境中运行。官方 BFCL 文档见：

- https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard
- https://pypi.org/project/bfcl-eval/
