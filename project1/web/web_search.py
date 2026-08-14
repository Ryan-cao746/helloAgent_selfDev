from typing import Any, Dict, List, Literal, Optional

import requests
from pydantic import BaseModel, ConfigDict, Field
from requests import Response


class SearchFilter(BaseModel):
    """web 搜索过滤条件。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    need_content: bool = Field(False, alias="NeedContent")
    need_url: bool = Field(False, alias="NeedUrl")
    sites: Optional[str] = Field(None, alias="Sites")
    block_hosts: Optional[str] = Field(None, alias="BlockHosts")
    auth_info_level: Literal[0, 1] = Field(0, alias="AuthInfoLevel")


class QueryControl(BaseModel):
    """搜索 query 控制项。"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    query_rewrite: bool = Field(False, alias="QueryRewrite")


class SearchRequestParams(BaseModel):
    """请求参数"""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    query: str = Field(..., alias="Query", min_length=1)
    search_type: Literal["web"] = Field("web", alias="SearchType")
    count: int = Field(10, alias="Count", ge=1, le=50)
    filter: Optional[SearchFilter] = Field(None, alias="Filter")
    time_range: Optional[str] = Field(
        None,
        alias="TimeRange",
        pattern=(
            r"^(OneDay|OneWeek|OneMonth|OneYear|"
            r"\d{4}-\d{2}-\d{2}\.\.\d{4}-\d{2}-\d{2})$"
        ),
    )
    query_control: Optional[QueryControl] = Field(None, alias="QueryControl")
    content_formats: Literal["text", "markdown"] = Field(
        "text",
        alias="ContentFormats",
    )
    industry: Optional[Literal["finance", "game", "gov"]] = Field(
        None,
        alias="Industry",
    )

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, exclude_none=True)

class ResponseMetadata(BaseModel):
    """响应元数据"""
    request_id: str = Field(..., alias = "RequestId")
    action:str = Field(..., alias = "Action")
    version:str = Field(..., alias = "Version")
    service:str = Field(..., alias = "Service")
    region:str = Field(..., alias = "Region")
    error:Optional[Dict[str, Any]] = Field(None, alias = "Error")

class WebItem(BaseModel):
    """数据项"""
    id: str = Field(..., alias = "Id")
    sort_id:int = Field(..., alias = "SortId")
    title: str = Field(..., alias = "Title")
    site_name:Optional[str] = Field(None, alias = "SiteName")
    url:Optional[str] = Field(None, alias = "Url")
    snippet:str = Field(..., alias = "Snippet") # 简短片段（约200字）
    summary:Optional[str] = Field(None, alias="Summary") # 相关摘要
    content:Optional[str] = Field(None, alias="Content")
    publish_time:Optional[str] = Field(None, alias="PublishTime")
    logo_url:Optional[str] = Field(None, alias="LogoUrl")
    rank_score:Optional[float] = Field(None, alias="RankScore")
    auth_info_des:str = Field(..., alias="AuthInfoDes")   # 权威度描述
    auth_info_level:int = Field(..., alias="AuthInfoLevel")
    content_formats:Optional[str] = Field(None, alias="ContentFormats")
    ruyi_info:Optional[Dict[str, Any]] = Field(None, alias="RuyiInfo") # WebItem形式的 火山如意 结果类型

class SearchContext(BaseModel):
    """搜索上下文信息"""
    search_type: str = Field(..., alias = "SearchType")
    origin_query: str = Field(..., alias = "OriginQuery")

class ResponseResult(BaseModel):
    """响应结果"""
    result_count: int = Field(..., alias = "ResultCount")
    web_results: Optional[List[WebItem]] = Field(None, alias = "WebResults")
    # 这里没写image相关参数
    search_context: SearchContext = Field(..., alias = "SearchContext")
    time_cost:int = Field(..., alias = "TimeCost")
    log_id: str = Field(..., alias = "LogId")
    card_results: Optional[List[Any]] = Field(None, alias = "CardResults")


class SearchResponseParams(BaseModel):
    """响应参数"""
    response_metadata: ResponseMetadata = Field(..., alias = "ResponseMetadata")
    result:Optional[ResponseResult] = Field(None, alias = "Result")

class FinalSearchResult(BaseModel):
    params: Optional[SearchResponseParams] = None
    state:Literal["Success", "Error"]
    error: Optional[str] = None

def send_search_request(
        search_params: SearchRequestParams,
        base_url: str,
        api_key: str,
        timeout: float = 30,
) -> FinalSearchResult:
    """发送请求"""
    payload = search_params.model_dump(by_alias=True, exclude_none=True)
    custom_headers = {
        "Authorization": f"Bearer {api_key}"
    }

    try:
        response = requests.post(
            base_url,
            json=payload,
            headers=custom_headers,
            timeout=timeout,
        )
        response.raise_for_status()

        data = extract_json_from_response(response) # 转换为Python字典
        params = SearchResponseParams.model_validate(data)
        api_error = params.response_metadata.error
        if api_error:
            message = api_error.get("Message") or api_error.get("Code") or str(api_error)
            return FinalSearchResult(state="Error", params=params, error=message)
        if params.result is None:
            return FinalSearchResult(
                state="Error",
                params=params,
                error="豆包搜索响应中缺少 Result",
            )
        return FinalSearchResult(state = "Success", params = params)
    except Exception as e:
        return FinalSearchResult(state="Error", error=str(e))

def extract_json_from_response(response:Response) -> Dict[str, Any]:
    try:
        json_response = response.json()
        return json_response
    except Exception as e:
        print(f"json解析出错: {e}")
        return {}
