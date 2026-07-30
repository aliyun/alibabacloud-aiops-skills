# Runtime File Dependencies

Use this reference for every data file, model weight, configuration, certificate, lookup table, or other file opened by job code or a Python callback.

## Resolve every file read

Record one mapping for each reachable read:

| Field | Required value |
|---|---|
| Source | Artifact name and owning repository or system |
| Consumer | Function and expected format |
| Local validation | Fixture path and availability |
| VVR attachment | Upload mode and uploaded artifact |
| Target path | Exact path used by target code |
| Validation status | Locally checked or VVR-only |

When the source artifact is unavailable, mark it unresolved and use a bounded fixture only when its path and format are explicit. Keep the file path configurable so local fixtures and VVR attachments can use different values.

## Select the upload mode

| Mode | Select when | Target contract |
|---|---|---|
| Python Archives | Related files require stable relative paths | If `data.zip` contains `mydata/data.txt`, use the confirmed archive-relative path `data.zip/mydata/data.txt` |
| Additional Dependency Files | Independent files are attached separately | Use the confirmed `/flink/usrlib/<filename>` path |

Record each file's local path, uploaded artifact, attachment field, and target path in the deployment documentation. Use [platform-runtime.md](platform-runtime.md) as the single source for console-field mapping. Treat uploaded-file debugging behavior as a VVR-only check.

## Completion criterion

Complete runtime-file resolution when every reachable file read has all six mapping fields, target code uses the configurable confirmed path, and credential values are absent from the artifact and path configuration.
