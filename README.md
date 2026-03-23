# py-har-mcp

一个用于解析和分析 HAR（HTTP Archive）文件的 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/introduction) Python 服务器。这个服务器允许 AI 助手检查 HAR 格式捕获的网络流量，并内置对敏感认证请求头的自动脱敏支持。

## Features

- **加载 HAR 文件**：支持本地文件系统路径和 HTTP/HTTPS URL
- **列出全部 URL 与 HTTP 方法**：查看 HAR 中访问过的请求组合
- **查询请求 ID**：根据 URL 与 Method 获取对应请求 ID
- **获取完整请求详情**：自动脱敏认证请求头，并尽量以纯文本输出响应内容
- **按域名统计请求**：汇总域名级别的请求数、方法分布、状态码分布
- **按状态码统计请求**：统计各 HTTP 状态码出现次数及关联请求 ID
- **全文搜索 HAR 内容**：支持搜索请求头、响应头、请求体、响应体
- **兼容真实世界 HAR 文件**：
  - `time` 和 `timings` 字段支持整数/浮点数并自动转为整数
  - `response.content.text` 支持普通文本或 base64 文本，并优先输出纯文本
  - 允许 HAR 中存在标准规范之外的附加字段
- 支持浏览器开发者工具导出的标准 HAR 格式

## Installation

你可以通过标准 MCP 配置方式安装和运行这个 MCP 服务器。

将如下 JSON 配置加入你的 MCP 配置文件。

## Using uvx

如果你使用 [`uv`](https://docs.astral.sh/uv/)，可以直接通过 `uvx` 运行：

```json
{
  "mcpServers": {
    "py-har-mcp": {
      "command": "uvx",
      "args": [
        "py-har-mcp"
      ]
    }
  }
}
```

## Using python -m

也可以直接通过 `python -m` 启动服务器。

```json
{
  "mcpServers": {
    "py-har-mcp": {
      "command": "python",
      "args": [
        "-m",
        "py_har_mcp"
      ],
      "cwd": "D:\\Project\\py\\har-mcp\\py-har-mcp"
    }
  }
}
```

### Build / Install from source

如果你不想依赖 `uvx`，可以先在项目根目录安装源码：

```bash
pip install -e .
```

安装后可直接把命令配置为 `py-har-mcp`：

```json
{
  "mcpServers": {
    "py-har-mcp": {
      "command": "py-har-mcp"
    }
  }
}
```

## Usage

`py-har-mcp` 以基于 stdio 的 MCP 服务器方式运行，通过标准输入/输出进行通信。

### Running the Server

在 [`py-har-mcp`](py-har-mcp) 目录下执行：

```bash
python -m py_har_mcp
```

或：

```bash
py-har-mcp
```

### HTTP Mode

如果你希望以 HTTP 方式运行：

```bash
python -m py_har_mcp --http --port 8000
```

### Available Tools

#### 1. `load_har`
加载 HAR 文件，并将其保存为默认分析数据集。

**Parameters:**
- `source` (string, required): HAR 文件路径或 HTTP/HTTPS URL

**Example:**
```json
{
  "source": "D:\\captures\\demo.har"
}
```

#### 2. `list_urls_methods`
列出 HAR 中所有访问过的 URL 与 HTTP 方法组合。

**Parameters:**
- `source` (string, optional): 指定 HAR 文件路径或 URL；为空时使用已通过 `load_har` 加载的默认 HAR

**Returns:** 带有 URL、Method 和关联请求 ID 的数组。

#### 3. `get_request_ids`
根据指定 URL 和 HTTP 方法获取请求 ID 列表。

**Parameters:**
- `url` (string, required): 要匹配的完整请求 URL
- `method` (string, required): 要匹配的 HTTP 方法，如 `GET`、`POST`
- `source` (string, optional): 指定 HAR 文件路径或 URL；为空时使用默认 HAR

**Example:**
```json
{
  "url": "https://api.example.com/users",
  "method": "GET",
  "source": "D:\\captures\\demo.har"
}
```

#### 4. `get_request_details`
根据请求 ID 获取完整请求详情。认证相关请求头会被自动脱敏。

**Parameters:**
- `request_id` (string, required): 要查询的请求 ID，例如 `request_0`
- `source` (string, optional): 指定 HAR 文件路径或 URL；为空时使用默认 HAR

**Example:**
```json
{
  "request_id": "request_0",
  "source": "D:\\captures\\demo.har"
}
```

**Redacted Headers:**
- Authorization
- X-API-Key
- X-Auth-Token
- Cookie
- Set-Cookie
- Proxy-Authorization

#### 5. `get_domain_stats`
按域名汇总请求统计信息，包括方法分布和状态码分布。

**Parameters:**
- `source` (string, optional): 指定 HAR 文件路径或 URL；为空时使用默认 HAR

**Returns:** 包含 `domain`、`total_requests`、`methods`、`status_codes` 的数组。

#### 6. `get_status_code_stats`
按 HTTP 状态码汇总请求统计信息。

**Parameters:**
- `source` (string, optional): 指定 HAR 文件路径或 URL；为空时使用默认 HAR

**Returns:** 包含 `status_code`、`count`、`request_ids` 的数组。

#### 7. `search_har`
在 HAR 中搜索请求头、响应头、请求体和响应体内容。

**Parameters:**
- `query` (string, required): 搜索关键字或片段
- `search_headers` (boolean, optional): 是否搜索请求头和响应头，默认 `true`
- `search_request_body` (boolean, optional): 是否搜索请求体，默认 `true`
- `search_response_body` (boolean, optional): 是否搜索响应体，默认 `true`
- `case_sensitive` (boolean, optional): 是否区分大小写，默认 `false`
- `source` (string, optional): 指定 HAR 文件路径或 URL；为空时使用默认 HAR

**Returns:** 包含 `request_id`、`location`、`field`、`snippet`、`url`、`method`、`status_code` 的匹配结果数组。

## Integration with Claude Desktop

将如下配置加入 Claude Desktop：

```json
{
  "mcpServers": {
    "py-har-mcp": {
      "command": "python",
      "args": [
        "-m",
        "py_har_mcp"
      ],
      "cwd": "D:\\Project\\py\\har-mcp\\py-har-mcp"
    }
  }
}
```

## Development

### Running Checks

在 [`py-har-mcp`](py-har-mcp) 目录下执行：

```bash
python -m compileall py_har_mcp
```

### Project Structure

```text
.
├── pyproject.toml
├── README.md
└── py_har_mcp/
    ├── __init__.py
    ├── __main__.py
    ├── models.py
    ├── parser.py
    └── server.py
```

## Dependencies

- [fastmcp](https://github.com/jlowin/fastmcp) - Python MCP server implementation
- Python standard library - HAR parsing, HTTP fetching, JSON processing

## License

MIT
