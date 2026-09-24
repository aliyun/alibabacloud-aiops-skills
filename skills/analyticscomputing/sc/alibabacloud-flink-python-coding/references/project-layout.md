# Recommended Project Layout

For a new job, place the project directly in its working directory:

```text
<project-root>/
├── README.md
├── src/
│   └── <deployable job code>
├── scripts/
│   ├── package_code.sh          # modular code only
│   └── build_dependencies.sh    # packaged Python dependencies only
├── requirements.txt            # packaged Python dependencies only
└── artifacts/
    ├── <job>.zip                # modular code, after packaging
    └── deps.zip                 # after a successful dependency build
```

Create the files needed by the job. A single-file job can use `src/job.py` directly without a packaging script or code ZIP. Keep API source caches and local environments outside deployment artifacts.

Existing projects keep their established layout, script names, and deployment documentation location. Use this layout as a guide for the content needed, not as a migration requirement.

For runtime data, models, configuration, or JARs, preserve the supplied locations and document the [runtime mapping](runtime-files.md). [Artifact preparation](handoff-deliverables.md) describes packaging and the deployment README.
