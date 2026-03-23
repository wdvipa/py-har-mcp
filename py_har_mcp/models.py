from __future__ import annotations

from dataclasses import dataclass
from typing import Any


REDACTED_HEADER_NAMES = {
    "authorization",
    "x-api-key",
    "x-auth-token",
    "cookie",
    "set-cookie",
    "proxy-authorization",
}


@dataclass(slots=True)
class URLMethodEntry:
    url: str
    method: str
    request_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "method": self.method,
            "request_ids": self.request_ids,
        }


@dataclass(slots=True)
class DomainStatsEntry:
    domain: str
    total_requests: int
    methods: dict[str, int]
    status_codes: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "total_requests": self.total_requests,
            "methods": self.methods,
            "status_codes": self.status_codes,
        }


@dataclass(slots=True)
class StatusCodeStatsEntry:
    status_code: int
    count: int
    request_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status_code": self.status_code,
            "count": self.count,
            "request_ids": self.request_ids,
        }


@dataclass(slots=True)
class SearchMatch:
    request_id: str
    location: str
    field: str
    snippet: str
    url: str
    method: str
    status_code: int | None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "request_id": self.request_id,
            "location": self.location,
            "field": self.field,
            "snippet": self.snippet,
            "url": self.url,
            "method": self.method,
        }
        if self.status_code is not None:
            result["status_code"] = self.status_code
        return result


@dataclass(slots=True)
class HARData:
    entries: list[dict[str, Any]]


@dataclass(slots=True)
class RequestDetails:
    request_id: str
    started_datetime: str
    time: int
    request: dict[str, Any] | None
    response: dict[str, Any] | None
    cache: dict[str, Any] | None
    timings: dict[str, Any] | None
    server_ip_address: str | None = None
    connection: str | None = None
    comment: str | None = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "request_id": self.request_id,
            "started_datetime": self.started_datetime,
            "time": self.time,
            "request": self.request,
            "response": self.response,
        }
        if self.cache is not None:
            result["cache"] = self.cache
        if self.timings is not None:
            result["timings"] = self.timings
        if self.server_ip_address:
            result["serverIPAddress"] = self.server_ip_address
        if self.connection:
            result["connection"] = self.connection
        if self.comment:
            result["comment"] = self.comment
        return result
