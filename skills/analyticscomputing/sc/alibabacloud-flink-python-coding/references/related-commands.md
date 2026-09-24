# Useful Local Commands

Use the project's tools and paths where established.

| Purpose | Example |
|---|---|
| Locate an already-installed API distribution | `python -m pip show -f ververica-flink` |
| Compile Python | `python -m py_compile <file.py>` |
| Check shell syntax | `bash -n <script.sh>` |
| Test a ZIP | `python -m zipfile -t <archive.zip>` |
| Inspect the archive root | `python -m zipfile -l <archive.zip>` |

Use the generated or existing build script's documented arguments for code and dependency packaging. API source inspection and these local checks do not execute a VVR job.
