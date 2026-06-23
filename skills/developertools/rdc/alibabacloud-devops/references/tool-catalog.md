# Tool Catalog

This document covers the Alibaba Cloud CLI command set and the MCP toolset separately. The two sections are independent; refer to the relevant section as needed.

---

## Alibaba Cloud CLI Command Set

### Authentication Parameters

Cloud DevOps CLI authenticates via Personal Access Token. Configure via environment variables (recommended) or command-line parameters:

- Central site: `--organization-id <ID>` + `--yunxiao-access-token <token>` (or set `ALIBABA_CLOUD_YUNXIAO_ORGANIZATION_ID` and `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` env vars)
- Regional site: `--api-base-url <url>` + `--yunxiao-access-token <token>` (or set `ALIBABA_CLOUD_YUNXIAO_API_BASE_URL` and `ALIBABA_CLOUD_YUNXIAO_ACCESS_TOKEN` env vars)

### Command Discovery

View all available commands with `aliyun devops --help`, or filter by product prefix:

```bash
aliyun devops --help 2>&1 | grep '^  flow-'       # Flow commands
aliyun devops --help 2>&1 | grep '^  codeup-'     # Codeup commands
aliyun devops --help 2>&1 | grep '^  projex-'     # Projex commands
aliyun devops --help 2>&1 | grep '^  test-hub-'   # Testhub commands
aliyun devops --help 2>&1 | grep '^  app-stack-'  # AppStack commands
aliyun devops --help 2>&1 | grep '^  packages-'   # Packages commands
aliyun devops --help 2>&1 | grep '^  base-'       # Base management commands
```

### Product Prefix Overview

| Product Group | CLI Command Prefix | Command Count |
|---------------|-------------------|---------------|
| Flow | `flow-` | 77 |
| Codeup | `codeup-` | 100 |
| Projex | `projex-` | 66 |
| Testhub | `test-hub-` | 14 |
| AppStack | `app-stack-` | 93 |
| Packages | `packages-` | 6 |
| Base management | `base-` | 15 |

### Parameter Lookup

Run the help for a specific command to view its parameter definitions:

```bash
aliyun devops <command-name> --help
```

---

## MCP Toolset (~165 tools)

This section lists all MCP tools provided by `alibabacloud-devops-mcp-server`, organized by product. For complete parameter definitions, refer to the MCP Schema:

```bash
npx -y mcporter list --stdio "npx -y alibabacloud-devops-mcp-server" --schema
```

### Base -- 3

| Tool | Description |
|------|-------------|
| `get_current_organization_info` | Get current user and organization info based on Token |
| `get_user_organizations` | Get the list of organizations the current user belongs to |
| `get_current_user` | Get current user info based on Token |

### Code Management (code-management) -- 32

#### Repositories
| Tool | Description |
|------|-------------|
| `get_repository` | Get repository details |
| `list_repositories` | List code repositories |

#### Branches
| Tool | Description |
|------|-------------|
| `list_branches` | List all branches in a repository |
| `get_branch` | Get branch information |
| `create_branch` | Create a branch |
| `delete_branch` | Delete a branch |

#### Files
| Tool | Description |
|------|-------------|
| `get_file_blobs` | Get file content |
| `create_file` | Create a file |
| `update_file` | Update a file |
| `delete_file` | Delete a file |
| `list_files` | List files in a directory |
| `compare` | Compare code (branches/commits) |

#### Change Requests (MR)
| Tool | Description |
|------|-------------|
| `create_change_request` | Create a change request |
| `get_change_request` | Get change request details |
| `list_change_requests` | List change requests |
| `list_change_request_patch_sets` | List patch sets |
| `create_change_request_comment` | Create a change request comment |
| `list_change_request_comments` | List change request comments |
| `update_change_request_comment` | Update a change request comment |

#### Commits
| Tool | Description |
|------|-------------|
| `list_commits` | List commits |
| `get_commit` | Get commit details |
| `create_commit_comment` | Create a commit comment |

### Organization Management (organization-management) -- 12

#### Departments
| Tool | Description |
|------|-------------|
| `list_organization_departments` | List departments |
| `get_organization_department_info` | Get department info |
| `get_organization_department_ancestors` | Get department ancestor chain |

#### Members
| Tool | Description |
|------|-------------|
| `list_organization_members` | List members |
| `get_organization_member_info` | Get member info |
| `get_organization_member_info_by_user_id` | Get member by user ID |
| `search_organization_members` | Search members |

#### Roles
| Tool | Description |
|------|-------------|
| `list_organization_roles` | List roles |
| `get_organization_role` | Get role details |

#### Resource Members (shared)
| Tool | Description |
|------|-------------|
| `list_resource_members` | List resource members |
| `create_resource_member` | Add a resource member |
| `update_resource_member` | Update a resource member |
| `delete_resource_member` | Delete a resource member |
| `update_resource_owner` | Transfer resource ownership |

### Project Management (project-management) -- 47

#### Projects / Programs
| Tool | Description |
|------|-------------|
| `get_project` | Get project details |
| `search_projects` | Search projects |
| `search_programs` | Search programs |
| `list_program_versions` | List program versions |

#### Versions
| Tool | Description |
|------|-------------|
| `list_versions` / `create_version` / `update_version` / `delete_version` | Version CRUD |

#### Sprints
| Tool | Description |
|------|-------------|
| `list_sprints` / `get_sprint` / `create_sprint` / `update_sprint` | Sprint CRU |

#### Work Items
| Tool | Description |
|------|-------------|
| `create_work_item` / `get_work_item` / `search_workitems` / `update_work_item` | Work item CRU + query |
| `get_work_item_types` / `list_all_work_item_types` / `list_work_item_types` / `get_work_item_type` | Work item types |
| `list_work_item_relation_work_item_types` | Related work item types |
| `get_work_item_type_field_config` / `get_work_item_workflow` | Field configuration and workflow |
| `list_work_item_comments` / `create_work_item_comment` | Comments |
| `list_workitem_attachments` / `get_workitem_file` / `create_workitem_attachment` | Attachments |

#### Effort
| Tool | Description |
|------|-------------|
| `list_current_user_effort_records` / `list_effort_records` | Query effort records |
| `create_effort_record` / `update_effort_record` | Effort CU |
| `list_estimated_efforts` / `create_estimated_effort` / `update_estimated_effort` | Estimated effort |

### Pipeline Management (pipeline-management) -- 43

#### Pipeline Basics
| Tool | Description |
|------|-------------|
| `list_pipelines` / `smart_list_pipelines` | List / smart query pipelines |
| `get_pipeline` / `update_pipeline` | Get / update |

#### Generation
| Tool | Description |
|------|-------------|
| `generate_pipeline_yaml` | Generate pipeline YAML |
| `create_pipeline_from_description` | Create pipeline from description |

#### Runs
| Tool | Description |
|------|-------------|
| `create_pipeline_run` | Run a pipeline |
| `get_latest_pipeline_run` | Get the latest run |
| `get_pipeline_run` / `list_pipeline_runs` | Get / list run records |

#### Jobs
| Tool | Description |
|------|-------------|
| `list_pipeline_jobs_by_category` | List jobs by category |
| `list_pipeline_job_historys` | Job history |
| `execute_pipeline_job_run` | Manually execute a job |
| `get_pipeline_job_run_log` | Get job log |

#### Service Connections
| Tool | Description |
|------|-------------|
| `list_service_connections` | List service connections |

#### VM Deploy
| Tool | Description |
|------|-------------|
| `get_vm_deploy_order` / `stop_vm_deploy_order` / `resume_vm_deploy_order` | Deploy order management |
| `skip_vm_deploy_machine` / `retry_vm_deploy_machine` | Machine-level operations |
| `get_vm_deploy_machine_log` | Machine log |

### Packages Management (packages-management) -- 3

| Tool | Description |
|------|-------------|
| `list_package_repositories` | List artifact repositories |
| `list_artifacts` | List artifacts |
| `get_artifact` | Get artifact details |

### Application Delivery (application-delivery) -- 48

#### Applications
| Tool | Description |
|------|-------------|
| `list_applications` / `get_application` / `create_application` / `update_application` | Application CRU |

#### Application Tags / Templates
| Tool | Description |
|------|-------------|
| `create_app_tag` / `update_app_tag` / `search_app_tags` / `update_app_tag_bind` | Tags |
| `search_app_templates` | Application templates |

#### Global Variables / Variable Groups
| Tool | Description |
|------|-------------|
| `create_global_var` / `get_global_var` / `update_global_var` / `list_global_vars` | Global variable groups |
| `get_env_variable_groups` | Environment variable groups |
| `create_variable_group` / `delete_variable_group` / `get_variable_group` / `update_variable_group` | Variable groups |
| `get_app_variable_groups` / `get_app_variable_groups_revision` | Application variable groups |

#### Orchestration
| Tool | Description |
|------|-------------|
| `get_latest_orchestration` / `list_app_orchestration` / `create_app_orchestration` | List / create |
| `delete_app_orchestration` / `get_app_orchestration` / `update_app_orchestration` | Single orchestration operations |

#### Application Change Requests
| Tool | Description |
|------|-------------|
| `create_appstack_change_request` | Create a change request |
| `get_appstack_change_request_audit_items` | Audit items |
| `list_appstack_change_request_executions` | Execution records |
| `list_appstack_change_request_work_items` | Related work items |
| `cancel_appstack_change_request` / `close_appstack_change_request` | Cancel / close |

#### Change Orders / Deployments
| Tool | Description |
|------|-------------|
| `create_change_order` / `get_change_order` / `list_change_order_versions` | Change orders (deployment units) |
| `list_change_order_job_logs` / `find_task_operation_log` | Logs |
| `execute_job_action` / `list_change_orders_by_origin` | Actions / queries |
| `get_machine_deploy_log` | Machine deploy log |
| `add_host_list_to_host_group` / `add_host_list_to_deploy_group` | Host groups / deploy groups |

#### Release Workflows
| Tool | Description |
|------|-------------|
| `list_app_release_workflows` / `list_app_release_workflow_briefs` | Query release workflows |
| `get_app_release_workflow_stage` / `list_app_release_stage_briefs` / `update_app_release_stage` | Stage management |
| `list_app_release_stage_runs` / `execute_app_release_stage` / `cancel_app_release_stage_execution` | Execution |
| `retry_app_release_stage_pipeline` / `skip_app_release_stage_pipeline` | Pipeline retry / skip |
| `list_app_release_stage_metadata` / `get_app_release_stage_pipeline_run` | Metadata / run instances |
| `pass_app_release_stage_validate` / `refuse_app_release_stage_validate` | Approval |
| `get_app_release_stage_job_log` | Job log |

### Test Management (test-management) -- 11

#### Test Cases
| Tool | Description |
|------|-------------|
| `list_testcase_directories` / `create_testcase_directory` | Directories (requires `testRepoId`) |
| `get_testcase_field_config` | Field configuration (**recommended to call before creation to confirm required field names**) |
| `create_testcase` | Create a test case (key parameters: `subject` title, `assignedTo` assignee userId, `testRepoId`, `directoryId`, `testSteps` test steps) |
| `search_testcases` / `get_testcase` / `delete_testcase` | Test case query and deletion |

#### Test Plans
| Tool | Description |
|------|-------------|
| `list_test_plans` | List test plans |
| `get_test_result_list` | Get the list of test cases in a plan |
| `update_test_result` | Update a test result |
