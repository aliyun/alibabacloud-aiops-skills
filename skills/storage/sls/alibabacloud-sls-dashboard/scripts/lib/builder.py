"""Compile explicit SLS plans; no network access or semantic model expansion."""
from __future__ import annotations

import copy
import re

from .common import METRIC, SkillError, deep_merge, schema_check
from .charts import aggpro, burgauge, linepro, piepro, statpro


def unique_map(items, key, kind):
    result = {}
    for item in items:
        if item[key] in result:
            raise SkillError(f"Duplicate {kind}: {item[key]}")
        result[item[key]] = item
    return result


def compile_query(query, sources):
    if query["source"] not in sources:
        raise SkillError("Unknown query source", source=query["source"])
    source = sources[query["source"]]
    result = {"name": query["name"], "datasource": source["type"],
              "project": source["project"], "logstore": source["name"], "region": source["region"],
              "query": query["query"], "tokenQuery": query["query"]}
    if source["type"] in METRIC:
        result.update(queryType=query.get("queryType", "range"), interval=query.get("interval", "60s"),
                      limit=query.get("limit", 10000), format=query.get("format", "time_series"))
        if "legendFormat" in query:
            result["legendFormat"] = query["legendFormat"]
    elif any(key in query for key in ("queryType", "interval", "limit", "format", "legendFormat")):
        raise SkillError("Metric query options require metricstore or metricstore_storeview; "
                         "SQL limits and grouping belong in SQL")
    if "hide" in query:
        result["hide"] = query["hide"]
    unique_map(query.get("fields", []), "name", "result field")
    return result


def display_binding(chart, queries):
    typ = chart["type"]
    expected_config = {"statpro": "stat", "piepro": "pie", "burgauge": "gauge", "aggpro": "agg"}.get(typ)
    if set(chart.get("config", {})) - ({expected_config} if expected_config else set()):
        raise SkillError("Chart config does not match its chart type", "CHART_CONTRACT_ERROR")
    entries = chart.get("queries", [])
    metric = bool(queries) and all(q["datasource"] in METRIC and q.get("format") == "time_series" for q in queries)
    adapter = {"key": chart["id"], "title": chart["title"], "type": typ,
               "datasources": [{"queryResultFields": [{"name": f["name"], "dataType": f["type"]}
                               for f in q.get("fields", [])]} for q in entries], **chart.get("config", {})}
    if typ == "linepro":
        patch = linepro.direct_display_patch(adapter, "", [], True, len(queries) > 1)
        if not metric:
            bindings = {}
            axis_modes = set()
            explicit = chart.get("display", {})
            if "isTimeSeries" in explicit and type(explicit["isTimeSeries"]) is not bool:
                raise SkillError("display.isTimeSeries must be boolean")
            if not isinstance(explicit.get("queryOptionMap", {}), dict):
                raise SkillError("display.queryOptionMap must be an object")
            for q in entries:
                fields = q.get("fields", [])
                supplied = explicit.get("queryOptionMap", {}).get(q["name"])
                if supplied is not None:
                    if (not isinstance(supplied, dict) or not isinstance(supplied.get("xAxisKey"), str)
                            or not supplied["xAxisKey"] or not isinstance(supplied.get("yAxisKeys"), list)
                            or not supplied["yAxisKeys"] or any(not isinstance(v, str) or not v for v in supplied["yAxisKeys"])):
                        raise SkillError("Line binding requires xAxisKey and a non-empty yAxisKeys array")
                    binding = copy.deepcopy(supplied)
                    declared = {f["name"]: f["type"] for f in fields}
                    if declared and (binding["xAxisKey"] not in declared or any(
                            declared.get(v) != "number" for v in binding["yAxisKeys"])):
                        raise SkillError("Line bindings must select declared X and numeric Y fields")
                    x_type = declared.get(binding["xAxisKey"])
                else:
                    x = [f for f in fields if f["type"] == "time"]
                    if not x:
                        x = [f for f in fields if f["type"] == "string"]
                    values = [f["name"] for f in fields if f["type"] == "number"]
                    if len(x) != 1 or not values:
                        raise SkillError("Line chart needs an explicit binding or one declared time/dimension field and numeric fields")
                    binding = {"xAxisKey": x[0]["name"], "yAxisKeys": values}
                    x_type = x[0]["type"]
                if "isTimeSeries" not in explicit and x_type not in {"time", "string"}:
                    raise SkillError("Set display.isTimeSeries explicitly when the X field's time/category meaning is unknown")
                axis_modes.add(explicit.get("isTimeSeries", x_type == "time"))
                bindings[q["name"]] = binding
            if len(axis_modes) > 1:
                raise SkillError("Line queries must use compatible time or category axes")
            patch["isTimeSeries"] = next(iter(axis_modes), True)
            if not patch["isTimeSeries"] and len(queries) > 1:
                raise SkillError("A category-axis line chart needs a single query result")
            patch["queryOptionMap"] = bindings
        patch["legendOption"]["show"] = metric or sum(
            f["type"] == "number" for q in entries for f in q.get("fields", [])) > 1
        return patch
    if typ == "tablepro":
        return {}
    modules = {"statpro": statpro, "piepro": piepro, "burgauge": burgauge, "aggpro": aggpro}
    if typ in modules:
        if typ == "aggpro" and metric:
            raise SkillError("Native metric series use linepro; aggpro requires grouped tabular results")
        module = modules[typ]
        if typ == "statpro" and "stat" not in adapter:
            if metric:
                adapter["stat"] = {"reducer": "lastNotNull"}
            else:
                values = list(dict.fromkeys(f["name"] for q in entries for f in q.get("fields", [])
                                           if f["type"] == "number"))
                adapter["stat"] = {"mode": "calculate", "valueFields": values, "reducer": "lastNotNull"}
        try:
            patch = module.metric_display_patch(adapter, queries) if metric else module.direct_display_patch(adapter)
        except ValueError as exc:
            message = str(exc).replace("queryResultFields", "queries[].fields").replace("dataType", "type")
            for name in ("stat", "pie", "gauge", "agg"):
                message = message.replace(f"charts[].{name}", f"charts[].config.{name}")
            raise SkillError(message, "CHART_CONTRACT_ERROR") from exc
        refs = {chr(65 + i) if i < 8 else f"REF{i}": q["name"] for i, q in enumerate(entries)}
        if "queryOptionMap" in patch and not metric:
            patch["queryOptionMap"] = {refs.get(k, k): v for k, v in patch["queryOptionMap"].items()}
        return patch
    if typ == "dashboardrow":
        if queries:
            raise SkillError("Row containers do not have queries")
        return {"rowChartOption": {"collasped": False}}
    if typ in {"timeseriesPro", "facetPro"}:
        if len(queries) != 1:
            raise SkillError("Algorithm charts require exactly one query")
        return {}
    if not chart.get("display"):
        raise SkillError(f"{typ} requires explicit display bindings from its chart reference; "
                         "automatic binding is not available", "EXPLICIT_BINDING_REQUIRED")
    return {}


def compile_control(control, sources):
    mode, key = control["mode"], control["key"]
    values = control.get("values", [])
    defaults = control.get("defaults", [])
    if any(value not in values for value in defaults):
        raise SkillError("Static defaults must refer to declared values")
    if "aliases" in control and len(control["aliases"]) != len(values):
        raise SkillError("Control aliases must align with values")
    if "query" in control and (values or defaults):
        raise SkillError("Dynamic candidate controls cannot contain sampled static values/defaults")
    source = sources.get(control.get("source"))
    if mode == "filter" and (not source or source["type"] not in {"logstore", "logstore_storeview"}):
        raise SkillError("Field filters require a log datasource")
    option = {"type": mode, "key": key, "alias": control.get("label", key),
              "list": values, "listAlias": control.get("aliases", [])}
    queries = []
    if mode == "adhoc":
        if not source or source["type"] not in METRIC or not re.fullmatch(r"\w+", key):
            raise SkillError("Adhoc requires a metricstore datasource and a stable word key")
        forbidden = {"query", "values", "defaults", "multiSelect", "includeAll", "allValue", "valueField"}
        if forbidden.intersection(control):
            raise SkillError("Adhoc does not use token options or candidate queries")
        queries = [{"name": "A", "datasource": source["type"], "project": source["project"],
                    "logstore": source["name"], "region": source["region"], "query": "", "tokenQuery": ""}]
        option["globalFilter"] = True
    else:
        option["tokenDefault" if mode == "token" else "listDefault"] = [v in defaults for v in values]
        if mode == "token":
            option.update(showType="select", multiSelect=control.get("multiSelect", False),
                          includeAll=control.get("includeAll", False))
            if option["includeAll"]:
                if "allValue" not in control:
                    raise SkillError("An All option requires an explicit allValue")
                option["allValue"] = control["allValue"]
            if option["multiSelect"]:
                option["customTemplate"] = control.get("customTemplate", '<%= data.join("|") %>')
            if "valueField" in control:
                option["multipleTokenKey"] = control["valueField"]
        if "query" in control:
            if source and control["query"]["source"] != source["id"]:
                raise SkillError("Control candidate source must match its declared source")
            queries = [compile_query(control["query"], sources)]
    display = {"version": "2", "showDropListChart": True, "dropListOption": option,
               "bindQuery": bool(queries) and mode != "adhoc",
               "basicOptions": {"showTitle": False, "showTime": False, "showBackground": False, "showBorder": False}}
    return display, queries


def build(plan, facts=None):
    schema_check(plan, "plan")
    sources = unique_map(plan["sources"], "id", "source")
    controls = unique_map(plan.get("controls", []), "id", "control")
    unique_map(plan["charts"], "id", "chart")
    unique_map([c for c in controls.values() if c["mode"] == "token"], "key", "token")
    for fact in facts or []:
        schema_check(fact, "source-facts")
        source = sources.get(fact["source"]["id"])
        if source != fact["source"]:
            raise SkillError("Facts do not match the Plan source identity")
    charts, used_controls = [], set()
    for item in plan["charts"]:
        entries = item.get("queries", [])
        unique_map(entries, "name", "query")
        queries = [compile_query(query, sources) for query in entries]
        if item["type"] == "imagePro" and not queries:
            queries = [{"name": "A", "datasource": "builtin", "type": "random_time_line"}]
        if item["type"] == "droplistpro":
            ref = item.get("control")
            if ref not in controls or ref in used_controls or queries:
                raise SkillError("A droplist requires one unique control reference and no chart queries")
            used_controls.add(ref)
            patch, queries = compile_control(controls[ref], sources)
        else:
            if "control" in item:
                raise SkillError("Only droplistpro may refer to a control")
            patch = display_binding(item, queries)
        display = deep_merge({"basicOptions": {"displayName": item["title"], "showTitle": True,
                              "showTime": True, "showBorder": True, "showBackground": True}}, patch)
        display = deep_merge(display, item.get("display", {}))
        display.update(dict(zip(("xPos", "yPos", "width", "height"),
                                (item["layout"][key] for key in ("x", "y", "w", "h")))))
        if "actions" in item:
            display["actionOptions"] = copy.deepcopy(item["actions"])
        search = {"chartQueries": queries, "start": "-3600s", "end": "now", "timeSpanType": "",
                  "dataSourceType": "mixed", "transformers": copy.deepcopy(item.get("transformers", []))}
        if {"chartQueries", "transformers"}.intersection(item.get("search", {})):
            raise SkillError("Use Plan queries/transformers, not search overrides, for query construction")
        search.update(copy.deepcopy(item.get("search", {})))
        if item["type"] == "droplistpro":
            search["isInheritFilter"] = controls[item["control"]].get("inheritFilter", False)
        charts.append({"title": item["id"], "type": item["type"], "display": display, "search": search, "action": {}})
    if used_controls != set(controls):
        raise SkillError("Every declared control needs one visible droplist chart")
    return {"displayName": plan["dashboard"]["displayName"],
            "description": plan["dashboard"].get("description", ""),
            "attribute": {"type": plan["dashboard"].get("layout", "grid")}, "charts": charts}
