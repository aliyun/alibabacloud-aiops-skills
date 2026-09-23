#!/usr/bin/env python3
"""Fetch current AgentLoop instrumentation references with Python's standard library.

Python >= 3.8; no browser, credentials, pip packages, or JavaScript execution.
The JSON endpoints are public help-site implementation details, so failures are
explicit and URL fetches can fall back to the page's embedded SSR JSON.
"""

import argparse
import datetime
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


BASE = "https://help.aliyun.com"
SCOPES = {
    "genai": "/cms/cloudmonitor-2-0/integrating-llm-applications-with-opentelemetry-genai-utils",
    "best-practices": "/cms/cloudmonitor-2-0/application-monitoring-best-practices",
}
MENU_SEED = "3043079"
SEEDS = {SCOPES["genai"]: "3044328", SCOPES["best-practices"]: "3000060"}
HOSTS = {"help.aliyun.com", "github.com", "api.github.com", "raw.githubusercontent.com"}
GITHUB_REPOS = {"alibaba/loongsuite-java", "alibaba/loongsuite-python", "alibaba/loongsuite-go", "alibaba/loongsuite-js", "open-telemetry/opentelemetry-python-genai"}
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


class FetchError(Exception):
    """An unavailable, invalid, or mismatched source; never valid document text."""


class DirectoryError(FetchError):
    """A directory that must be enumerated instead of following its first child."""


def utc_now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def safe_url(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in HOSTS or parts.username or parts.password:
        raise FetchError("Only HTTPS help.aliyun.com and public GitHub reference URLs are supported: " + url)
    if parts.port not in (None, 443):
        raise FetchError("Only the standard HTTPS port is supported")
    return urlunsplit((parts.scheme, parts.netloc, parts.path, parts.query, ""))


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        safe_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Client:
    def __init__(self, timeout=20.0, retries=2, max_bytes=8 * 1024 * 1024):
        self.timeout = timeout
        self.retries = retries
        self.max_bytes = max_bytes
        self.opener = build_opener(SafeRedirect())

    def get(self, url):
        url = safe_url(url)
        last_error = None
        for attempt in range(self.retries + 1):
            try:
                request = Request(url, headers={"User-Agent": "AgentLoop-document-fetcher/1.0", "Accept-Encoding": "identity", "Accept": "application/json,text/html,text/plain"})
                with self.opener.open(request, timeout=self.timeout) as response:
                    length = response.headers.get("Content-Length")
                    if length and int(length) > self.max_bytes:
                        raise FetchError("Response exceeds --max-bytes: " + url)
                    body = response.read(self.max_bytes + 1)
                    if len(body) > self.max_bytes:
                        raise FetchError("Response exceeds --max-bytes: " + url)
                    if not body.strip():
                        raise FetchError("Empty HTTP response: " + url)
                    charset = response.headers.get_content_charset() or "utf-8"
                    return body.decode(charset), safe_url(response.geturl())
            except HTTPError as exc:
                last_error = "HTTP {}: {}".format(exc.code, url)
                if exc.code not in (408, 429, 500, 502, 503, 504):
                    break
            except (URLError, socket.timeout, TimeoutError, OSError, UnicodeError, ValueError) as exc:
                last_error = "{}: {} ({})".format(type(exc).__name__, url, exc)
            if attempt < self.retries:
                time.sleep(min(0.5 * (2 ** attempt), 2.0))
        raise FetchError(last_error or "Unable to fetch " + url)

    def json(self, url):
        text, final_url = self.get(url)
        try:
            return json.loads(text), final_url
        except ValueError as exc:
            raise FetchError("Expected JSON, received an invalid response from {}: {}".format(url, exc))


def api_url(name, node_id):
    if not str(node_id).isdigit():
        raise FetchError("nodeId must be a numeric help-site node ID, not an HTML main-* ID")
    return BASE + "/help/json/" + name + ".json?" + urlencode({"nodeId": str(node_id), "website": "cn", "language": "zh"})


def api_data(payload, source):
    if not isinstance(payload, dict):
        raise FetchError("Unexpected JSON shape: " + source)
    code = str(payload.get("code", ""))
    if code == "302":
        destination = (payload.get("data") or {}).get("redirectUrl", "")
        raise DirectoryError("Help API returned code 302 (directory or moved node), destination {}. Use catalog to enumerate all children; a redirect is not document content.".format(destination))
    if code != "200" or payload.get("success") is not True or not isinstance(payload.get("data"), dict):
        raise FetchError("Help API error from {}: code={}, success={}, message={}".format(source, code, payload.get("success"), payload.get("msg", "missing data")))
    return payload["data"]


def route(url):
    path = unquote(urlsplit(url).path).rstrip("/")
    return re.sub(r"^/(zh|en)(?=/)", "", path)


def iter_nodes(node, parents=()):
    if not isinstance(node, dict):
        raise FetchError("Invalid node in directory tree")
    yield node, parents
    children = node.get("children", [])
    if not isinstance(children, list):
        raise FetchError("Invalid children in directory tree")
    for child in children:
        yield from iter_nodes(child, parents + (node,))


def languages_for(node, parents):
    text = " ".join(str(n.get("title", "")) + " " + str(n.get("url", "")) for n in parents + (node,)).lower()
    patterns = {"java": r"\bjava\b", "go": r"\bgo(?:lang)?\b", "python": r"\bpython\b", "nodejs": r"\bnode[. -]?js\b|\bjavascript\b|\btypescript\b"}
    return [language for language, pattern in patterns.items() if re.search(pattern, text)]


def build_catalog(tree, scope="all", language=None, keywords=()):
    chosen = list(SCOPES) if scope == "all" else [scope]
    subtrees = {}
    for node, _ in iter_nodes(tree):
        alias = route(node.get("alias") or node.get("url", ""))
        for name in chosen:
            if alias == SCOPES[name]:
                subtrees[name] = node
    missing = set(chosen) - set(subtrees)
    if missing:
        raise FetchError("Current menu does not contain expected scope(s): {}. Inspect the current help-site menu; do not reuse a stale list.".format(", ".join(sorted(missing))))
    documents = []
    for name in chosen:
        for node, parents in iter_nodes(subtrees[name]):
            # A node can have both content and children (the GenAI overview does).
            if node.get("emptyNode") is True or node.get("validDocument") is False:
                continue
            if not node.get("id") or not node.get("url"):
                continue
            documents.append({"scope": name, "node_id": node["id"], "title": node.get("title", ""), "url": urljoin(BASE, node["url"]), "languages": languages_for(node, parents), "ancestors": [{"node_id": n.get("id"), "title": n.get("title", "")} for n in parents]})
    candidates = []
    for doc in documents:
        if language and doc["languages"] and language not in doc["languages"]:
            continue
        search_text = " ".join([doc["title"], doc["url"]] + [n["title"] for n in doc["ancestors"]]).casefold()
        if keywords and not any(word.casefold() in search_text for word in keywords):
            continue
        candidates.append(doc)
    return {"fetched_at": utc_now(), "source_url": api_url("menupath", MENU_SEED), "scope": scope, "filters": {"language": language, "keywords_any": list(keywords)}, "trees": subtrees, "documents": documents, "candidates": candidates, "document_count": len(documents), "candidate_count": len(candidates)}


def fetch_catalog(client, scope="all", language=None, keywords=()):
    source = api_url("menupath", MENU_SEED)
    payload, _ = client.json(source)
    tree = api_data(payload, source)
    if not tree.get("children"):
        raise FetchError("Menu response has no children; cannot enumerate sibling documents")
    return build_catalog(tree, scope, language, keywords)


def parse_ssr(page):
    match = re.search(r"window\.__ICE_PAGE_PROPS__\s*=\s*", page)
    if not match:
        raise FetchError("Page has no supported SSR JSON; refusing to treat navigation, login, or error HTML as a document")
    try:
        props, _ = json.JSONDecoder().raw_decode(page[match.end():])
        data = props["docDetailData"]["storeData"]["data"]
    except (ValueError, TypeError, KeyError) as exc:
        raise FetchError("Unsupported SSR JSON schema: " + str(exc))
    if not isinstance(data, dict):
        raise FetchError("SSR document data is not an object")
    return data


def validate_document(data, node_id=None, requested_url=None):
    actual_id = data.get("nodeId") or data.get("id")
    if not actual_id or not str(actual_id).isdigit():
        raise FetchError("Document has no real nodeId; HTML main-* IDs are not node IDs")
    if node_id is not None and str(actual_id) != str(node_id):
        raise FetchError("Document ID mismatch: requested {}, received {}".format(node_id, actual_id))
    if not isinstance(data.get("content"), str) or not data["content"].strip():
        raise FetchError("Document {} has empty content".format(actual_id))
    if not (data.get("title") or data.get("docTitle")):
        raise FetchError("Document {} has no title".format(actual_id))
    actual_url = data.get("url") or data.get("path") or data.get("alias")
    if not actual_url:
        raise FetchError("Document {} has no canonical URL".format(actual_id))
    actual_url = urljoin(BASE, actual_url)
    if requested_url and route(requested_url) != route(actual_url):
        raise DirectoryError("Requested URL resolves to a different document: {} -> {}. If the input is a directory, use catalog to enumerate all children.".format(requested_url, actual_url))
    return actual_url


class Node:
    def __init__(self, tag="", attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []


class DocumentParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def plain(node):
    if isinstance(node, str):
        return node
    if node.tag == "br":
        return "\n"
    return "".join(plain(child) for child in node.children)


def descendants(node, tag):
    for child in node.children:
        if isinstance(child, Node):
            if child.tag == tag:
                yield child
            yield from descendants(child, tag)


class Markdown:
    def __init__(self, base_url):
        self.base_url = base_url
        self.links = []

    def target(self, href, label="", kind="link"):
        url = urljoin(self.base_url, href)
        if urlsplit(url).scheme not in ("http", "https"):
            return ""
        item = {"url": url, "text": label.strip(), "kind": kind}
        if item not in self.links:
            self.links.append(item)
        return url

    def raw_table(self, node):
        # Preserve rowspan/colspan and multiline code in complex tables. Raw HTML
        # tables are legal Markdown; the original body is also saved losslessly.
        if isinstance(node, str):
            return html.escape(node, quote=False)
        if node.tag in ("script", "style"):
            return ""
        attrs = []
        for key in ("rowspan", "colspan", "href", "src", "alt"):
            value = node.attrs.get(key)
            if value:
                if key in ("href", "src"):
                    value = self.target(value, plain(node), "image" if key == "src" else "link")
                attrs.append(' {}="{}"'.format(key, html.escape(value, quote=True)))
        start = "<" + node.tag + "".join(attrs) + ">"
        if node.tag in VOID_TAGS:
            return start
        return start + "".join(self.raw_table(child) for child in node.children) + "</" + node.tag + ">"

    def render(self, node, depth=0):
        if isinstance(node, str):
            return re.sub(r"\s+", " ", node)
        tag = node.tag
        if tag in ("script", "style", "noscript"):
            return ""
        if tag == "pre":
            code = plain(node)
            fences = re.findall(r"`+", code)
            fence = "`" * max(3, 1 + max([len(x) for x in fences] or [0]))
            language = node.attrs.get("data-language", "")
            classes = node.attrs.get("class", "") + " " + " ".join(child.attrs.get("class", "") for child in node.children if isinstance(child, Node))
            match = re.search(r"(?:language|lang)-([\w+-]+)", classes)
            if match:
                language = match.group(1)
            language = language if re.fullmatch(r"[\w+-]*", language) else ""
            return "\n\n" + fence + language + "\n" + code + ("" if code.endswith("\n") else "\n") + fence + "\n\n"
        if tag == "table":
            rows = list(descendants(node, "tr"))
            complex_table = bool(list(descendants(node, "pre"))) or any(cell.attrs.get(key) not in (None, "", "1") for row in rows for cell in row.children if isinstance(cell, Node) for key in ("rowspan", "colspan"))
            if complex_table:
                return "\n\n" + self.raw_table(node) + "\n\n"
            cells = [[self.render(cell, depth).strip().replace("|", "\\|").replace("\n", "<br>") for cell in row.children if isinstance(cell, Node) and cell.tag in ("td", "th")] for row in rows]
            cells = [row for row in cells if row]
            if not cells:
                return ""
            width = max(len(row) for row in cells)
            cells = [row + [""] * (width - len(row)) for row in cells]
            lines = ["| " + " | ".join(row) + " |" for row in cells]
            lines.insert(1, "| " + " | ".join(["---"] * width) + " |")
            return "\n\n" + "\n".join(lines) + "\n\n"
        if tag in ("ul", "ol"):
            items = []
            for index, child in enumerate(child for child in node.children if isinstance(child, Node) and child.tag == "li"):
                prefix = str(index + 1) + ". " if tag == "ol" else "- "
                body = self.render(child, depth + 1).strip()
                items.append(prefix + body.replace("\n", "\n" + " " * len(prefix)))
            return "\n\n" + "\n".join(items) + "\n\n"
        content = "".join(self.render(child, depth) for child in node.children)
        if re.fullmatch(r"h[1-6]", tag):
            return "\n\n" + "#" * int(tag[1]) + " " + content.strip() + "\n\n"
        if tag in ("p", "div", "section", "main", "article", "blockquote"):
            return "\n\n" + content.strip() + "\n\n"
        if tag == "br":
            return "\n"
        if tag == "hr":
            return "\n\n---\n\n"
        if tag in ("strong", "b"):
            return "**" + content + "**" if content.strip() else content
        if tag in ("em", "i"):
            return "*" + content + "*" if content.strip() else content
        if tag == "code":
            fence = "`" * max(1, 1 + max([len(x) for x in re.findall(r"`+", content)] or [0]))
            return fence + content + fence
        if tag == "a":
            target = self.target(node.attrs.get("href", ""), plain(node))
            return "[{}](<{}>)".format(content.strip() or target, target) if target else content
        if tag == "img":
            target = self.target(node.attrs.get("src", ""), node.attrs.get("alt", ""), "image")
            return "![{}](<{}>)".format(node.attrs.get("alt", ""), target) if target else ""
        return content


def convert_html(content, url):
    parser = DocumentParser()
    parser.feed(content)
    parser.close()
    if not plain(parser.root).strip():
        raise FetchError("Document body contains no readable text")
    converter = Markdown(url)
    # Do not globally normalize newlines: that would corrupt blank lines in code.
    markdown = converter.render(parser.root).strip() + "\n"
    if not markdown.strip():
        raise FetchError("Document body contains no readable content after removing scripts and styles")
    return markdown, converter.links


def fetch_document(client, node_id=None, url=None):
    if url:
        url = safe_url(url)
        if urlsplit(url).hostname != "help.aliyun.com":
            raise FetchError("Expected a help.aliyun.com document URL")
    requested_url = url
    ssr = None
    page_source = None
    warnings = []
    if not node_id:
        node_id = SEEDS.get(route(url))
    if not node_id:
        page, page_source = client.get(url)
        ssr = parse_ssr(page)
        validate_document(ssr, requested_url=url)
        node_id = ssr.get("nodeId") or ssr.get("id")
    source = api_url("document_detail", node_id)
    try:
        payload, retrieved_from = client.json(source)
        data = api_data(payload, source)
        canonical = validate_document(data, node_id, requested_url)
        method = "help-json-api"
    except DirectoryError:
        raise
    except FetchError as exc:
        if not url:
            raise
        if ssr is None:
            page, page_source = client.get(url)
            ssr = parse_ssr(page)
        canonical = validate_document(ssr, node_id, requested_url)
        data, method, retrieved_from = ssr, "embedded-ssr-json", page_source
        warnings.append("API retrieval failed; validated SSR fallback used: " + str(exc))
    markdown, links = convert_html(data["content"], canonical)
    metadata = {"requested_url": requested_url, "requested_node_id": str(node_id), "node_id": data.get("nodeId") or data.get("id"), "title": data.get("title") or data.get("docTitle"), "source_url": canonical, "retrieved_from": retrieved_from, "retrieval_method": method, "fetched_at": utc_now(), "last_modified": data.get("lastModifiedTime"), "content_sha256": hashlib.sha256(data["content"].encode("utf-8")).hexdigest(), "body_characters": len(data["content"]), "links": links, "warnings": warnings}
    return markdown, data["content"], metadata


def github_target(url):
    """Resolve observed official blob/tree/raw URLs; do not guess branch names."""
    url = safe_url(url)
    parts = urlsplit(url)
    segments = parts.path.strip("/").split("/")
    if len(segments) < 4 or "/".join(segments[:2]) not in GITHUB_REPOS:
        raise FetchError("Only repositories linked by the GenAI documentation are supported; use an explicit blob/tree URL")
    repo = "/".join(segments[:2])
    if parts.hostname == "github.com":
        if segments[2] not in ("blob", "tree"):
            raise FetchError("Use a GitHub blob or tree URL with an explicit ref")
        kind, ref, path = segments[2], segments[3], "/".join(segments[4:])
    elif parts.hostname == "raw.githubusercontent.com":
        kind, ref, path = "blob", segments[2], "/".join(segments[3:])
    else:
        raise FetchError("Use github.com blob/tree or raw.githubusercontent.com URLs")
    if kind == "blob" and not path:
        raise FetchError("A GitHub blob URL must include a file path")
    return repo, kind, unquote(ref), unquote(path)


def source_links(source_text, public_url, extension):
    """Discover Markdown and RST links without rewriting the source file."""
    targets = re.findall(r"\[([^\]]*)\]\(([^\s)]+)\)", source_text)
    if extension == ".rst":
        targets.extend(re.findall(r"(?<!`)`([^`<]+?)\s*<([^>\s]+)>`__?", source_text))
        for quoted_label, label, href in re.findall(r"^\s*\.\.\s+_(?:`([^`]+)`|([^:\n]+)):\s*(\S+)\s*$", source_text, re.M):
            targets.append((quoted_label or label, href))
    links = []
    for label, href in targets:
        resolved = urljoin(public_url, href)
        item = {"url": resolved, "text": re.sub(r"\s+", " ", label).strip(), "kind": "link"}
        if urlsplit(resolved).scheme in ("http", "https") and item not in links:
            links.append(item)
    return links


def fetch_github(client, url, output_dir):
    repo, kind, ref, path = github_target(url)
    encoded_path = quote(path, safe="/")
    public_url = "https://github.com/{}/{}/{}/{}".format(repo, kind, quote(ref, safe=""), encoded_path).rstrip("/")
    if kind == "tree":
        source = "https://api.github.com/repos/{}/contents/{}?{}".format(repo, encoded_path, urlencode({"ref": ref}))
        payload, retrieved_from = client.json(source)
        if not isinstance(payload, list):
            raise FetchError("Expected a GitHub directory listing, received an error or file. Source: " + source)
        if len(payload) >= 1000:
            raise FetchError("GitHub Contents API listing may be truncated at 1000 entries; use the repository Git tree API or clone it explicitly")
        entries = []
        for item in payload:
            if not isinstance(item, dict) or not all(item.get(key) for key in ("name", "path", "type", "html_url")):
                raise FetchError("Invalid GitHub Contents API directory entry")
            entries.append({key: item.get(key) for key in ("name", "path", "type", "html_url", "download_url", "sha", "size")})
        body = "This is a directory listing, not article content. Select a README or source file and fetch its URL explicitly.\n\n" + "\n".join("- [{}]({}) ({})".format(entry["name"], entry["html_url"], entry["type"]) for entry in entries) + "\n"
        links = [{"url": entry["html_url"], "text": entry["name"], "kind": entry["type"]} for entry in entries]
        metadata = {"kind": "directory", "entries": entries, "retrieval_method": "github-contents-api"}
        source_text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        source = "https://raw.githubusercontent.com/{}/{}/{}".format(repo, quote(ref, safe=""), encoded_path)
        source_text, retrieved_from = client.get(source)
        if re.match(r"\s*(?:<!doctype\s+html|<html\b)", source_text, re.I):
            raise FetchError("Received HTML instead of a raw GitHub reference file: " + source)
        extension = Path(path).suffix.lower()
        if extension in (".md", ".markdown"):
            body = source_text
        else:
            fence = "`" * max(3, 1 + max([len(x) for x in re.findall(r"`+", source_text)] or [0]))
            body = fence + extension.lstrip(".") + "\n" + source_text + "\n" + fence + "\n"
        links = source_links(source_text, public_url, extension)
        metadata = {"kind": "file", "retrieval_method": "github-raw"}
    fetched_at = utc_now()
    metadata.update({"requested_url": url, "source_url": public_url, "retrieved_from": retrieved_from, "fetched_at": fetched_at, "repository": repo, "ref": ref, "path": path, "title": repo + "/" + path, "content_sha256": hashlib.sha256(source_text.encode("utf-8")).hexdigest(), "links": links})
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = "github-" + repo.split("/")[1] + "-" + hashlib.sha256(public_url.encode("utf-8")).hexdigest()[:12]
    paths = {"markdown": str((output_dir / (stem + ".md")).resolve()), "metadata": str((output_dir / (stem + ".meta.json")).resolve()), "source": str((output_dir / (stem + (".directory.json" if kind == "tree" else ".source.txt"))).resolve())}
    metadata["files"] = paths
    Path(paths["markdown"]).write_text("# {}\n\nSource: {}\n\nFetched: {}\n\n{}".format(metadata["title"], public_url, fetched_at, body), encoding="utf-8")
    Path(paths["source"]).write_text(source_text, encoding="utf-8")
    write_json(paths["metadata"], metadata)
    return {"kind": metadata["kind"], "title": metadata["title"], "source_url": public_url, "retrieval_method": metadata["retrieval_method"], "files": paths, "links": links}


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def save_document(output_dir, markdown, source_html, metadata):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = str(metadata["node_id"])
    paths = {"markdown": str((output_dir / (stem + ".md")).resolve()), "metadata": str((output_dir / (stem + ".meta.json")).resolve()), "source_html": str((output_dir / (stem + ".source.html")).resolve())}
    metadata["files"] = paths
    header = "# {}\n\nSource: {}\n\nFetched: {}\n\n".format(metadata["title"], metadata["source_url"], metadata["fetched_at"])
    Path(paths["markdown"]).write_text(header + markdown, encoding="utf-8")
    Path(paths["source_html"]).write_text(source_html, encoding="utf-8")
    write_json(paths["metadata"], metadata)
    return {"node_id": metadata["node_id"], "title": metadata["title"], "source_url": metadata["source_url"], "retrieval_method": metadata["retrieval_method"], "files": paths, "link_count": len(metadata["links"]), "warnings": metadata["warnings"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=20, help="HTTPS socket timeout in seconds (default: 20)")
    parser.add_argument("--retries", type=int, default=2, help="Additional attempts for transient transport errors (0-3)")
    parser.add_argument("--max-bytes", type=int, default=8 * 1024 * 1024, help="Maximum bytes per response (default: 8 MiB)")
    sub = parser.add_subparsers(dest="command", required=True)
    catalog = sub.add_parser("catalog", help="Fetch the fresh complete menu, preserve selected subtrees, then filter candidate documents")
    catalog.add_argument("--scope", choices=["all", "genai", "best-practices"], default="all")
    catalog.add_argument("--language", choices=["python", "java", "go", "nodejs"])
    catalog.add_argument("--keyword", action="append", default=[], help="Repeat for OR matching against title, URL, and ancestor titles")
    catalog.add_argument("--output", help="JSON output path; otherwise print complete catalog")
    fetch = sub.add_parser("fetch", help="Fetch and validate one document; directories must be enumerated with catalog")
    selector = fetch.add_mutually_exclusive_group(required=True)
    selector.add_argument("--url")
    selector.add_argument("--node-id")
    fetch.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 120 or not 0 <= args.retries <= 3 or not 1024 <= args.max_bytes <= 32 * 1024 * 1024:
        parser.error("timeout must be (0,120], retries 0-3, max-bytes 1024-33554432")
    client = Client(args.timeout, args.retries, args.max_bytes)
    try:
        if args.command == "catalog":
            result = fetch_catalog(client, args.scope, args.language, args.keyword)
            if args.output:
                write_json(args.output, result)
                result = {"output": str(Path(args.output).resolve()), "document_count": result["document_count"], "candidate_count": result["candidate_count"], "candidates": result["candidates"]}
        elif args.url and urlsplit(args.url).hostname in ("github.com", "raw.githubusercontent.com"):
            result = fetch_github(client, args.url, args.output_dir)
        else:
            markdown, source_html, metadata = fetch_document(client, args.node_id, args.url)
            result = save_document(args.output_dir, markdown, source_html, metadata)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (FetchError, OSError, ValueError) as exc:
        print("fetch_docs: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
