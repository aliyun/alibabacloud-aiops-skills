"""Read variable references from effective query inputs without changing JSON."""
import re

TOKEN = re.compile(r"\$\{\{([^{}|]+)(\|[^{}]*)?\}\}|\$\{([^{}|]+)(?:\|[^{}]*)?\}")


def token_requirements(texts):
    """Map names to whether any occurrence needs a value without a default."""
    found = {}
    for text in texts:
        if not isinstance(text, str):
            continue
        for match in TOKEN.finditer(text):
            name = (match[1] or match[3]).strip()
            if name:
                needs_value = match[1] is None or match[2] is None
                found[name] = found.get(name, False) or needs_value
    return found


def first_text(mapping, keys):
    return next(
        (mapping[key] for key in keys if isinstance(mapping.get(key), str) and mapping[key]), ""
    )


def query_inputs(chart):
    search, display = chart.get("search"), chart.get("display")
    if not isinstance(search, dict) or not isinstance(display, dict):
        return
    option = display.get("dropListOption")
    if (
        chart.get("type") == "droplistpro"
        and isinstance(option, dict)
        and option.get("type") in ("filter", "token")
        and not display.get("bindQuery")
    ):
        return
    if "chartQueries" in search:
        queries = search["chartQueries"]
        if not isinstance(queries, list):
            return
        for query in queries:
            if (
                not isinstance(query, dict)
                or query.get("hide") is True
                or query.get("datasource") == "builtin"
            ):
                continue
            fields = (
                ("expr", "tokenQuery", "query")
                if query.get("datasource") == "prometheus"
                else ("tokenQuery", "query")
            )
            yield first_text(query, fields)
            yield query.get("logstore")
            if search.get("dataSourceType") == "mixed":
                yield query.get("project")
            if query.get("datasource") in ("metricstore", "metricstore_storeview"):
                yield query.get("interval")
    else:
        token_map = search.get("tokenQueryMap")
        token_map = token_map if isinstance(token_map, dict) else {}
        sub = search.get("subSearch")
        queries = [search] + (sub if isinstance(sub, list) else [])
        for index, query in enumerate(queries):
            if not isinstance(query, dict):
                continue
            yield first_text(
                {"tokenQuery": token_map.get(str(index)), "query": query.get("query")},
                ("tokenQuery", "query"),
            )
            yield query.get("logstore")
