#!/usr/bin/env python3
"""
PAI-Rec Engine JSON configuration validator.

Usage:
    python validate.py <config_file_path>                    # Validate a config file
    python validate.py '{"RunMode": "daily"}'                # Pass JSON string directly
    python validate.py --stdin                               # Read JSON from stdin
    echo '{"RunMode": "daily"}' | python validate.py --stdin # Pipe input

Exit codes:
    0: Validation passed
    1: Validation failed
    2: File/input error
"""

import json
import sys
import os
from pathlib import Path

# JSON Schema validation
try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


SCRIPT_DIR = Path(__file__).parent
# schema.json lives under references/ (scripts/ is reserved for executable code
# only per Agent Skill directory conventions).
SCHEMA_PATH = SCRIPT_DIR.parent / "references" / "schema.json"

# Supported recall types
VALID_RECALL_TYPES = {
    "UserCollaborativeFilterRecall",
    "UserTopicRecall",
    "VectorRecall",
    "UserCustomRecall",
    "HologresVectorRecall",
    "ItemCollaborativeFilterRecall",
    "UserGroupHotRecall",
    "UserGlobalHotRecall",
    "I2IVectorRecall",
    "ColdStartRecall",
    "MilvusVectorRecall",
    "RealTimeU2IRecall",
    "OnlineHologresVectorRecall",
    "OnlineVectorRecall",
    "GraphRecall",
    "MockRecall",
    "RecallEngineRecall",
}

# Built-in recall instance names resolvable by the engine without explicit
# RecallConfs definition. SceneConfs.RecallNames may reference these directly.
BUILTIN_RECALL_NAMES = {
    "ContextItemRecall",
}

# Supported filter types
VALID_FILTER_TYPES = {
    "User2ItemExposureFilter",
    "User2ItemCustomFilter",
    "AdjustCountFilter",
    "PriorityAdjustCountFilter",
    "PriorityAdjustCountFilterV2",
    "ItemStateFilter",
    "ItemCustomFilter",
    "CompletelyFairFilter",
    "GroupWeightCountFilter",
    "DimensionFieldUniqueFilter",
    "User2ItemExposureWithConditionFilter",
    "ConditionFilter",
    "DiversityAdjustCountFilter",
    "SnakeFilter",
    "UniqueFilter",
}

# Supported sort (rerank) types
VALID_SORT_TYPES = {
    "ItemRankScore",
    "BoostScoreSort",
    "BoostScoreByWeight",
    "DiversityRuleSort",
    "DPPSort",
    "SSDSort",
    "AlgoScoreSort",
    "TrafficControlSort",
    "MultiRecallMixSort",
    "DistinctIdSort",
    "CustomFieldSort",
    "ConditionSort",
}

# Supported EAS response function names, sourced from
# pairec/algorithm/eas/client.go SetResponseFunc(). Keep in sync with upstream.
VALID_RESPONSE_FUNC_NAMES = {
    "pssmartResponseFunc",
    "tfResponseFunc",
    "alinkFMResponseFunc",
    "tfMutValResponseFunc",
    "easyrecResponseFunc",
    "easyrecResponseFuncDebug",
    "easyrecMutValResponseFunc",
    "easyrecMutValResponseFuncDebug",
    "easyrecMutClassificationResponseFunc",
    "easyrecMutClassificationResponseFuncDebug",
    "easyrecUserEmbResponseFunc",
    "easyrecUserRealtimeEmbeddingResponseFunc",
    "easyrecUserRealtimeEmbeddingMindResponseFunc",
    "tfServingResponseFunc",
    "torchrecMutValResponseFunc",
    "torchrecMutValResponseFuncDebug",
    "torchrecEmbeddingResponseFunc",
    "torchrecEmbeddingItemsResponseFunc",
    "torchrecEmbeddingItemsResponseFuncDebug",
    "tfUseEmbResponseFunc",
    "torchrecMutClassificationResponseFunc",
    "torchrecMutClassificationResponseFuncDebug",
}

# Supported run modes
VALID_RUN_MODES = {"daily", "prepub", "product"}

# Data source adapter -> configuration key mapping
DATASOURCE_ADAPTER_MAP = {
    "hologres": "HologresConfs",
    "redis": "RedisConfs",
    "mysql": "MysqlConfs",
    "tablestore": "TableStoreConfs",
    "featurestore": "FeatureStoreConfs",
    "clickhouse": "ClickHouseConfs",
    "graph": "GraphConfs",
    "lindorm": "LindormConfs",
    "recallengine": "RecallEngineConfs",
}


class ValidationError:
    """Represents a single validation error or warning."""

    def __init__(self, path: str, message: str, severity: str = "error"):
        self.path = path
        self.message = message
        self.severity = severity  # "error" or "warning"

    def __str__(self):
        return f"[{self.severity.upper()}] {self.path}: {self.message}"

    def __eq__(self, other):
        if isinstance(other, ValidationError):
            return self.path == other.path and self.message == other.message
        return False

    def __repr__(self):
        return f"ValidationError(path={self.path!r}, message={self.message!r}, severity={self.severity!r})"


class PairecConfigValidator:
    """PAI-Rec engine configuration validator."""

    def __init__(self, config: dict):
        self.config = config
        self.errors: list[ValidationError] = []

    def validate(self) -> list[ValidationError]:
        """Run all validations and return the collected error list."""
        self.errors = []

        self._validate_run_mode()
        self._validate_recall_confs()
        self._validate_filter_confs()
        self._validate_sort_confs()
        self._validate_algo_confs()
        self._validate_scene_confs()
        self._validate_filter_names()
        self._validate_sort_names()
        self._validate_rank_conf()
        self._validate_general_rank_confs()
        self._validate_feature_confs()
        self._validate_user_feature_confs()
        self._validate_debug_confs()
        self._validate_feature_log_confs()
        self._validate_callback_confs()
        self._validate_pipeline_confs()
        self._validate_datasource_refs()

        return self.errors

    def _add_error(self, path: str, message: str, severity: str = "error"):
        self.errors.append(ValidationError(path, message, severity))

    def _validate_run_mode(self):
        """Validate RunMode."""
        run_mode = self.config.get("RunMode")
        if run_mode is not None and run_mode not in VALID_RUN_MODES:
            self._add_error(
                "RunMode",
                f"Invalid run mode '{run_mode}'. Valid values: {', '.join(sorted(VALID_RUN_MODES))}",
            )

    def _validate_recall_confs(self):
        """Validate recall configurations."""
        recall_confs = self.config.get("RecallConfs", [])
        if not isinstance(recall_confs, list):
            self._add_error("RecallConfs", "RecallConfs must be an array")
            return

        names = set()
        for i, recall in enumerate(recall_confs):
            path = f"RecallConfs[{i}]"

            if not isinstance(recall, dict):
                self._add_error(path, "Recall entry must be an object")
                continue

            # Required fields
            name = recall.get("Name")
            if not name:
                self._add_error(path, "Missing required field 'Name'")
            elif name in names:
                self._add_error(path, f"Duplicate recall name '{name}'")
            else:
                names.add(name)

            recall_type = recall.get("RecallType")
            if not recall_type:
                self._add_error(path, "Missing required field 'RecallType'")
            elif recall_type not in VALID_RECALL_TYPES:
                self._add_error(
                    path,
                    f"Invalid RecallType '{recall_type}'. Valid values: {', '.join(sorted(VALID_RECALL_TYPES))}",
                )

            recall_count = recall.get("RecallCount")
            if recall_count is None:
                self._add_error(path, "Missing required field 'RecallCount'")
            elif not isinstance(recall_count, int) or recall_count <= 0:
                self._add_error(path, "'RecallCount' must be a positive integer")

    def _validate_filter_confs(self):
        """Validate filter configurations."""
        filter_confs = self.config.get("FilterConfs", [])
        if not isinstance(filter_confs, list):
            self._add_error("FilterConfs", "FilterConfs must be an array")
            return

        names = set()
        for i, filt in enumerate(filter_confs):
            path = f"FilterConfs[{i}]"

            if not isinstance(filt, dict):
                self._add_error(path, "Filter entry must be an object")
                continue

            name = filt.get("Name")
            if not name:
                self._add_error(path, "Missing required field 'Name'")
            elif name in names:
                self._add_error(path, f"Duplicate filter name '{name}'")
            else:
                names.add(name)

            filter_type = filt.get("FilterType")
            if not filter_type:
                self._add_error(path, "Missing required field 'FilterType'")
            elif filter_type not in VALID_FILTER_TYPES:
                self._add_error(
                    path,
                    f"Invalid FilterType '{filter_type}'. Valid values: {', '.join(sorted(VALID_FILTER_TYPES))}",
                )

            # User2ItemExposureFilter: featurestore pseudo-exposure requires TimeInterval > 0
            if filter_type == "User2ItemExposureFilter":
                self._validate_exposure_filter(path, filt)

            # PriorityAdjustCountFilter/V2: require RecallName + Count per entry
            if filter_type in ("PriorityAdjustCountFilter", "PriorityAdjustCountFilterV2"):
                self._validate_priority_adjust_count(path, filt)

            # DiversityAdjustCountFilter: require Expression + Count per entry
            if filter_type == "DiversityAdjustCountFilter":
                self._validate_diversity_adjust_count(path, filt)

            # SnakeFilter: require RecallName + Weight per entry
            if filter_type == "SnakeFilter":
                self._validate_snake_filter_adjust_count(path, filt)

    def _validate_exposure_filter(self, path: str, filt: dict):
        """Validate User2ItemExposureFilter settings."""
        write_log = filt.get("WriteLog")
        dao_conf = filt.get("DaoConf", {})
        adapter_type = dao_conf.get("AdapterType", "").lower() if isinstance(dao_conf, dict) else ""

        # FeatureStore data source + pseudo exposure (WriteLog=true): TimeInterval must be set and > 0
        if write_log is True and adapter_type == "featurestore":
            time_interval = filt.get("TimeInterval")
            if time_interval is None:
                self._add_error(
                    path,
                    "FeatureStore pseudo-exposure (WriteLog=true) must configure 'TimeInterval'",
                )
            elif not isinstance(time_interval, int) or time_interval <= 0:
                self._add_error(
                    path,
                    f"FeatureStore pseudo-exposure 'TimeInterval' must be a positive integer, got: {time_interval}",
                )

    def _validate_priority_adjust_count(self, path: str, filt: dict):
        """Validate AdjustCountConfs of PriorityAdjustCountFilter/V2.

        Required fields per entry: RecallName, Count.
        """
        adjust_confs = filt.get("AdjustCountConfs", [])
        if not isinstance(adjust_confs, list) or len(adjust_confs) == 0:
            return

        # Check required fields per entry
        for j, ac in enumerate(adjust_confs):
            if not isinstance(ac, dict):
                continue
            ac_path = f"{path}.AdjustCountConfs[{j}]"
            if not ac.get("RecallName"):
                self._add_error(ac_path, "Missing required field 'RecallName'")
            if ac.get("Count") is None:
                self._add_error(ac_path, "Missing required field 'Count'")

        # Collect entries using accumulator type (default is accumulator)
        counts = []
        for j, ac in enumerate(adjust_confs):
            if not isinstance(ac, dict):
                continue
            ac_type = ac.get("Type", "accumulator")
            count = ac.get("Count")
            if ac_type == "accumulator" and isinstance(count, int):
                counts.append((j, ac.get("RecallName", f"entry#{j+1}"), count))

        # In accumulator mode, Count must be strictly increasing
        if len(counts) >= 2:
            for k in range(1, len(counts)):
                prev_idx, prev_name, prev_count = counts[k - 1]
                curr_idx, curr_name, curr_count = counts[k]
                if curr_count <= prev_count:
                    self._add_error(
                        f"{path}.AdjustCountConfs",
                        f"In accumulator mode Count must be strictly increasing: "
                        f"'{curr_name}'(Count={curr_count}) should be greater than "
                        f"'{prev_name}'(Count={prev_count}). "
                        f"Use Type='fix' if independent per-recall truncation is intended.",
                        severity="warning",
                    )
                    break  # Report once to avoid duplicate warnings

    def _validate_diversity_adjust_count(self, path: str, filt: dict):
        """Validate AdjustCountConfs of DiversityAdjustCountFilter.

        Required fields per entry: Expression, Count.
        RecallName is NOT required.
        """
        adjust_confs = filt.get("AdjustCountConfs", [])
        if not isinstance(adjust_confs, list) or len(adjust_confs) == 0:
            return

        for j, ac in enumerate(adjust_confs):
            if not isinstance(ac, dict):
                continue
            ac_path = f"{path}.AdjustCountConfs[{j}]"
            if not ac.get("Expression"):
                self._add_error(ac_path, "Missing required field 'Expression'")
            if ac.get("Count") is None:
                self._add_error(ac_path, "Missing required field 'Count'")

    def _validate_snake_filter_adjust_count(self, path: str, filt: dict):
        """Validate AdjustCountConfs of SnakeFilter.

        Required fields:
          - Filter-level: RetainNum (total items to retain, allocated by Weight ratio)
          - Per entry: RecallName, Weight.
        Count is NOT required (computed from Weight/totalWeight * RetainNum).
        """
        retain_num = filt.get("RetainNum")
        if retain_num is None:
            self._add_error(path, "Missing required field 'RetainNum' (total retain count for SnakeFilter)")
        elif not isinstance(retain_num, int) or retain_num <= 0:
            self._add_error(path, f"'RetainNum' must be a positive integer, got: {retain_num}")

        adjust_confs = filt.get("AdjustCountConfs", [])
        if not isinstance(adjust_confs, list) or len(adjust_confs) == 0:
            return

        for j, ac in enumerate(adjust_confs):
            if not isinstance(ac, dict):
                continue
            ac_path = f"{path}.AdjustCountConfs[{j}]"
            if not ac.get("RecallName"):
                self._add_error(ac_path, "Missing required field 'RecallName'")
            if ac.get("Weight") is None:
                self._add_error(ac_path, "Missing required field 'Weight'")

    def _validate_sort_confs(self):
        """Validate sort (rerank) configurations."""
        sort_confs = self.config.get("SortConfs", [])
        if not isinstance(sort_confs, list):
            self._add_error("SortConfs", "SortConfs must be an array")
            return

        names = set()
        for i, sort in enumerate(sort_confs):
            path = f"SortConfs[{i}]"

            if not isinstance(sort, dict):
                self._add_error(path, "Sort entry must be an object")
                continue

            name = sort.get("Name")
            if not name:
                self._add_error(path, "Missing required field 'Name'")
            elif name in names:
                self._add_error(path, f"Duplicate sort name '{name}'")
            else:
                names.add(name)

            sort_type = sort.get("SortType")
            if not sort_type:
                self._add_error(path, "Missing required field 'SortType'")
            elif sort_type not in VALID_SORT_TYPES:
                self._add_error(
                    path,
                    f"Invalid SortType '{sort_type}'. Valid values: {', '.join(sorted(VALID_SORT_TYPES))}",
                )

    def _validate_algo_confs(self):
        """Validate algorithm (model) configurations."""
        algo_confs = self.config.get("AlgoConfs", [])
        if not isinstance(algo_confs, list):
            self._add_error("AlgoConfs", "AlgoConfs must be an array")
            return

        names = set()
        for i, algo in enumerate(algo_confs):
            path = f"AlgoConfs[{i}]"

            if not isinstance(algo, dict):
                self._add_error(path, "Algo entry must be an object")
                continue

            name = algo.get("Name")
            if not name:
                self._add_error(path, "Missing required field 'Name'")
            elif name in names:
                self._add_error(path, f"Duplicate algo name '{name}'")
            else:
                names.add(name)

            if not algo.get("Type"):
                self._add_error(path, "Missing required field 'Type'")

            # EasConf.ResponseFuncName must match a response func registered in
            # pairec algorithm/eas/client.go SetResponseFunc(); unknown names are
            # silently ignored at runtime and the algo call will produce empty
            # response parsing, so flag them here.
            if algo.get("Type") == "EAS":
                eas_conf = algo.get("EasConf")
                if isinstance(eas_conf, dict):
                    rf_name = eas_conf.get("ResponseFuncName")
                    if not rf_name:
                        self._add_error(
                            f"{path}.EasConf",
                            "Missing required field 'ResponseFuncName'",
                        )
                    elif rf_name not in VALID_RESPONSE_FUNC_NAMES:
                        self._add_error(
                            f"{path}.EasConf.ResponseFuncName",
                            f"Unknown ResponseFuncName '{rf_name}'. Must match one of the funcs registered in pairec algorithm/eas/client.go SetResponseFunc(). Valid values: {', '.join(sorted(VALID_RESPONSE_FUNC_NAMES))}",
                        )

    def _get_defined_recall_names(self) -> set:
        """Collect all recall names defined in RecallConfs plus engine built-ins."""
        names = set(BUILTIN_RECALL_NAMES)
        for recall in self.config.get("RecallConfs", []):
            if isinstance(recall, dict) and recall.get("Name"):
                names.add(recall["Name"])
        return names

    def _get_defined_filter_names(self) -> set:
        """Collect all filter names defined in FilterConfs (plus built-ins)."""
        names = {"UniqueFilter"}  # Built-in filter
        for filt in self.config.get("FilterConfs", []):
            if isinstance(filt, dict) and filt.get("Name"):
                names.add(filt["Name"])
        return names

    def _get_defined_sort_names(self) -> set:
        """Collect all sort names defined in SortConfs (plus built-ins)."""
        names = {"ItemRankScore"}  # Built-in sort
        for sort in self.config.get("SortConfs", []):
            if isinstance(sort, dict) and sort.get("Name"):
                names.add(sort["Name"])
        return names

    def _get_defined_algo_names(self) -> set:
        """Collect all algo names defined in AlgoConfs."""
        names = set()
        for algo in self.config.get("AlgoConfs", []):
            if isinstance(algo, dict) and algo.get("Name"):
                names.add(algo["Name"])
        return names

    def _validate_scene_confs(self):
        """Validate SceneConfs reference consistency."""
        scene_confs = self.config.get("SceneConfs", {})
        if not isinstance(scene_confs, dict):
            self._add_error("SceneConfs", "SceneConfs must be an object")
            return

        defined_recalls = self._get_defined_recall_names()

        for scene_name, categories in scene_confs.items():
            if not isinstance(categories, dict):
                self._add_error(f"SceneConfs.{scene_name}", "Scene config must be an object")
                continue
            for cat_name, cat_config in categories.items():
                if not isinstance(cat_config, dict):
                    continue
                recall_names = cat_config.get("RecallNames", [])
                for rn in recall_names:
                    if rn not in defined_recalls:
                        self._add_error(
                            f"SceneConfs.{scene_name}.{cat_name}.RecallNames",
                            f"References undefined recall '{rn}'. Define it in RecallConfs.",
                            severity="warning",
                        )

    def _validate_filter_names(self):
        """Validate FilterNames reference consistency."""
        filter_names = self.config.get("FilterNames", {})
        if not isinstance(filter_names, dict):
            self._add_error("FilterNames", "FilterNames must be an object")
            return

        defined_filters = self._get_defined_filter_names()

        for scene_name, names in filter_names.items():
            if not isinstance(names, list):
                self._add_error(f"FilterNames.{scene_name}", "Filter name list must be an array")
                continue
            for fn in names:
                if fn not in defined_filters:
                    self._add_error(
                        f"FilterNames.{scene_name}",
                        f"References undefined filter '{fn}'. Define it in FilterConfs.",
                        severity="warning",
                    )

    def _validate_sort_names(self):
        """Validate SortNames reference consistency."""
        sort_names = self.config.get("SortNames", {})
        if not isinstance(sort_names, dict):
            self._add_error("SortNames", "SortNames must be an object")
            return

        defined_sorts = self._get_defined_sort_names()

        for scene_name, names in sort_names.items():
            if not isinstance(names, list):
                self._add_error(f"SortNames.{scene_name}", "Sort name list must be an array")
                continue
            for sn in names:
                if sn not in defined_sorts:
                    self._add_error(
                        f"SortNames.{scene_name}",
                        f"References undefined sort '{sn}'. Define it in SortConfs.",
                        severity="warning",
                    )

    def _validate_rank_conf(self):
        """Validate RankConf."""
        rank_conf = self.config.get("RankConf", {})
        if not isinstance(rank_conf, dict):
            self._add_error("RankConf", "RankConf must be an object")
            return

        defined_algos = self._get_defined_algo_names()

        for scene_name, rank in rank_conf.items():
            if not isinstance(rank, dict):
                continue
            path = f"RankConf.{scene_name}"

            if "RankAlgoList" not in rank:
                self._add_error(path, "Missing required field 'RankAlgoList'")
            else:
                algo_list = rank["RankAlgoList"]
                if isinstance(algo_list, list):
                    for algo_name in algo_list:
                        if algo_name not in defined_algos:
                            self._add_error(
                                f"{path}.RankAlgoList",
                                f"References undefined algo '{algo_name}'. Define it in AlgoConfs.",
                                severity="warning",
                            )

            if "RankScore" not in rank:
                self._add_error(path, "Missing required field 'RankScore'")

    def _validate_general_rank_confs(self):
        """Validate GeneralRankConfs."""
        gr_confs = self.config.get("GeneralRankConfs", {})
        if not isinstance(gr_confs, dict):
            self._add_error("GeneralRankConfs", "GeneralRankConfs must be an object")
            return

        for scene_name, gr in gr_confs.items():
            if not isinstance(gr, dict):
                continue
            path = f"GeneralRankConfs.{scene_name}"

            action_confs = gr.get("ActionConfs", [])
            for j, action in enumerate(action_confs):
                if not isinstance(action, dict):
                    continue
                action_type = action.get("ActionType")
                if action_type not in ("sort", "filter"):
                    self._add_error(
                        f"{path}.ActionConfs[{j}]",
                        f"Invalid ActionType '{action_type}'. Valid values: sort, filter",
                    )

    def _validate_feature_confs(self):
        """Validate FeatureConfs."""
        feature_confs = self.config.get("FeatureConfs", {})
        if not isinstance(feature_confs, dict):
            self._add_error("FeatureConfs", "FeatureConfs must be an object")
            return

        for scene_name, scene_conf in feature_confs.items():
            if not isinstance(scene_conf, dict):
                continue
            self._validate_scene_feature_config(f"FeatureConfs.{scene_name}", scene_conf)

    def _validate_user_feature_confs(self):
        """Validate UserFeatureConfs."""
        uf_confs = self.config.get("UserFeatureConfs", {})
        if not isinstance(uf_confs, dict):
            self._add_error("UserFeatureConfs", "UserFeatureConfs must be an object")
            return

        for scene_name, scene_conf in uf_confs.items():
            if not isinstance(scene_conf, dict):
                continue
            self._validate_scene_feature_config(f"UserFeatureConfs.{scene_name}", scene_conf)

    def _validate_scene_feature_config(self, path: str, conf: dict):
        """Validate a single scene feature configuration."""
        load_confs = conf.get("FeatureLoadConfs", [])
        if not isinstance(load_confs, list):
            self._add_error(f"{path}.FeatureLoadConfs", "FeatureLoadConfs must be an array")
            return

        for i, lc in enumerate(load_confs):
            if not isinstance(lc, dict):
                continue
            dao_conf = lc.get("FeatureDaoConf", {})
            if not isinstance(dao_conf, dict):
                continue

            lc_path = f"{path}.FeatureLoadConfs[{i}].FeatureDaoConf"

            # If LoadFromCacheFeaturesName is set, no further dao config is needed
            if dao_conf.get("LoadFromCacheFeaturesName"):
                continue

            feature_store = dao_conf.get("FeatureStore")
            if feature_store and feature_store not in ("user", "item"):
                self._add_error(
                    lc_path, f"FeatureStore must be 'user' or 'item', got: '{feature_store}'"
                )

    def _validate_debug_confs(self):
        """Validate DebugConfs."""
        debug_confs = self.config.get("DebugConfs", {})
        if not isinstance(debug_confs, dict):
            self._add_error("DebugConfs", "DebugConfs must be an object")
            return

        for scene_name, dc in debug_confs.items():
            if not isinstance(dc, dict):
                continue
            path = f"DebugConfs.{scene_name}"

            output_type = dc.get("OutputType")
            if output_type and output_type not in ("console", "datahub", "kafka", "file"):
                self._add_error(
                    path,
                    f"Invalid OutputType '{output_type}'. Valid values: console, datahub, kafka, file",
                )

            rate = dc.get("Rate")
            if rate is not None:
                if not isinstance(rate, int) or rate < 0 or rate > 100:
                    self._add_error(path, "Rate must be an integer in [0, 100]")

    def _validate_feature_log_confs(self):
        """Validate FeatureLogConfs."""
        fl_confs = self.config.get("FeatureLogConfs", {})
        if not isinstance(fl_confs, dict):
            self._add_error("FeatureLogConfs", "FeatureLogConfs must be an object")
            return

        for scene_name, flc in fl_confs.items():
            if not isinstance(flc, dict):
                continue
            path = f"FeatureLogConfs.{scene_name}"

            if not flc.get("OutputType"):
                self._add_error(path, "Missing required field 'OutputType'")

    def _validate_callback_confs(self):
        """Validate CallBackConfs."""
        cb_confs = self.config.get("CallBackConfs", {})
        if not isinstance(cb_confs, dict):
            self._add_error("CallBackConfs", "CallBackConfs must be an object")
            return

        for scene_name, cb in cb_confs.items():
            if not isinstance(cb, dict):
                continue
            path = f"CallBackConfs.{scene_name}"

            ds = cb.get("DataSource", {})
            if isinstance(ds, dict):
                if not ds.get("Name"):
                    self._add_error(f"{path}.DataSource", "Missing required field 'Name'")
                if not ds.get("Type"):
                    self._add_error(f"{path}.DataSource", "Missing required field 'Type'")

    def _validate_pipeline_confs(self):
        """Validate PipelineConfs (Pipeline.Name must be globally unique)."""
        pipeline_confs = self.config.get("PipelineConfs", {})
        if not isinstance(pipeline_confs, dict):
            self._add_error("PipelineConfs", "PipelineConfs must be an object")
            return

        all_pipeline_names = set()
        for scene_name, pipelines in pipeline_confs.items():
            if not isinstance(pipelines, list):
                self._add_error(f"PipelineConfs.{scene_name}", "Pipeline list must be an array")
                continue
            for i, pipeline in enumerate(pipelines):
                if not isinstance(pipeline, dict):
                    continue
                path = f"PipelineConfs.{scene_name}[{i}]"
                name = pipeline.get("Name")
                if not name:
                    self._add_error(path, "Missing required field 'Name'")
                elif name in all_pipeline_names:
                    self._add_error(path, f"Duplicate Pipeline name '{name}' (must be globally unique)")
                else:
                    all_pipeline_names.add(name)

    def _validate_datasource_refs(self):
        """Validate data-source references across the config."""
        self._check_datasource_ref_in_recall()
        self._check_datasource_ref_in_filter()
        self._check_datasource_ref_in_features()

    def _get_defined_datasource_names(self, conf_key: str) -> set:
        """Return the set of datasource names defined under a specific *Confs key."""
        confs = self.config.get(conf_key, {})
        if isinstance(confs, dict):
            return set(confs.keys())
        return set()

    def _check_datasource_name(self, path: str, adapter_type: str, ds_name: str):
        """Check whether a referenced datasource name exists in the corresponding *Confs."""
        conf_key = DATASOURCE_ADAPTER_MAP.get(adapter_type)
        if conf_key and ds_name:
            defined = self._get_defined_datasource_names(conf_key)
            if ds_name not in defined:
                self._add_error(
                    path,
                    f"References undefined data source '{ds_name}'. Define it in {conf_key}.",
                    severity="warning",
                )

    def _check_dao_datasource(self, path: str, dao_conf: dict):
        """Inspect a DaoConf block and validate its data-source reference."""
        adapter_type = dao_conf.get("AdapterType", "").lower()

        if adapter_type == "hologres":
            name = dao_conf.get("HologresName")
            if name:
                self._check_datasource_name(path, "hologres", name)
        elif adapter_type == "redis":
            name = dao_conf.get("RedisName")
            if name:
                self._check_datasource_name(path, "redis", name)
        elif adapter_type == "mysql":
            name = dao_conf.get("MysqlName")
            if name:
                self._check_datasource_name(path, "mysql", name)
        elif adapter_type == "tablestore":
            name = dao_conf.get("TableStoreName")
            if name:
                self._check_datasource_name(path, "tablestore", name)
        elif adapter_type == "featurestore":
            name = dao_conf.get("FeatureStoreName")
            if name:
                self._check_datasource_name(path, "featurestore", name)

    def _check_datasource_ref_in_recall(self):
        """Check data-source references inside RecallConfs."""
        for i, recall in enumerate(self.config.get("RecallConfs", [])):
            if not isinstance(recall, dict):
                continue
            path = f"RecallConfs[{i}]"

            # DaoConf
            dao = recall.get("DaoConf")
            if isinstance(dao, dict):
                self._check_dao_datasource(f"{path}.DaoConf", dao)

            # UserCollaborativeDaoConf
            uc_dao = recall.get("UserCollaborativeDaoConf")
            if isinstance(uc_dao, dict):
                self._check_dao_datasource(f"{path}.UserCollaborativeDaoConf", uc_dao)

    def _check_datasource_ref_in_filter(self):
        """Check data-source references inside FilterConfs."""
        for i, filt in enumerate(self.config.get("FilterConfs", [])):
            if not isinstance(filt, dict):
                continue
            dao = filt.get("DaoConf")
            if isinstance(dao, dict):
                self._check_dao_datasource(f"FilterConfs[{i}].DaoConf", dao)

    def _check_datasource_ref_in_features(self):
        """Check data-source references inside FeatureConfs / UserFeatureConfs."""
        for conf_key in ("FeatureConfs", "UserFeatureConfs"):
            confs = self.config.get(conf_key, {})
            if not isinstance(confs, dict):
                continue
            for scene_name, scene_conf in confs.items():
                if not isinstance(scene_conf, dict):
                    continue
                for i, lc in enumerate(scene_conf.get("FeatureLoadConfs", [])):
                    if not isinstance(lc, dict):
                        continue
                    dao = lc.get("FeatureDaoConf")
                    if isinstance(dao, dict):
                        self._check_dao_datasource(
                            f"{conf_key}.{scene_name}.FeatureLoadConfs[{i}].FeatureDaoConf",
                            dao,
                        )


def validate_with_schema(config: dict) -> list[ValidationError]:
    """Validate the configuration against the JSON Schema."""
    if not HAS_JSONSCHEMA:
        return []

    if not SCHEMA_PATH.exists():
        return []

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema = json.load(f)

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(config):
        path = ".".join(str(p) for p in error.absolute_path) or "(root)"
        errors.append(ValidationError(path, error.message))

    return errors


# Fragment-type auto-detection map
_FRAGMENT_TYPE_MAP = {
    "FilterType": "FilterConfs",
    "RecallType": "RecallConfs",
    "SortType": "SortConfs",
}


def _wrap_fragment(config: dict) -> dict:
    """If input is a single config fragment (e.g. one Filter/Recall/Sort),
    wrap it into a full config structure for validation."""
    for type_key, confs_key in _FRAGMENT_TYPE_MAP.items():
        if type_key in config and confs_key not in config:
            return {confs_key: [config]}
    return config


def validate_config(config: dict, use_schema: bool = True) -> list[ValidationError]:
    """Validate a PAI-Rec configuration and return all errors."""
    config = _wrap_fragment(config)
    errors = []

    # JSON Schema validation
    if use_schema:
        errors.extend(validate_with_schema(config))

    # Custom rule validation
    validator = PairecConfigValidator(config)
    errors.extend(validator.validate())

    return errors


def load_config(file_path: str) -> dict:
    """Load a JSON configuration file from disk."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python validate.py <config_file_path>")
        print("       python validate.py --stdin")
        print("       python validate.py '{\"RunMode\": \"daily\"}' (inline JSON string)")
        print("       echo '{...}' | python validate.py --stdin")
        sys.exit(2)

    arg = sys.argv[1]

    try:
        if arg == "--stdin":
            # Read JSON from standard input
            config = json.load(sys.stdin)
        elif os.path.exists(arg):
            # Treat as a file path
            config = load_config(arg)
        else:
            # Try to parse as an inline JSON string
            try:
                config = json.loads(arg)
            except json.JSONDecodeError:
                print("Error: argument is neither a valid file path nor a valid JSON string")
                print(f"Argument: {arg}")
                sys.exit(2)
    except json.JSONDecodeError as e:
        print(f"Error: JSON decode failed - {e}")
        sys.exit(2)

    errors = validate_config(config)

    if not errors:
        print("Validation passed: configuration is well-formed")
        sys.exit(0)
    else:
        error_count = sum(1 for e in errors if e.severity == "error")
        warning_count = sum(1 for e in errors if e.severity == "warning")

        print(f"Validation finished: {error_count} error(s), {warning_count} warning(s)\n")
        for err in errors:
            print(f"  {err}")

        sys.exit(1 if error_count > 0 else 0)


if __name__ == "__main__":
    main()
