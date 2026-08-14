import json
import os
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

from project1.web.web_search import SearchRequestParams, send_search_request
from project1.tools.base import Tool, ToolParameter


DEFAULT_SEARCH_BASE_URL = "https://open.feedcoopapi.com/search_api/web_search"


class DouBaoSearchTool(Tool):
    """使用豆包搜索引擎获取实时网络信息的工具。"""

    def __init__(
            self,
            api_key: Optional[str] = None,
            base_url: Optional[str] = None,
            timeout: float = 30,
    ):
        self.api_key = api_key or os.getenv("DOUBAO_SEARCH_API_KEY")
        self.base_url = (
            base_url
            or os.getenv("DOUBAO_SEARCH_BASE_URL")
            or DEFAULT_SEARCH_BASE_URL
        )
        self.timeout = timeout
        super().__init__(
            name="doubao_search_tool",
            description=(
                "调用豆包搜索 Custom 版 API 获取实时网页搜索结果。"
                "当问题涉及时效性信息，或对事实的置信度较低、需要外部来源佐证时使用。"
                "当前工具仅声明 web 搜索参数，不用于图片搜索。"
            ),
        )

    def run(self, parameters: Dict[str, Any]) -> str:
        if not self.api_key:
            raise ValueError(
                "豆包搜索 API Key 未配置，请传入 api_key 或设置 "
                "DOUBAO_SEARCH_API_KEY 环境变量"
            )

        try:
            search_params = SearchRequestParams.model_validate(parameters)
        except ValidationError as error:
            raise ValueError(f"豆包搜索参数校验失败：{error}") from error

        search_result = send_search_request(
            search_params=search_params,
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        if (
                search_result.state != "Success"
                or search_result.params is None
                or search_result.params.result is None
        ):
            detail = search_result.error or "未知错误"
            raise RuntimeError(f"豆包搜索请求失败：{detail}")

        result_data = search_result.params.result.model_dump(
            exclude_none=True,
        )
        return json.dumps(result_data, ensure_ascii=False)

    def get_parameters(self) -> List[ToolParameter]:
        return [
            ToolParameter(
                name="query",
                type="str",
                description=(
                    "用户的搜索 query，长度为 1~100 个字符；过长内容会被接口截断，"
                    "不支持同时提交多个搜索词。"
                ),
                required=True,
            ),
            ToolParameter(
                name="search_type",
                type="str",
                description='搜索类型。目前该工具仅支持 "web"。',
                required=False,
                default="web",
            ),
            ToolParameter(
                name="count",
                type="int",
                description="返回的搜索结果条数，最多 50 条。",
                required=False,
                default=10,
            ),
            ToolParameter(
                name="filter",
                type="Dict[str, Any]",
                description=(
                    "网页结果过滤条件。可包含：need_content（bool，是否仅返回有正文的结果，"
                    "默认 false）；need_url（bool，是否仅返回有原文链接的结果，默认 false，"
                    "设为 true 会过滤如意结果）；sites（str，用 '|' 分隔完整域名，最多 20 个，"
                    "例如 'aliyun.com|mp.qq.com'）；block_hosts（str，用 '|' 分隔需要屏蔽的"
                    "完整域名，最多 5 个）；auth_info_level（int，0 表示不限制权威等级，"
                    "1 表示仅返回非常权威的结果，并会过滤如意结果）。"
                ),
                required=False,
                default=None,
            ),
            ToolParameter(
                name="time_range",
                type="str",
                description=(
                    "限定内容发布时间。不填表示不限制；可选 OneDay、OneWeek、OneMonth、"
                    "OneYear，或使用 'YYYY-MM-DD..YYYY-MM-DD' 指定包含起止日期的区间，"
                    "例如 '2024-12-30..2025-12-30'。"
                ),
                required=False,
                default=None,
            ),
            ToolParameter(
                name="query_control",
                type="Dict[str, bool]",
                description=(
                    "搜索 query 控制项。可包含 query_rewrite（bool），表示是否开启 query 改写；"
                    "默认 false，开启后会增加搜索耗时。"
                ),
                required=False,
                default=None,
            ),
            ToolParameter(
                name="content_formats",
                type="str",
                description=(
                    '指定返回正文的格式，可选 "text" 或 "markdown"，默认为 "text"。'
                ),
                required=False,
                default="text",
            ),
            ToolParameter(
                name="industry",
                type="str",
                description=(
                    "行业搜索类型。可选 finance（金融）、game（电子游戏）或 gov（政府网站、"
                    "央媒/地区官媒、国家机构和国家级官方协会等高权威来源）。启用后结果会减少，"
                    "并过滤如意结果。"
                ),
                required=False,
                default=None,
            ),
        ]
