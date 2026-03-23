from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP

from .models import HARData
from .parser import HARParser

mcp = FastMCP("py-har-mcp")
parser = HARParser()
har_data: HARData | None = None


@mcp.tool()
def load_har(
    source: Annotated[
        str,
        "HAR 文件来源。支持本地文件绝对/相对路径，或 http/https URL。调用后会把该 HAR 保存为默认分析数据集。",
    ],
) -> str:
    """从文件路径或 HTTP URL 加载 HAR 文件，并保存为默认分析数据集。"""
    global har_data
    har_data = parser.parse_source(source)
    return f"Successfully loaded HAR file with {len(har_data.entries)} entries"


@mcp.tool()
def list_urls_methods(
    source: Annotated[
        str | None,
        "可选 HAR 文件来源。为空时使用 `load_har` 已加载的默认 HAR；传入时直接分析指定 HAR 文件。",
    ] = None,
) -> list[dict[str, Any]]:
    """列出 HAR 中访问过的所有 URL 与 HTTP 方法组合。"""
    data = _resolve_har_data(source)
    return [entry.to_dict() for entry in parser.get_urls_and_methods(data)]


@mcp.tool()
def get_request_ids(
    url: Annotated[str, "要过滤的完整请求 URL。通常应与 HAR 中记录的 URL 完全一致。"],
    method: Annotated[str, "要过滤的 HTTP 方法，例如 GET、POST、PUT、DELETE。"],
    source: Annotated[
        str | None,
        "可选 HAR 文件来源。为空时使用默认 HAR；传入时直接分析指定 HAR 文件。",
    ] = None,
) -> list[str]:
    """根据指定 URL 与 HTTP 方法，返回匹配的请求 ID 列表。"""
    data = _resolve_har_data(source)
    return parser.get_request_ids_for_url_method(data, url, method)


@mcp.tool()
def get_request_details(
    request_id: Annotated[
        str,
        "请求 ID，格式通常为 `request_0`、`request_1`。可由 `list_urls_methods` 或 `get_request_ids` 返回。",
    ],
    source: Annotated[
        str | None,
        "可选 HAR 文件来源。为空时使用默认 HAR；传入时直接分析指定 HAR 文件。",
    ] = None,
) -> dict[str, Any]:
    """根据请求 ID 获取完整请求详情，并自动脱敏认证相关请求头。"""
    data = _resolve_har_data(source)
    return parser.get_request_details(data, request_id).to_dict()


@mcp.tool()
def get_domain_stats(
    source: Annotated[
        str | None,
        "可选 HAR 文件来源。为空时使用默认 HAR；传入时直接分析指定 HAR 文件。",
    ] = None,
) -> list[dict[str, Any]]:
    """按域名汇总请求统计信息，包括请求方法和状态码分布。"""
    data = _resolve_har_data(source)
    return [entry.to_dict() for entry in parser.get_domain_stats(data)]


@mcp.tool()
def get_status_code_stats(
    source: Annotated[
        str | None,
        "可选 HAR 文件来源。为空时使用默认 HAR；传入时直接分析指定 HAR 文件。",
    ] = None,
) -> list[dict[str, Any]]:
    """按 HTTP 状态码汇总请求统计信息。"""
    data = _resolve_har_data(source)
    return [entry.to_dict() for entry in parser.get_status_code_stats(data)]


@mcp.tool()
def search_har(
    query: Annotated[str, "要搜索的关键字或片段。可用于匹配请求头、响应头、请求体或响应体中的文本。"],
    search_headers: Annotated[bool, "是否搜索请求头与响应头。默认 true。"] = True,
    search_request_body: Annotated[bool, "是否搜索请求体内容，例如 POST/PUT 的 `postData.text`。默认 true。"] = True,
    search_response_body: Annotated[bool, "是否搜索响应体内容，例如 `response.content.text`。默认 true。"] = True,
    case_sensitive: Annotated[bool, "是否区分大小写。默认 false。"] = False,
    source: Annotated[
        str | None,
        "可选 HAR 文件来源。为空时使用默认 HAR；传入时直接分析指定 HAR 文件。",
    ] = None,
) -> list[dict[str, Any]]:
    """在 HAR 中搜索请求头、响应头、请求体和响应体内容。"""
    data = _resolve_har_data(source)
    return [
        match.to_dict()
        for match in parser.search_requests(
            data,
            query=query,
            search_headers=search_headers,
            search_request_body=search_request_body,
            search_response_body=search_response_body,
            case_sensitive=case_sensitive,
        )
    ]


def _resolve_har_data(source: str | None = None) -> HARData:
    if source:
        return parser.parse_source(source)
    if har_data is None:
        raise ValueError(
            "No HAR file loaded. Please load a HAR file first using load_har, or pass the source parameter directly."
        )
    return har_data
