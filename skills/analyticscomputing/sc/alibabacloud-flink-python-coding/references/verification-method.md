# Local Checks

Choose checks appropriate to the change. `ververica-flink` supplies API inspection, not a supported local VVR runtime.

## Local

- Run applicable repository checks and [Pyright](#pyright) on job source for syntax, imports, symbols, call signatures, and types.
- Test pure-Python helpers with representative fixtures, including types/nulls and file parsing where relevant. Keep these independent of DataFrame construction or a Flink gateway.
- Check generated shell syntax and built ZIP integrity/root layout; confirm Entry Module resolves from the code archive.
- Reconcile dependency builds with the [runtime-provided/job-provided split](python-dependencies.md#exclude-runtime-packages-before-downloading), including download steps and the final package list.
- Reconcile runtime-file paths and README deployment fields with the delivered files; check [ordinary placeholders versus secret variables](platform-runtime.md#credentials-and-service-setup).

[Related commands](related-commands.md) provides syntax and archive inspection commands. Report checks actually performed and meaningful gaps.

### Pyright

Run `pyright --project pyrightconfig.json` (or the project's equivalent). Match `pythonVersion` to the job, set `pythonPlatform` to `Linux`, and scope `include` to job source. Point `extraPaths` at the directory containing the matching [extracted `pyflink` source](product-contract.md#obtain-api-source). Use available source/stubs without installing the full VVR dependency stack.

Example `pyrightconfig.json` for VVR 11.8 and Python 3.11; adapt paths and versions to the job:

```json
{
  "include": ["src"],
  "extraPaths": [".cache/vvr-api/11.8.0/source"],
  "pythonVersion": "3.11",
  "pythonPlatform": "Linux"
}
```

Review every diagnostic: fix confirmed defects and explain typing limitations, missing local dependencies, or unresolved findings. A nonzero result alone does not block delivery; report an unavailable checker as unperformed.

Reserve manual source/docstring checks for unresolved diagnostics, dynamic APIs, and semantics Pyright cannot establish, such as connector options and version-specific behavior.

### Don't do

- Do not attempt DataFrame construction/planning/execution, connector discovery or I/O, or AI/multimodal calls in the API-only local environment.
- Do not treat successful imports, syntax checks, or helper tests as proof of VVR runtime behavior, including deployed dependency, file, or secret resolution.
