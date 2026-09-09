# Reliable workflow for querying an unfamiliar product

The cost of skipping steps 1 and 4 is concrete: the region list gets borrowed from another
product, 7 regions never get scanned, yet the result is reported as complete coverage.
Each step below blocks one specific failure path — do not cherry-pick.

## Before querying resources of an unfamiliar product

1. **Read the parameter table with `GetApiDefinition`** — confirm two things:
   - Is there a `RegionId`? It decides whether the region goes into `params` or is routed
     via `region=`.
   - Is there a parameter with `in: host`? (e.g. SLS's `project`, OSS's `bucket`)

   ```bash
   mcpx call GetApiDefinition '{"product":"Sls","apiName":"ListLogStores","apiVersion":"2020-12-30","x_output_jmespath_filter":"{path: path, params: parameters[].{name: name, in: in}}"}'
   ```

2. **Get the authoritative command form with `GenerateCLICommand`** — do not copy the shape
   from another product's example. OpenAPI-style (ECS/VPC/RDS) and plugin-style (SLS/OSS)
   commands are completely different. In the response, prefer `unifiedCli`; if it is empty,
   use `cli`, verbatim.

3. **Determine the resource scope empirically** — call the same API in two regions and
   compare the returns:
   - Results change by region and do not overlap ⇒ **region-level**, must iterate
   - One call returns cross-region data ⇒ **account-global**, iterating is wasted effort

   "No `RegionId` in the parameter table" does **not** imply "global": SLS and OSS both
   lack it, yet their scopes are opposite.

4. **Use that product's own `ListProductRegions`** — do not borrow ECS's region list.
   SLS has 33 regions, ECS has 32; the two sets do not coincide.

5. **Run a probe before the bulk job** — call only 1–2 times, using `try/except` to verify
   how each API takes its parameters:

   ```python
   out = {}
   try:
       p = await call_cli(product="Sls", action="ListProject",
                          params={"size": 5}, region="cn-hangzhou")
       out["ListProject"] = {"ok": True, "total": p.get("total")}
       name = (p.get("projects") or [{}])[0].get("projectName")
   except Exception as exc:
       out["ListProject"] = {"ok": False, "err": str(exc)[:200]}
       name = None
   if name:
       try:
           ls = await call_cli(product="Sls", action="ListLogStores",
                               params={"project": name}, region="cn-hangzhou")
           out["ListLogStores"] = {"ok": True, "total": ls.get("total")}
       except Exception as exc:
           out["ListLogStores"] = {"ok": False, "err": str(exc)[:200]}
   result = out
   ```

   Cost: one call. It avoids discovering a wrong parameter shape only after a long job of
   hundreds of calls has finished.

6. **Scale up to the full set**, with `try/except` guarding each resource, and **keep the
   full error text** rather than recording only `True/False`.

## Every time you use x_output_jmespath_filter

- Returns `null` / empty → **call it bare first to confirm the response structure**; do not
  conclude "no data". The script prints a warning, but a warning is only a reminder — the
  re-check must actually be performed.
- The response is XML (OSS) → filter does not apply; save to disk and parse locally; judge
  pagination with `grep -E 'IsTruncated|NextMarker'`.
- A key contains non-ASCII → it must be double-quoted: `{"总数": TotalCount}` works,
  `{总数: TotalCount}` errors.

## Every time you use RunScript

- Save the return to disk **first**, then read `processID`; do not view it with `tail` /
  `head` (`processID` is at the beginning).
- Use a **whitelist** to stop polling: `None` / `InspectError` / `Stop`. Both `CallGetTask`
  (first return) and `CallGetTaskAgain` (mid-way) are non-terminal.
- Write all three kwargs of `await call_cli(...)` (`product` / `action` / `params`); pass
  `{}` even when `params` is empty.
- Use `str(exc)` for the error message, not `type(exc).__name__` (the sandbox forbids
  dunder attribute access).
- Write operations carry `costManifest`.

## Before drawing a conclusion

- **Read the errors of a bulk job one by one**, distinguishing two classes:
  - `endpoint not configured for product 'x' in region 'y'` → no service in that region,
    **not a gap**
  - `Forbidden` / `AccessDenied` → there may be resources you cannot see, **a gap that must
    be declared**
- Check whether pagination truncated the result (`IsTruncated` / `NextMarker` / `count` vs
  `total`).
- Verify the numbers reconcile (sum of parts == total).
- State the conclusion's scope explicitly: **single account**. Other member accounts under
  a resource directory require cross-account querying.
- **The equivalence of a fallback must be verified.** Switching to another data source after
  a query fails (for example, borrowing another product's region list) is an unverified
  assumption — that is exactly how the 7-region blind spot arises.
