# Product Mapping (Keywords → Products → Toolsets)

## Product Functional Boundaries

| Product | Code Name | Toolset | Core Objects |
|---------|-----------|---------|-------------|
| Pipeline | Flow | `pipeline-management` | Pipelines, builds, deployments, jobs, service connections |
| Code Management | Codeup | `code-management` | Repositories, branches, files, commits, merge requests (MR), comments |
| Artifact Repository | Packages | `packages-management` | Artifact repositories, artifacts, versions |
| Project Collaboration | Projex | `project-management` | Projects, programs, sprints, work items, versions, work hours |
| Test Management | Testhub | `test-management` | Test case directories, test cases, test plans, test results |
| Application Delivery | AppStack | `application-delivery` | Applications, orchestrations, change orders, release workflows, environment variables |
| Organization Management | - | `organization-management` | Members, departments, roles |
| Base | - | `base` | Current user, current organization |

## Keyword Mapping Table

| Keyword | Mapped Product | Toolset |
|---------|---------------|---------|
| Pipeline, CI/CD, build, compile, continuous integration, continuous delivery, release pipeline | Flow | `pipeline-management` |
| Deploy, run, execute pipeline, pipeline instance | Flow | `pipeline-management` |
| YAML, pipeline YAML, pipeline configuration | Flow | `pipeline-management` |
| Service connection, connection credentials (for pipelines) | Flow | `pipeline-management` |
| Code, code repository, Repo, repository (code) | Codeup | `code-management` |
| Branch, commit, Commit, file, directory (code) | Codeup | `code-management` |
| Merge request, MR, PR, code review, review comment | Codeup | `code-management` |
| Artifact, package, Package, Artifact, Maven, NPM, Docker image | Packages | `packages-management` |
| Artifact repository, binary repository | Packages | `packages-management` |
| Requirement, defect, Bug, task, work item, Issue | Projex | `project-management` |
| Sprint, Sprint, sprint plan | Projex | `project-management` |
| Project (collaboration), program, Program, version (project) | Projex | `project-management` |
| Work hours (effort), estimated hours, time tracking | Projex | `project-management` |
| Test case, Case, test directory | Testhub | `test-management` |
| Test plan, test task, test result, test report | Testhub | `test-management` |
| Application, App, application template, application tag | AppStack | `application-delivery` |
| Orchestration, Orchestration, application orchestration | AppStack | `application-delivery` |
| Change order (deployment unit) | AppStack | `application-delivery` |
| Application change request (approval workflow) | AppStack | `application-delivery` |
| Release workflow, release stage, Release Workflow, Release Stage | AppStack | `application-delivery` |
| Environment variable, variable group, global variable | AppStack | `application-delivery` |
| Host deployment, VM Deploy, machine deployment | AppStack / Flow | `application-delivery` + `pipeline-management` |
| Member, user (organization), department, role, permission | - | `organization-management` |
| Current user, my, current organization | - | `base` |

## Product Mapping Decision Tree

```
Identify the target object
  │
  ├─ Involves the full CI/CD process?
  │   ├─ Only build + run pipeline → Flow
  │   ├─ Involves application lifecycle (orchestration, change orders, release workflows) → AppStack
  │   └─ Involves both → Ask user for specific requirements
  │
  ├─ Involves code operations?
  │   ├─ Repository / branch / file / commit / MR → Codeup
  │   └─ Artifact and package management → Packages
  │
  ├─ Involves project management?
  │   ├─ Requirements / sprints / work items / work hours → Projex
  │   └─ Testing related → Testhub
  │
  ├─ Involves application delivery?
  │   ├─ Application metadata (create/query/tags/templates) → AppStack
  │   ├─ Orchestration → AppStack
  │   ├─ Change orders → AppStack
  │   └─ Release workflows (Release Workflow/Stage) → AppStack
  │
  └─ Involves organization/members? → organization-management
```

## Ambiguous Keyword Handling

| Ambiguous Term | Possible Products | Must Ask |
|---------------|-------------------|----------|
| "repository" | Codeup (code repository) / Packages (artifact repository) | Which type of repository? |
| "build" | Flow (pipeline build) / AppStack (release stage) | Pipeline build or application release? |
| "deploy" | Flow (pipeline deployment) / AppStack (release workflow) | Pipeline trigger or release workflow? |
| "change" | Codeup (change request/MR) / AppStack (change order) | Code MR or application change order? |
| "version" | Projex (project version) / Packages (artifact version) / AppStack (orchestration version) | Ask for context |
| "task" | Projex (work item - task) / Flow (pipeline job) | Ask for context |
| "comment" | Codeup (MR/commit comment) / Projex (work item comment) | Ask for context |

## Cross-Product Typical Combinations

| Scenario | Products Involved |
|----------|-------------------|
| Trigger pipeline after code MR merge | Codeup + Flow |
| Pipeline run and publish to application | Flow + AppStack |
| Link requirement to code MR | Projex + Codeup |
| Link test plan to pipeline | Testhub + Flow |
| Link change order to work item | AppStack + Projex |
