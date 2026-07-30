# Project Layout

Resolve the layout before the first implementation write.

## Select the layout branch

- **New project created by the current request:** place the canonical layout directly in the project root, with no wrapper or delivery directory.
- **Existing project:** preserve its established source, dependency, artifact, runtime-file, and deployment-documentation locations. Use the canonical layout as a content checklist. The two applicable project-side packaging scripts keep their fixed paths under `scripts/`; adapt their path handling to the existing repository.

## Canonical new-project layout

```text
<project-root>/
├── README.md
├── src/
│   └── <all deployable job code>
├── scripts/
│   ├── package_code.sh          # packages modular job code
│   └── build_dependencies.sh    # builds non-pre-installed Python packages
├── requirements.txt             # only with non-pre-installed packages
└── artifacts/
    ├── <job>.zip                # only for modular code, after packaging
    └── deps.zip                 # only after a successful dependency build
```

Add runtime data, models, certificates, configuration, or JARs only when the operation graph reads them. Place them according to [runtime-files.md](runtime-files.md), and omit empty directories and unused conditional files.

## Apply the selected layout

- Put deployable source in `src/` for a new project or the established source location for an existing project.
- Put deployment documentation in the new-project root `README.md`; for an existing project, update its established documentation or use the root `README.md` when none exists.
- Generate `scripts/package_code.sh` only for modular code and `scripts/build_dependencies.sh` only for non-pre-installed third-party packages. These paths remain fixed in both layout branches.
- Put generated archives under `artifacts/` for a new project or the established artifact location for an existing project.
- Preserve unrelated files and repository conventions.

## Completion criterion

Complete layout selection when the repository is classified as new or existing; every required source, documentation, dependency, runtime-file, script, and artifact location is explicit; and each conditional path is either required by the artifact list or omitted.
