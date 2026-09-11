"""Differential restore engine - ACL policy comparison and on-demand restore

Background: ACL policies allow duplicate names, and the plugin's built-in restore is a blind
append (all rows inserted at the end), which produces fully duplicated policies in the
"restore from the backup account itself" scenario. This module first renders the live existing
policies using the plugin's own column definitions, compares them row by row against the backup
sheet by signature, and only restores the rows missing online.

Signature rule: (column name, normalized value) tuples of all columns except the volatile ones
(priority/restore status). Normalization: empty values (None/NaN/''/'nan') are normalized to an
empty string; booleans are normalized to 'true'/'false'; everything else is stripped and converted
to string. Values rendered by live getters and values read back from Excel are compared after the
same normalization.
"""
import os
import tempfile

import pandas as pd

from core import BackupEngine, call_api

# Order/status columns do not participate in comparison (priority changes with the insertion
# position, and restore status is a local tracking column)
SKIP_COLS = {"优先级", "恢复状态"}


def _norm(v):
    """Normalize a value: empty values to empty string, booleans to true/false, everything else stripped and converted to string"""
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    if isinstance(v, bool) or type(v).__name__ in ("bool_",):
        return "true" if v else "false"
    s = str(v).strip()
    if s.lower() in ("nan", "none"):
        return ""
    if s in ("true", "false", "True", "False"):
        return s.lower()
    return s


def _signature(row_dict):
    """Row signature: (column name, normalized value) tuples of all columns except the volatile ones"""
    return tuple((k, _norm(v)) for k, v in row_dict.items() if k not in SKIP_COLS)


def _live_signatures(engine, plugin):
    """Fetch live data and render it into a signature set using the plugin's column definitions"""
    items = engine.fetch(plugin)
    sigs = set()
    for item in items:
        row = {}
        for col_name, getter in plugin.columns:
            if col_name in SKIP_COLS:
                continue
            try:
                row[col_name] = getter(item)
            except Exception:
                row[col_name] = ""
        sigs.add(_signature(row))
    return sigs, len(items)


def _backup_rows(excel_file, sheet_name):
    """Read the backup sheet and return ([(signature, row index)], DataFrame)"""
    df = pd.read_excel(excel_file, sheet_name=sheet_name)
    rows = []
    for idx in range(len(df)):
        row_dict = {col: df.iloc[idx].get(col, "") for col in df.columns}
        rows.append((_signature(row_dict), idx))
    return rows, df


def diff_restore(plugin, excel_file, ak, sk, region, apply=True, security_token=None):
    """Compare live configurations with the backup and return the missing row count; when apply=True, only restore the missing rows.

    Returns:
        (missing_count, live_count, backup_count)
    """
    engine = BackupEngine(ak, sk, region, security_token=security_token)
    live_sigs, live_count = _live_signatures(engine, plugin)
    b_rows, df = _backup_rows(excel_file, plugin.sheet_name)
    missing = [(sig, idx) for sig, idx in b_rows if sig not in live_sigs]

    print(f"  [{plugin.name}] live: {live_count} rows | backup: {len(b_rows)} rows | missing: {len(missing)} rows")

    if not missing:
        return (0, live_count, len(b_rows))

    # Show missing rows (policy name or the first column)
    name_col = "策略名称" if "策略名称" in df.columns else df.columns[0]
    for _, idx in missing[:20]:
        print(f"    - backup row {idx + 2}: {df.iloc[idx].get(name_col, '?')}")
    if len(missing) > 20:
        print(f"    ... and {len(missing) - 20} more rows")

    if not apply:
        return (len(missing), live_count, len(b_rows))

    # Write only the missing rows to a temporary Excel and reuse the plugin's own restore logic
    sub = df.iloc[[idx for _, idx in missing]].copy()
    if "恢复状态" in sub.columns:
        sub = sub.drop(columns=["恢复状态"])

    tmp_dir = tempfile.mkdtemp(prefix="cfw_diff_restore_")
    tmp_file = os.path.join(tmp_dir, f"missing_{plugin.sheet_name}.xlsx")
    with pd.ExcelWriter(tmp_file) as writer:
        sub.to_excel(writer, sheet_name=plugin.sheet_name, index=False)

    print(f"  >>> restoring only the {len(missing)} missing policies (temporary file: {tmp_file})")
    plugin.restore(ak=ak, sk=sk, region=region, call_api_fn=call_api,
                   excel_file=tmp_file, security_token=security_token)
    return (len(missing), live_count, len(b_rows))
