# Prepare Deployment

Produce local deployment artifacts and instructions for an existing implementation. New-job development calls this workflow by default; modification calls it for affected artifacts.

1. Establish the job's VVR/Python versions, entry point, and [layout](../project-layout.md).
2. Apply [resolve](resolve-dependencies.md) where dependencies or runtime files are not yet resolved.
3. Follow [artifact preparation](../handoff-deliverables.md) to package modular code and needed dependencies. A single-file job needs no code ZIP.
4. Verify the produced files with the relevant [local checks](../verification-method.md), then document their [deployment fields and runtime settings](../platform-runtime.md) in the README.

The README should let the user deploy manually or pass the same artifacts and parameters to an available job-submission skill. Include the entry point, target versions, actual artifact paths, runtime arguments/settings, remaining parameter values, and checks to perform on VVR.

When a build is blocked, deliver a usable build script and identify the missing artifact and cause. Finish with artifacts whose contents and deployment mappings are known, or explicitly documented remaining work. Uploading, deploying, and starting the job belong to the separately requested submission step.
