# -*- coding: utf-8 -*-
"""
数据集解析模块：智能选表、用户权限查询、数据集相关性排序。

当用户未指定 cubeId 时，通过本模块自动匹配最合适的数据集。
"""

from __future__ import annotations

import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.utils import read_config, require_user_id, request_openapi
from common.messages import msg


# ---------------------------------------------------------------------------
# 用户权限查询
# ---------------------------------------------------------------------------

def query_accessible_cubes(*, config: Optional[dict] = None) -> List[dict]:
    """
    调用 GET /openapi/v2/smartq/query/llmCubeWithThemeList 查询用户有权限的问数数据集。
    返回 [{"cubeId": "xxx", "cubeName": "yyy"}, ...] 列表。
    """
    config = config or read_config()
    user_id = require_user_id(config)

    resp = request_openapi(
        "GET",
        "/openapi/v2/smartq/query/llmCubeWithThemeList",
        params={"userId": user_id, "runningBySkill": "true"},
        config=config,
    )
    result = resp.json()

    if not result.get("success", False):
        raise RuntimeError(
            msg("cube_permission_query_failed", code=result.get('code'), message=result.get('message'))
        )

    data = result.get("data") or {}
    if isinstance(data, str):
        data = json.loads(data)
    cube_ids_map = (data.get("cubeIds") if isinstance(data, dict) else {}) or {}

    return [
        {"cubeId": cid, "cubeName": cname}
        for cid, cname in cube_ids_map.items()
    ]


# ---------------------------------------------------------------------------
# 数据集相关性排序
# ---------------------------------------------------------------------------

def rank_cubes_by_relevance(
    question: str, cubes: List[dict], top_n: int = 2
) -> List[dict]:
    """
    根据用户问题与数据集名称的文本相关性对数据集排序，返回最相关的 top_n 个。

    评分策略：
    1. cubeName 是 question 的子串 → 高分加成
    2. question 中包含 cubeName 的连续子串 → 按最长匹配长度加分
    3. 共同字符占 cubeName 长度的比例 → 基础分
    """
    scored: List[tuple] = []
    q_lower = question.lower()

    for cube in cubes:
        name = cube.get("cubeName", "")
        if not name:
            scored.append((0.0, cube))
            continue

        n_lower = name.lower()
        score = 0.0

        if n_lower in q_lower:
            score += 100.0
        elif q_lower in n_lower:
            score += 80.0

        matcher = SequenceMatcher(None, q_lower, n_lower)
        longest = matcher.find_longest_match(0, len(q_lower), 0, len(n_lower))
        if longest.size > 0:
            score += (longest.size / max(len(n_lower), 1)) * 50.0

        common_chars = set(q_lower) & set(n_lower)
        name_chars = set(n_lower)
        if name_chars:
            score += (len(common_chars) / len(name_chars)) * 30.0

        scored.append((score, cube))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:top_n]]


# ---------------------------------------------------------------------------
# 名称直查
# ---------------------------------------------------------------------------

def match_cube_by_name(name_hint: str, cubes: List[dict]) -> dict:
    """
    按名称匹配数据集。

    匹配策略：
    1. 精确匹配（大小写不敏感、忽略首尾空格）→ status=exact
    2. 相似匹配：复用 rank_cubes_by_relevance 的评分逻辑，返回 top 3 → status=similar
    3. cubes 为空或无候选超过阈值 → status=not_found

    返回格式：
      {"status": "exact",     "cube": {"cubeId": "...", "cubeName": "..."}}
      {"status": "similar",   "candidates": [{"cubeId":..., "cubeName":..., "score":...}, ...]}
      {"status": "not_found", "candidates": []}
    """
    if not cubes:
        return {"status": "not_found", "candidates": []}

    # 1. 精确匹配
    hint_normalized = name_hint.strip().lower()
    for cube in cubes:
        cube_name = cube.get("cubeName", "")
        if cube_name.strip().lower() == hint_normalized:
            return {"status": "exact", "cube": cube}

    # 2. 相似匹配：内部执行评分逻辑（与 rank_cubes_by_relevance 一致）
    SCORE_THRESHOLD = 10.0
    scored: List[tuple] = []
    q_lower = hint_normalized

    for cube in cubes:
        name = cube.get("cubeName", "")
        if not name:
            continue

        n_lower = name.lower()
        score = 0.0

        if n_lower in q_lower:
            score += 100.0
        elif q_lower in n_lower:
            score += 80.0

        matcher = SequenceMatcher(None, q_lower, n_lower)
        longest = matcher.find_longest_match(0, len(q_lower), 0, len(n_lower))
        if longest.size > 0:
            score += (longest.size / max(len(n_lower), 1)) * 50.0

        common_chars = set(q_lower) & set(n_lower)
        name_chars = set(n_lower)
        if name_chars:
            score += (len(common_chars) / len(name_chars)) * 30.0

        if score >= SCORE_THRESHOLD:
            scored.append((score, cube))

    if not scored:
        return {"status": "not_found", "candidates": []}

    scored.sort(key=lambda x: x[0], reverse=True)
    candidates = [
        {"cubeId": cube["cubeId"], "cubeName": cube["cubeName"], "score": round(score, 1)}
        for score, cube in scored[:3]
    ]
    return {"status": "similar", "candidates": candidates}


# ---------------------------------------------------------------------------
# 智能选表
# ---------------------------------------------------------------------------

def call_table_search(
    question: str,
    *,
    cube_ids: Optional[List[str]] = None,
    config: Optional[dict] = None,
) -> List[str]:
    """
    调用 POST /openapi/v2/smartq/tableSearch 进行智能选表。
    当用户未指定 cubeId 时，根据问题自动匹配最合适的数据集。
    返回匹配到的 cubeId 列表。
    """
    config = config or read_config()
    user_id = require_user_id(config)

    payload: Dict[str, Any] = {
        "userId": user_id,
        "userQuestion": question,
        "llmNameForInference": "SYSTEM_deepseek-r1-0528",
        "runningBySkill": True,
    }
    if cube_ids:
        payload["cubeIds"] = cube_ids

    resp = request_openapi(
        "POST",
        "/openapi/v2/smartq/tableSearch",
        json_body=payload,
        config=config,
    )
    body = resp.json()
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        if str(body.get("success", "")).lower() != "true":
            raise RuntimeError(msg("cube_table_search_failed", code=body.get('code'), message=body.get('message')))
        data = body.get("data")
        if isinstance(data, list):
            return data
        if isinstance(data, str) and data != "null":
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
    return []


# ---------------------------------------------------------------------------
# 常量配置
# ---------------------------------------------------------------------------

# 智能选表批次大小降级序列：从大到小尝试，避免触发接口 cubeIds 数量限制
# 当接口返回 "cubeIds can not be empty or over limit" 时自动降级到下一档
TABLE_SEARCH_BATCH_SIZES = [30, 10]


# ---------------------------------------------------------------------------
# 组合：数据集解析
# ---------------------------------------------------------------------------

def resolve_cube_id(
    question: str,
    *,
    name_hint: Optional[str] = None,
    cube_ids: Optional[List[str]] = None,
    config: Optional[dict] = None,
) -> Optional[str]:
    """
    完整的数据集解析流程：
    1. 查询用户有权限的问数数据集列表
    1.5 若提供了 name_hint，先尝试名称直查（精确匹配时直接返回）
    2. 将权限数据集 cubeIds（与调用方传入的候选合并）按文本相关性预筛选
    3. 使用自适应降级策略调用智能选表（尝试批次大小 [30, 10]）
    4. 智能选表未匹配时，按文本相关性从权限数据集中选择最相关的

    返回解析到的 cubeId，全部失败时返回 None。
    """
    config = config or read_config()

    print(f"{'=' * 60}", flush=True)
    print(msg("cube_smart_select_start"), flush=True)
    print(msg("cube_smart_select_question", question=question), flush=True)
    print(f"{'=' * 60}", flush=True)

    # Step 1: 查询用户有权限的数据集
    try:
        accessible = query_accessible_cubes(config=config)
    except Exception as e:
        print(msg("cube_permission_failed", exc=e), flush=True)
        return None

    if not accessible:
        print(msg("cube_no_permission"), flush=True)
        print(msg("cube_no_datasets_promo"), flush=True)
        return None

    print(msg("cube_accessible_count", count=len(accessible)), flush=True)
    for item in accessible[:10]:
        print(f"  - {item['cubeId']}  {item['cubeName']}", flush=True)
    if len(accessible) > 10:
        print(msg("cube_accessible_total", count=len(accessible)), flush=True)

    # Step 1.5: 名称直查（当提供了 name_hint 时）
    if name_hint:
        print(msg("cube_name_lookup_start", name=name_hint), flush=True)
        lookup_result = match_cube_by_name(name_hint, accessible)
        if lookup_result["status"] == "exact":
            cube = lookup_result["cube"]
            print(msg("cube_name_lookup_exact", cube_name=cube["cubeName"], cube_id=cube["cubeId"]), flush=True)
            return cube["cubeId"]
        elif lookup_result["status"] == "similar":
            print(msg("cube_name_lookup_similar", count=len(lookup_result["candidates"])), flush=True)
        else:
            print(msg("cube_name_lookup_not_found", name=name_hint), flush=True)

    # Step 2: 合并权限 cubeIds 与调用方传入的候选
    accessible_ids = [item["cubeId"] for item in accessible]
    if cube_ids:
        merged = list(dict.fromkeys(cube_ids + accessible_ids))
    else:
        merged = accessible_ids

    # Step 3: 使用自适应降级策略调用智能选表
    matched_cube_ids: List[str] = []
    
    # 预筛选：按文本相关性对所有候选排序
    ranked_all = rank_cubes_by_relevance(question, accessible, top_n=len(accessible))
    ranked_id_to_cube = {cube["cubeId"]: cube for cube in accessible}
    
    # 将 merged 中的 ID 按相关性排序
    merged_set = set(merged)
    ranked_merged_ids = [cube["cubeId"] for cube in ranked_all if cube["cubeId"] in merged_set]
    
    for batch_size in TABLE_SEARCH_BATCH_SIZES:
        # 截取当前批次的候选 ID
        candidates = ranked_merged_ids[:batch_size]
        
        if not candidates:
            continue
        
        print(msg("cube_smart_select_trying", count=len(candidates)), flush=True)
        
        try:
            matched_cube_ids = call_table_search(question, cube_ids=candidates, config=config)
            if matched_cube_ids:
                print(msg("cube_smart_select_success", count=len(candidates)), flush=True)
                break  # 找到匹配，提前终止
        except Exception as e2:
            error_msg = str(e2)
            if "cubeIds can not be empty or over limit" in error_msg:
                print(msg("cube_smart_select_over_limit", count=len(candidates)), flush=True)
                continue  # 尝试更小批次
            # 其他异常直接抛出
            print(msg("cube_smart_select_failed", exc=e2), flush=True)
            matched_cube_ids = []
            break

    if matched_cube_ids:
        cube_id = matched_cube_ids[0]
        print(msg("cube_smart_select_matched", cube_id=cube_id), flush=True)
        if len(matched_cube_ids) > 1:
            print(msg("cube_smart_select_others", others=matched_cube_ids[1:]), flush=True)
        return cube_id

    # Step 4: 智能选表未匹配，按文本相关性从权限数据集中选择
    ranked = rank_cubes_by_relevance(question, accessible, top_n=2)
    cube_id = ranked[0]["cubeId"]
    print(msg("cube_relevance_fallback"), flush=True)
    for i, rc in enumerate(ranked):
        tag = msg("cube_relevance_selected") if i == 0 else msg("cube_relevance_candidate")
        print(f"  {tag}: {rc['cubeId']}  {rc['cubeName']}", flush=True)
    return cube_id
