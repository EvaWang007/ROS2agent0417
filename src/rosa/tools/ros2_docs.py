import html
import json
import os
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Tuple

from langchain.agents import tool


DEFAULT_TIMEOUT_SEC = float(os.getenv("ROSA_ROS2_DOCS_TIMEOUT_SEC", "8"))
DEFAULT_MAX_CHARS = int(os.getenv("ROSA_ROS2_DOCS_MAX_CHARS", "12000"))
DEFAULT_MAX_RESULTS = int(os.getenv("ROSA_ROS2_DOCS_MAX_RESULTS", "5"))
DEFAULT_DISTRO = os.getenv("ROSA_ROS2_DOCS_DISTRO", "humble")
DOCS_ENABLED = os.getenv("ROSA_ROS2_DOCS_ENABLED", "true").lower() == "true"

ALLOWED_DOMAINS = {
    "docs.ros.org",
    "design.ros2.org",
}

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _is_allowed_url(url: str) -> Tuple[bool, str]:
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        return False, "Invalid URL."

    if parsed.scheme not in ("http", "https"):
        return False, "Only http/https URLs are allowed."

    hostname = (parsed.hostname or "").lower()
    if hostname in ALLOWED_DOMAINS:
        return True, ""

    if any(hostname.endswith("." + domain) for domain in ALLOWED_DOMAINS):
        return True, ""

    return False, f"Domain '{hostname}' is not in the allowed ROS docs whitelist."


def _http_get(url: str, timeout_sec: float = DEFAULT_TIMEOUT_SEC) -> str:
    request = urllib.request.Request(
        url=url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        content_type = response.headers.get("Content-Type", "")
        payload = response.read()
        charset = "utf-8"
        if "charset=" in content_type:
            charset = content_type.split("charset=")[-1].split(";")[0].strip()
        return payload.decode(charset, errors="replace")


def _strip_html(html_text: str) -> str:
    # Remove script/style and comments first.
    without_script = re.sub(
        r"<script[\s\S]*?</script>|<style[\s\S]*?</style>|<!--[\s\S]*?-->",
        " ",
        html_text,
        flags=re.IGNORECASE,
    )
    # Keep text content only.
    no_tags = re.sub(r"<[^>]+>", " ", without_script)
    text = html.unescape(no_tags)
    return re.sub(r"\s+", " ", text).strip()


def _parse_duckduckgo_results(html_text: str, max_results: int) -> List[Dict[str, str]]:
    # ddg html endpoint uses links with class result__a and redirect format /l/?uddg=<urlencoded>
    anchor_pattern = re.compile(
        r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
        flags=re.IGNORECASE | re.DOTALL,
    )
    snippet_pattern = re.compile(
        r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>|'
        r'<div[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</div>',
        flags=re.IGNORECASE | re.DOTALL,
    )

    anchors = anchor_pattern.findall(html_text)
    snippets = snippet_pattern.findall(html_text)
    parsed_snippets: List[str] = []
    for s1, s2 in snippets:
        parsed_snippets.append(_strip_html(s1 or s2))

    results: List[Dict[str, str]] = []
    for idx, (raw_href, raw_title) in enumerate(anchors):
        href = html.unescape(raw_href)
        title = _strip_html(raw_title)

        # decode ddg redirect urls
        if "duckduckgo.com/l/?" in href or href.startswith("/l/?"):
            query = urllib.parse.urlparse(href).query
            params = urllib.parse.parse_qs(query)
            target = params.get("uddg", [None])[0]
            if target:
                href = urllib.parse.unquote(target)

        ok, _ = _is_allowed_url(href)
        if not ok:
            continue

        snippet = parsed_snippets[idx] if idx < len(parsed_snippets) else ""
        results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= max_results:
            break

    # de-duplicate by URL while preserving order
    seen = set()
    deduped: List[Dict[str, str]] = []
    for item in results:
        if item["url"] in seen:
            continue
        seen.add(item["url"])
        deduped.append(item)

    return deduped


def _extract_command_tokens(command: str) -> List[str]:
    cleaned = re.sub(r"\s+", " ", command.strip())
    if cleaned == "":
        return []
    return cleaned.split(" ")


def _extract_usage_lines(text: str, tokens: List[str], max_lines: int = 5) -> List[str]:
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    if not tokens:
        return []

    usage_lines = []
    token_key = " ".join(tokens[: min(3, len(tokens))]).lower()
    for line in lines:
        normalized = line.lower()
        if normalized.startswith("usage") or token_key in normalized:
            usage_lines.append(line)
        if len(usage_lines) >= max_lines:
            break
    return usage_lines


def _extract_options_block(text: str, max_items: int = 12) -> List[str]:
    # Look for common CLI option forms like "-h", "--help", "--spin-time"
    pattern = re.compile(r"(?m)^\s*(?:-\w(?:,\s*)?)?(?:--[a-zA-Z0-9][\w-]*)(?:[^\n]*)$")
    matches = [m.group(0).strip() for m in pattern.finditer(text)]
    deduped: List[str] = []
    seen = set()
    for item in matches:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
        if len(deduped) >= max_items:
            break
    return deduped


def _extract_examples(text: str, command: str, max_items: int = 6) -> List[str]:
    lines = [ln.strip() for ln in text.split("\n")]
    lines = [ln for ln in lines if ln]
    cmd_head = command.strip().split(" ")[0] if command.strip() else "ros2"

    examples: List[str] = []
    for line in lines:
        if line.startswith("ros2 ") or line.startswith(cmd_head + " "):
            examples.append(line)
        if len(examples) >= max_items:
            break

    deduped: List[str] = []
    seen = set()
    for ex in examples:
        if ex in seen:
            continue
        seen.add(ex)
        deduped.append(ex)
    return deduped


@tool
def ros2_docs_search(
    query: str,
    distro: str = DEFAULT_DISTRO,
    max_results: int = DEFAULT_MAX_RESULTS,
) -> dict:
    """
    Search ROS2 official documentation pages relevant to a query.

    :param query: Search query, e.g. "ros2 topic echo --once meaning".
    :param distro: ROS2 distro hint (e.g. humble, jazzy) to improve relevance.
    :param max_results: Maximum number of results to return.
    """
    if not DOCS_ENABLED:
        return {"error": "ROS2 docs tools are disabled by ROSA_ROS2_DOCS_ENABLED=false"}

    if not query or query.strip() == "":
        return {"error": "Query must be a non-empty string."}

    max_results = max(1, min(max_results, 10))
    full_query = (
        f"site:docs.ros.org OR site:design.ros2.org ROS2 {distro} {query.strip()}"
    )
    ddg_url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": full_query})

    try:
        page = _http_get(ddg_url)
        results = _parse_duckduckgo_results(page, max_results=max_results)
        return {
            "query": query,
            "distro": distro,
            "allowed_domains": sorted(ALLOWED_DOMAINS),
            "results_count": len(results),
            "results": results,
        }
    except Exception as e:
        return {"error": f"Failed to search ROS2 docs: {e}"}


@tool
def ros2_docs_fetch(url: str, max_chars: int = DEFAULT_MAX_CHARS) -> dict:
    """
    Fetch and normalize a ROS2 official documentation page.

    :param url: Full URL to docs.ros.org or design.ros2.org page.
    :param max_chars: Maximum number of characters to return.
    """
    if not DOCS_ENABLED:
        return {"error": "ROS2 docs tools are disabled by ROSA_ROS2_DOCS_ENABLED=false"}

    is_allowed, reason = _is_allowed_url(url)
    if not is_allowed:
        return {"error": reason}

    max_chars = max(1000, min(max_chars, 50000))

    try:
        raw_html = _http_get(url)
        text = _strip_html(raw_html)
        truncated = len(text) > max_chars
        if truncated:
            text = text[:max_chars]
        return {
            "url": url,
            "max_chars": max_chars,
            "truncated": truncated,
            "content": text,
        }
    except Exception as e:
        return {"error": f"Failed to fetch ROS2 docs page: {e}"}


@tool
def ros2_docs_extract_cli(command: str, page_text: str) -> dict:
    """
    Extract CLI usage, key options and examples from ROS2 docs page text.

    :param command: CLI command to extract for (e.g. "ros2 topic echo").
    :param page_text: Text content from ros2_docs_fetch().content.
    """
    if not command or command.strip() == "":
        return {"error": "Command must be a non-empty string."}
    if not page_text or page_text.strip() == "":
        return {"error": "page_text must be non-empty."}

    # Try to restore line structure if text arrives as a JSON-encoded object from some clients.
    if page_text.strip().startswith("{") and page_text.strip().endswith("}"):
        try:
            maybe_json = json.loads(page_text)
            if isinstance(maybe_json, dict) and "content" in maybe_json:
                page_text = str(maybe_json["content"])
        except Exception:
            pass

    # We intentionally keep this extractor heuristic/simple for robustness.
    tokens = _extract_command_tokens(command)
    usage = _extract_usage_lines(page_text, tokens=tokens)
    key_args = _extract_options_block(page_text)
    examples = _extract_examples(page_text, command=command)

    confidence = "low"
    score = 0
    if usage:
        score += 1
    if key_args:
        score += 1
    if examples:
        score += 1
    if score >= 3:
        confidence = "high"
    elif score == 2:
        confidence = "medium"

    return {
        "command": command,
        "usage": usage,
        "key_args": key_args,
        "examples": examples,
        "confidence": confidence,
    }
