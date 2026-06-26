# Product Reference Index

After identifying the target product, you **must** read the corresponding Yunxiao official documentation to understand concepts, constraints, and best practices. This document provides official documentation links, key concepts, and common constraint notes organized by product.

## Official Documentation Entry Points

| Product | Overview URL | Core Content |
|---------|-------------|--------------|
| Flow | https://help.aliyun.com/zh/yunxiao/user-guide/what-is-the-pipeline | Pipeline overview, use cases, advantages |
| Codeup | https://help.aliyun.com/zh/yunxiao/user-guide/what-is-code-management | Code hosting, features |
| Packages | https://help.aliyun.com/zh/yunxiao/user-guide/what-is-a-product-repository | Artifact repository features and use cases |
| Projex | https://help.aliyun.com/zh/yunxiao/user-guide/what-is-project-collaboration-1 | Project collaboration overview and features |
| Testhub | https://help.aliyun.com/zh/yunxiao/user-guide/what-is-test-management | Test management overview |

- Yunxiao product documentation portal: https://help.aliyun.com/product/150040.html
- Yunxiao OpenAPI: https://help.aliyun.com/zh/yunxiao/developer-reference/

> **Retrieving more documentation**: You can use web search or the AI agent's `fetch_content` capability to fetch the content of the URLs above directly; you can also have the user prepare a mirrored copy of the documentation and read it via filesystem tools. This Skill does not assume that any specific local documentation directory exists in the user's environment.

## Key Information Extraction Workflow

Each time you enter a product scenario, extract information in the following order:

1. Read the corresponding overview documentation from the table above
2. Understand the product's core concepts and terminology (e.g., Flow: "Stage/Step/Trigger"; Projex: "Work Item Type/Workflow/Field")
3. Confirm operation prerequisites (permissions, dependent resources, prerequisite resources)
4. Understand parameter constraints and best practices (ID formats, field enumerations, rate limiting, throttling)

## Quick Reference for Core Concepts by Product

### Flow
- **Pipeline**: An orchestrated CI/CD workflow composed of Stages and Jobs
- **Stage**: A serial execution unit, commonly "Build/Test/Deploy"
- **Job**: A parallel execution unit within a Stage
- **Trigger**: Code push, scheduled, manual, change request, etc.
- **Pipeline run** (PipelineRun): The execution record for each pipeline run
- **Service connection** (ServiceConnection): Credentials for the pipeline to access external systems

### Codeup
- **Repository**: A Git repository, located by `id` or `organizationId + name`
- **Branch**: Located by branch name; creation requires specifying a source branch
- **Change Request (MR)**: Codeup uses "change request" in its API naming; this is equivalent to a Merge Request (MR) in Git terminology. Located by `localId` (repository-scoped number) or global `id`
- **Patch Set**: A version snapshot of an MR
- **Comment**: Supports `GLOBAL_COMMENT` and `INLINE_COMMENT`

### Packages
- **Repository**: Categorized by format (Maven, NPM, Docker, etc.)
- **Artifact**: A specific version, containing metadata such as `groupId`, `artifactId`, `version`

### Projex
- **Project**: Located by `identifier`; also supports `projectId`
- **Work Item**: Requirements, tasks, defects, etc.; `workitemTypeId` distinguishes the type
- **Sprint**: A timebox with `startDate` and `endDate`
- **Version**: Aggregates work items by milestone
- **Effort**: Associates work items with members, including estimated and actual effort. Note: "effort" in the API corresponds to "work hours" in the UI.

### Testhub
- **TestcaseDirectory**: A tree structure for organizing test cases
- **Testcase**: Contains steps, expected results, and priority
- **TestPlan**: An execution dimension that aggregates selected test cases
- **TestResult**: The status of each test case within a plan execution

### AppStack
- **Application**: An application-centric delivery object
- **Orchestration**: The environment topology and deployment method for an application
- **Change Order**: A deployment unit targeting an environment
- **Release Workflow**: A complete workflow for promoting across multiple environments
- **Release Stage**: A promotion unit within a single environment

## Common Constraints

| Item | Constraint |
|------|-----------|
| organizationId | Required by all tools; obtain via `get_current_organization_info` |
| Pagination | Most `list_*` endpoints support `page` / `perPage`; paginate when exceeding 100 results |
| Naming | Pipeline/application/branch names only support letters, digits, hyphens, and underscores; refer to specific product limitations |
| Time format | Date: `YYYY-MM-DD`; Timestamp: UTC ISO 8601 |
| Deletion is irreversible | Branches, work items, and sprints cannot be recovered once deleted; always confirm before execution |
