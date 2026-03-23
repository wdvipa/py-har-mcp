from __future__ import annotations

import base64
import binascii
import copy
import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import urlopen

from .models import (
    DomainStatsEntry,
    HARData,
    REDACTED_HEADER_NAMES,
    RequestDetails,
    SearchMatch,
    StatusCodeStatsEntry,
    URLMethodEntry,
)


class HARParser:
    def parse_source(self, source: str) -> HARData:
        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            with urlopen(source) as response:  # nosec: B310
                payload = response.read().decode("utf-8")
            return self.parse_text(payload)

        payload = Path(source).read_text(encoding="utf-8")
        return self.parse_text(payload)

    def parse_text(self, payload: str) -> HARData:
        raw = json.loads(payload)
        log = raw.get("log")
        if not isinstance(log, dict):
            raise ValueError("HAR 文件缺少 log 对象")

        entries = log.get("entries")
        if not isinstance(entries, list):
            raise ValueError("HAR 文件缺少 entries 数组")

        normalized_entries: list[dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, dict):
                normalized_entries.append(self._normalize_entry(entry))

        return HARData(entries=normalized_entries)

    def get_urls_and_methods(self, har_data: HARData) -> list[URLMethodEntry]:
        grouped: dict[tuple[str, str], URLMethodEntry] = {}
        for index, entry in enumerate(har_data.entries):
            request = entry.get("request")
            if not isinstance(request, dict):
                continue

            url = str(request.get("url", ""))
            method = str(request.get("method", ""))
            key = (url, method)
            request_id = f"request_{index}"

            if key not in grouped:
                grouped[key] = URLMethodEntry(url=url, method=method, request_ids=[request_id])
            else:
                grouped[key].request_ids.append(request_id)

        return list(grouped.values())

    def get_request_ids_for_url_method(self, har_data: HARData, target_url: str, method: str) -> list[str]:
        request_ids: list[str] = []
        for index, entry in enumerate(har_data.entries):
            request = entry.get("request")
            if not isinstance(request, dict):
                continue
            if request.get("url") == target_url and request.get("method") == method:
                request_ids.append(f"request_{index}")
        return request_ids

    def get_request_details(self, har_data: HARData, request_id: str) -> RequestDetails:
        index = self._parse_request_id(request_id, len(har_data.entries))
        entry = har_data.entries[index]
        request = entry.get("request")
        request_info = self._redacted_request_info(request) if isinstance(request, dict) else None
        response = copy.deepcopy(entry.get("response")) if isinstance(entry.get("response"), dict) else None
        cache = copy.deepcopy(entry.get("cache")) if isinstance(entry.get("cache"), dict) else None
        timings = copy.deepcopy(entry.get("timings")) if isinstance(entry.get("timings"), dict) else None

        return RequestDetails(
            request_id=request_id,
            started_datetime=str(entry.get("startedDateTime", "")),
            time=int(entry.get("time", 0)),
            request=request_info,
            response=response,
            cache=cache,
            timings=timings,
            server_ip_address=self._string_or_none(entry.get("serverIPAddress")),
            connection=self._string_or_none(entry.get("connection")),
            comment=self._string_or_none(entry.get("comment")),
        )

    def get_domain_stats(self, har_data: HARData) -> list[DomainStatsEntry]:
        stats: dict[str, DomainStatsEntry] = {}
        for entry in har_data.entries:
            request = entry.get("request")
            if not isinstance(request, dict):
                continue

            url = str(request.get("url", ""))
            method = str(request.get("method", "")).upper()
            domain = self._extract_domain(url)
            if domain not in stats:
                stats[domain] = DomainStatsEntry(
                    domain=domain,
                    total_requests=0,
                    methods={},
                    status_codes={},
                )

            response = entry.get("response")
            status_code = self._status_code_from_entry(response)
            bucket = stats[domain]
            bucket.total_requests += 1
            if method:
                bucket.methods[method] = bucket.methods.get(method, 0) + 1
            if status_code is not None:
                key = str(status_code)
                bucket.status_codes[key] = bucket.status_codes.get(key, 0) + 1

        return sorted(stats.values(), key=lambda item: (-item.total_requests, item.domain))

    def get_status_code_stats(self, har_data: HARData) -> list[StatusCodeStatsEntry]:
        stats: dict[int, StatusCodeStatsEntry] = {}
        for index, entry in enumerate(har_data.entries):
            status_code = self._status_code_from_entry(entry.get("response"))
            if status_code is None:
                continue
            if status_code not in stats:
                stats[status_code] = StatusCodeStatsEntry(
                    status_code=status_code,
                    count=0,
                    request_ids=[],
                )
            stats[status_code].count += 1
            stats[status_code].request_ids.append(f"request_{index}")

        return sorted(stats.values(), key=lambda item: (item.status_code, item.count))

    def search_requests(
        self,
        har_data: HARData,
        query: str,
        search_headers: bool = True,
        search_request_body: bool = True,
        search_response_body: bool = True,
        case_sensitive: bool = False,
    ) -> list[SearchMatch]:
        if not query:
            raise ValueError("query must be a non-empty string")

        matches: list[SearchMatch] = []
        normalized_query = query if case_sensitive else query.lower()

        for index, entry in enumerate(har_data.entries):
            request_id = f"request_{index}"
            request = entry.get("request")
            response = entry.get("response")
            url = ""
            method = ""
            if isinstance(request, dict):
                url = str(request.get("url", ""))
                method = str(request.get("method", ""))

            status_code = self._status_code_from_entry(response)

            if search_headers and isinstance(request, dict):
                for header in request.get("headers", []):
                    if not isinstance(header, dict):
                        continue
                    header_name = str(header.get("name", ""))
                    header_value = str(header.get("value", ""))
                    matched_snippet = self._find_match_snippet(header_value, normalized_query, case_sensitive)
                    if matched_snippet is not None:
                        matches.append(
                            SearchMatch(
                                request_id=request_id,
                                location="request.headers",
                                field=header_name,
                                snippet=matched_snippet,
                                url=url,
                                method=method,
                                status_code=status_code,
                            )
                        )

                if isinstance(response, dict):
                    for header in response.get("headers", []):
                        if not isinstance(header, dict):
                            continue
                        header_name = str(header.get("name", ""))
                        header_value = str(header.get("value", ""))
                        matched_snippet = self._find_match_snippet(header_value, normalized_query, case_sensitive)
                        if matched_snippet is not None:
                            matches.append(
                                SearchMatch(
                                    request_id=request_id,
                                    location="response.headers",
                                    field=header_name,
                                    snippet=matched_snippet,
                                    url=url,
                                    method=method,
                                    status_code=status_code,
                                )
                            )

            if search_request_body and isinstance(request, dict):
                post_data = request.get("postData")
                if isinstance(post_data, dict):
                    body_text = post_data.get("text")
                    if body_text is not None:
                        matched_snippet = self._find_match_snippet(str(body_text), normalized_query, case_sensitive)
                        if matched_snippet is not None:
                            matches.append(
                                SearchMatch(
                                    request_id=request_id,
                                    location="request.body",
                                    field="postData.text",
                                    snippet=matched_snippet,
                                    url=url,
                                    method=method,
                                    status_code=status_code,
                                )
                            )

            if search_response_body and isinstance(response, dict):
                content = response.get("content")
                if isinstance(content, dict):
                    response_text = self._extract_response_text(content)
                    if response_text is not None:
                        matched_snippet = self._find_match_snippet(response_text, normalized_query, case_sensitive)
                        if matched_snippet is not None:
                            matches.append(
                                SearchMatch(
                                    request_id=request_id,
                                    location="response.body",
                                    field="response.content.text",
                                    snippet=matched_snippet,
                                    url=url,
                                    method=method,
                                    status_code=status_code,
                                )
                            )

        return matches

    def _normalize_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        normalized = copy.deepcopy(entry)
        normalized["time"] = self._coerce_int(normalized.get("time"), default=0)

        timings = normalized.get("timings")
        if isinstance(timings, dict):
            normalized_timings: dict[str, int] = {}
            for key, value in timings.items():
                normalized_timings[str(key)] = self._coerce_int(value, default=-1)
            normalized["timings"] = normalized_timings

        response = normalized.get("response")
        if isinstance(response, dict):
            response["status"] = self._coerce_int(response.get("status"), default=0)
            content = response.get("content")
            if isinstance(content, dict):
                size_value = content.get("size")
                if size_value is not None:
                    content["size"] = self._coerce_int(size_value, default=0)

                compression_value = content.get("compression")
                if compression_value is not None:
                    content["compression"] = self._coerce_int(compression_value, default=0)

        return normalized

    def _redacted_request_info(self, request: dict[str, Any]) -> dict[str, Any]:
        cloned = copy.deepcopy(request)
        headers = cloned.get("headers")
        if isinstance(headers, list):
            for header in headers:
                if not isinstance(header, dict):
                    continue
                name = str(header.get("name", ""))
                if name.lower() in REDACTED_HEADER_NAMES:
                    header["value"] = "[REDACTED]"
        return cloned

    def _extract_domain(self, url: str) -> str:
        parsed = urlparse(url)
        return parsed.netloc or "(unknown)"

    def _status_code_from_entry(self, response: Any) -> int | None:
        if not isinstance(response, dict):
            return None
        status = response.get("status")
        if isinstance(status, int):
            return status
        if isinstance(status, float):
            return int(status)
        if isinstance(status, str):
            try:
                return int(float(status))
            except ValueError:
                return None
        return None

    def _parse_request_id(self, request_id: str, total_entries: int) -> int:
        if not request_id.startswith("request_"):
            raise ValueError("Invalid request_id. Expected format like 'request_0'.")
        raw_index = request_id.split("_", maxsplit=1)[1]
        if not raw_index.isdigit():
            raise ValueError("Invalid request_id index.")
        index = int(raw_index)
        if index < 0 or index >= total_entries:
            raise ValueError("request_id out of range.")
        return index

    def _extract_response_text(self, content: dict[str, Any]) -> str | None:
        text = content.get("text")
        if text is None:
            return None

        text_str = str(text)
        encoding = str(content.get("encoding", "")).lower()
        if encoding == "base64":
            try:
                decoded = base64.b64decode(text_str, validate=True)
            except (binascii.Error, ValueError):
                return text_str

            for codec in ("utf-8", "utf-16", "latin-1"):
                try:
                    return decoded.decode(codec)
                except UnicodeDecodeError:
                    continue
            return text_str

        return text_str

    def _find_match_snippet(self, value: str, normalized_query: str, case_sensitive: bool) -> str | None:
        haystack = value if case_sensitive else value.lower()
        index = haystack.find(normalized_query)
        if index == -1:
            return None

        start = max(0, index - 40)
        end = min(len(value), index + len(normalized_query) + 40)
        snippet = value[start:end].strip()
        if start > 0:
            snippet = f"...{snippet}"
        if end < len(value):
            snippet = f"{snippet}..."
        return snippet

    def _coerce_int(self, value: Any, default: int) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(float(value))
            except ValueError:
                return default
        return default

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)
