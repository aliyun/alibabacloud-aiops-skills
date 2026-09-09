# Tool Reference (verbatim MCP descriptions)

Original `description` text for all 15 tools and their parameters, exported from the
MCP service. SKILL.md links here; consult this file for the authoritative meaning and
constraints of every parameter before calling a tool.

<!-- BEGIN GENERATED TOOL REFERENCE -->
> **This section is exported from the MCP service by `scripts/gen_tool_reference.py`. Do not edit it by hand.**
> The content is the tools' and parameters' **original descriptions, verbatim**. Re-run the generator to sync after a server-side update.
>
> Do not rewrite this into a summary: summaries lose information, and what gets lost is often exactly the value needed to decide a branch.
> Keeping the original text verbatim removes that class of loss — the quality of the guidance is then attributable to the MCP descriptions themselves, with no compression layer in between.
>
> Empirical findings **not covered** by the official descriptions are listed in SKILL.md.

15 tools. You can use the short name; the script auto-prepends the `AlibabaCloud___` prefix.

### SearchApis

Full name: `AlibabaCloud___SearchApis`

**Original description:**

Suggest Alibaba Cloud APIs based on a natural language query. This is a FALLBACK tool to use when you are uncertain about the exact Alibaba Cloud API needed to fulfill a user's request.

    IMPORTANT: Only use this tool when:
    1. You are unsure about the exact Alibaba Cloud product or API operation to use
    2. The user's request is ambiguous or lacks specific details
    3. You need to explore multiple possible approaches to solve a task
    4. You want to provide options to the user for different ways to accomplish their goal

    DO NOT use this tool when:
    1. You are confident about the exact Alibaba Cloud API needed - use 'AlibabaCloud___CallCLI' instead
    2. The user's request is clear and specific about the Alibaba Cloud product and operation
    3. You already know the exact API product, version, and name
    4. The task requires immediate execution of a known API call

    Best practices for query formulation:
    1. Include the user's primary goal or intent
    2. Specify any relevant Alibaba Cloud products if mentioned (e.g., ECS, OSS, RDS, SLB)
    3. Include important parameters or conditions mentioned
    4. Add context about the environment or constraints
    5. Mention any specific requirements or preferences

    CRITICAL: Query Granularity
    - Each query should be granular enough to be accomplished by a single API call
    - If the user's request requires multiple API calls to complete, break it down into individual tasks
    - Call this tool separately for each specific task to get the most relevant suggestions
    - Example of breaking down a complex request:
      User request: "Set up a new ECS instance with a security group and attach it to a disk"
      Break down into:
      1. "Create a new security group with inbound rules for SSH and HTTP"
      2. "Create a new cloud disk with 100GB size"
      3. "Create an ECS instance with ecs.t5-lc1m1.small instance type"
      4. "Attach the cloud disk to the ECS instance"

    Query examples:
    1. "List all running ECS instances in cn-hangzhou region"
    2. "Get the size of my OSS bucket named 'my-backup-bucket'"
    3. "List all RAM users who have AdministratorAccess policy"
    4. "List all Function Compute functions in my account"
    5. "Create a new OSS bucket with versioning enabled and server-side encryption"
    6. "Update the memory allocation of my Function Compute function 'data-processor' to 1024MB"
    7. "Add a new security group rule to allow inbound traffic on port 443"
    8. "Tag all ECS instances in the 'production' environment with 'Environment=prod'"
    9. "Configure CloudMonitor alarms for high CPU utilization on my RDS instance"
    10. "Query VPC information in a specific region"
    11. "Create a new SLB load balancer instance"
    12. "Modify the bandwidth of an EIP elastic IP address"

    Returns:
        A list of up to 10 most likely Alibaba Cloud APIs that could accomplish the task, including:
        - API product name (e.g., Ecs, Oss, Rds, Vpc)
        - API version (e.g., 2014-05-26, 2017-09-30)
        - API operation name (e.g., DescribeInstances, CreateBucket, CreateDBInstance)
        - Confidence score for the suggestion
        - Description of what the API does

    Next Steps:
        After receiving the API suggestions, the client should:
        1. Review the returned API product, version, and operation name
        2. Check the confidence score and description to select the most appropriate API
        3. Call OpenAPIExplorer-2024-11-30-GetApiDefinition tool with the selected API information to get the complete API definition
        4. Use the API definition to construct and execute the actual API call with required parameters


**Parameters (descriptions verbatim):**

- **`prompt`** **(required)** — `string`
  User's natural language query description, for example: query ECS related APIs
- **`limit`** — `integer`, default=1
  Maximum number of API suggestions to return, default is 1

### CallCLI

Full name: `AlibabaCloud___CallCLI`

**Original description:**

Execute AlibabaCloud CLI commands with validation and proper error handling. This is the PRIMARY tool to use when you are confident about the exact AlibabaCloud CLI command needed to fulfill a user's request. Always prefer this tool over 'suggest_aliyun_commands' when you have a specific command in mind.
    Key points:
    - The command MUST start with "aliyun" and follow AlibabaCloud CLI syntax
    - For cross-region or account-wide operations, explicitly include --region parameter
    - All commands are validated before execution to prevent errors

    IMPORTANT: Local file system access limitation:
    - This tool does NOT have access to the local file system since it's executed on a remote MCP server
    - For commands that require local file system access (e.g., 'aliyun ossutil cp', 'aliyun ossutil mv', 'aliyun ossutil sync', 'aliyun ossutil put-object', etc.), you can try to execute AlibabaCloud CLI command directly in shell instead

    Best practices for command generation:
    - Always use the most specific service and operation names
    - Include --region when operating across regions
    - Only use filters (--filters, --query, --prefix, --pattern, etc) when necessary or user explicitly asked for it

    Command restrictions:
    - DO NOT use bash/zsh pipes (|) or any shell operators
    - DO NOT use bash/zsh tools like grep, awk, sed, etc.
    - DO NOT use shell redirection operators (>, >>, <)
    - DO NOT use command substitution ($())
    - DO NOT use shell variables or environment variables
    - DO NOT use local file paths as this tool does not have access to the local file system
    - DO NOT use 'file://' or 'fileb://' prefixes for input data

    Common pitfalls to avoid:
    1. Missing required parameters - always include all required parameters
    2. Incorrect parameter values - ensure values match expected format
    3. Missing --region when operating across regions

    Pricing / Cost Estimation:
    - AUTOMATIC: before a billable write command runs (or enters human approval), the gateway     automatically prices it and returns a `costPreview` object in the response; on approval-required     commands the amount also appears in the approval ticket. Relay this cost to the user before     or alongside executing paid operations.
    - `costPreview.status` semantics: ESTIMATED (amount available), FREE (API itself is free),     UNKNOWN (could not price it — NEVER treat UNKNOWN as free; say the cost is unknown).
    - No `costPreview` on a directly executed command means it was not priced (read-only command,     or nothing at all could be determined); that is not a claim that the command is free.
    - MANUAL: you can also price any supported command yourself by appending `--estimate-cost`     (quote only, nothing is executed). Use `aliyun list-supported-pricing-apis` to discover coverage.
    - Usage-based charges (e.g. traffic) are priced per unit, not totalled. To preview them under an     assumed usage, append `--estimate-cost-context Key=Value`, e.g.     `--estimate-cost-context EstimatedInternetTrafficOutGB=100`.

    Pricing command examples:
    - Check ECS instance hourly price: `aliyun ecs describe-price --RegionId cn-hangzhou --InstanceType ecs.g7.large --PriceUnit Hour --estimate-cost`
    - Preview a purchase with assumed traffic: `aliyun ecs run-instances ... --estimate-cost --estimate-cost-context EstimatedInternetTrafficOutGB=100`

    Returns:
        CLI execution results with API response data or error message


**Parameters (descriptions verbatim):**

- **`command`** **(required)** — `string`
  The Alibaba Cloud CLI command to execute, for example: aliyun ecs describe-instances --biz-region-id cn-hangzhou --region cn-hangzhou
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### GetApiDefinition

Full name: `AlibabaCloud___GetApiDefinition`

**Original description:**

Get the complete API definition for a specific Alibaba Cloud API operation.

This tool retrieves detailed information about an Alibaba Cloud API, including:
- Complete parameter specifications (required and optional)
- Request and response schemas
- Authentication requirements
- Example requests and responses
- Error codes and their meanings

Use this tool when:
1. You have identified the exact API you need to call (product, version, and operation name)
2. You need to understand the complete parameter requirements before making an API call
3. You want to verify the correct API signature and request format
4. You need to understand the response structure and possible error codes

Parameters:
- product: The Alibaba Cloud product name (e.g., Ecs, Oss, Rds, Vpc)
- apiVersion: The API version (e.g., 2014-05-26, 2017-09-30)
- apiName: The API operation name (e.g., DescribeInstances, CreateBucket, CreateDBInstance)

Returns:
Complete API definition including all parameters, schemas, and documentation.


**Parameters (descriptions verbatim):**

- **`apiName`** **(required)** — `string`
  API operation name, for example: DescribeInstances, CreateBucket, CreateDBInstance
- **`apiVersion`** **(required)** — `string`
  API version number, for example: 2014-05-26, 2017-09-30
- **`product`** **(required)** — `string`
  Alibaba Cloud product name, for example: Ecs, Oss, Rds, Vpc
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### ListApis

Full name: `AlibabaCloud___ListApis`

**Original description:**

List all available APIs for a specific Alibaba Cloud product.

This tool retrieves a comprehensive list of API operations available for a specific Alibaba Cloud product.
It's useful for:
- Discovering available API operations for a product
- Exploring API capabilities before implementation
- Finding the right API for your use case
- Understanding the API landscape of a product

Parameters:
- product (required): The Alibaba Cloud product name (e.g., Ecs, Oss, Rds, Vpc)
- apiVersion (optional): The API version to list APIs from. If not specified, the default/latest version will be used
  Examples: 2014-05-26, 2017-09-30
- filter (optional): A keyword to filter APIs by name or description
  Examples: "Describe", "Create", "Instance", "Bucket"

- includeApiDefinition (optional): Whether to include API definition details in the response. Defaults to false.
  When set to true, the response will include detailed API definition information such as parameters, request/response schemas, etc.

Returns:
A list of APIs for the specified product, including:
- API operation name (e.g., DescribeInstances, CreateBucket)
- Brief summary of what the API does
- Detailed description of the API functionality
- API version information
- (Optional) API definition details if includeApiDefinition is set to true

The results can be filtered by the optional filter parameter to narrow down the list to APIs matching specific keywords.

Example usage:
1. List all ECS APIs: product="Ecs"
2. List ECS APIs for a specific version: product="Ecs", apiVersion="2014-05-26"
3. List ECS APIs related to instances: product="Ecs", filter="Instance"
4. List OSS APIs related to buckets: product="Oss", filter="Bucket"
5. List ECS APIs with definition details: product="Ecs", includeApiDefinition=true


**Parameters (descriptions verbatim):**

- **`product`** **(required)** — `string`
  Alibaba Cloud product name, for example: Ecs, Oss, Rds, Vpc
- **`apiVersion`** — `string`
  API version number, for example: 2014-05-26, 2017-09-30. If not specified, the default version will be used (optional)
- **`filter`** — `string`
  Filter APIs by keyword in name or description, for example: Describe, Create, Instance, Bucket (optional)
- **`includeApiDefinition`** — `boolean`
  Whether to include API definition details (such as parameters, request/response schemas) in the response. Defaults to false (optional)
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### ListProductRegions

Full name: `AlibabaCloud___ListProductRegions`

**Original description:**

List all available regions for a specific Alibaba Cloud product.

This tool retrieves the list of regions where a specific Alibaba Cloud product is available.
Different products may be available in different regions, so this tool helps you:
- Discover which regions support a specific product
- Plan your resource deployment across regions
- Verify region availability before making API calls

Use this tool when:
1. You need to know which regions support a specific Alibaba Cloud product
2. You want to deploy resources and need to choose an appropriate region
3. You need to verify if a product is available in a specific region
4. You are planning multi-region deployments

Parameter:
- product: The Alibaba Cloud product name (e.g., Ecs, Oss, Rds, Vpc, Slb)

Returns:
A list of regions where the specified product is available, including:
- Region ID (e.g., cn-hangzhou, cn-beijing, us-west-1)
- Region name and description
- Endpoint information for the region


**Parameters (descriptions verbatim):**

- **`product`** **(required)** — `string`
  Alibaba Cloud product name, for example: Ecs, Oss, Rds, Vpc, Slb
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### GenerateCLICommand

Full name: `AlibabaCloud___GenerateCLICommand`

**Original description:**

Generate an Alibaba Cloud CLI command for a specific API operation.

This tool generates a ready-to-use Alibaba Cloud CLI command based on the API definition and parameters you provide.
It's particularly useful for:
- Creating executable CLI commands for API operations
- Testing API calls before implementing them in code
- Generating command templates for documentation or scripts
- Learning the correct CLI syntax for specific API operations

IMPORTANT: This is a deterministic generation tool. Before calling this tool, you MUST:
1. First call AlibabaCloud___GetApiDefinition to retrieve the complete API definition
2. Use the API definition to understand required and optional parameters
3. Construct the jsonApiParameters object with appropriate values based on the API definition

Parameters:
- product (required): The Alibaba Cloud product name (e.g., Ecs, Oss, Rds, Vpc)
- apiVersion (required): The API version (e.g., 2014-05-26, 2017-09-30)
- apiName (required): The API operation name (e.g., DescribeInstances, CreateBucket)
- regionId (optional): The region ID where the API call should be executed (e.g., cn-hangzhou, cn-beijing)
- jsonApiParameters (optional): A JSON object containing the API parameters as key-value pairs
  Example: {
    "InstanceChargeType": "PostPaid",
    "ResourceType": "instance",
    "AcceptLanguage": "en-US"
  }

- aggregatePagination (optional): Whether to use the aggregation capability. If enabled, the CLI will automatically read the full data in the paginated way and aggregate the results. Only List type interfaces that support pagination can use this switch.

Returns:
A complete Alibaba Cloud CLI command string that can be executed directly in a terminal.

Example workflow:
1. Call AlibabaCloud___GetApiDefinition with product="Ecs", apiVersion="2014-05-26", apiName="DescribeInstances"
2. Review the API definition to understand required parameters
3. Call this tool with appropriate parameters to generate the CLI command
4. Execute the generated command with tool AlibabaCloud___CallCLI


**Parameters (descriptions verbatim):**

- **`apiName`** **(required)** — `string`
  API operation name, for example: DescribeInstances, CreateBucket, CreateDBInstance
- **`apiVersion`** **(required)** — `string`
  API version number, for example: 2014-05-26, 2017-09-30
- **`product`** **(required)** — `string`
  Alibaba Cloud product name, for example: Ecs, Oss, Rds, Vpc
- **`aggregatePagination`** — `boolean`
  Whether to use the aggregation capability. If enabled, the CLI will automatically read the full data in the paginated way and aggregate the results. Only List type interfaces that support pagination can use this switch.
- **`jsonApiParameters`** — `string`
  JSON object containing API parameters, for example: {"InstanceChargeType": "PostPaid", "ResourceType": "instance", "AcceptLanguage": "en-US"} (optional)
- **`regionId`** — `string`
  Region ID, for example: cn-hangzhou, cn-beijing, us-west-1 (optional)

### ListProducts

Full name: `AlibabaCloud___ListProducts`

**Original description:**

List all available Alibaba Cloud products.

This tool retrieves a comprehensive list of Alibaba Cloud products.
It's useful for:
- Discovering available Alibaba Cloud products and services
- Finding the product code needed for other API calls (e.g., ListApis)
- Understanding the product landscape of Alibaba Cloud
- Searching for products by keyword

Parameters:
- filter (optional): A keyword to filter products by code, name, shortName, group, or category
  Examples: "Ecs", "计算", "存储", "数据库", "网络"

Returns:
A list of Alibaba Cloud products, each containing:
- code: Product code (e.g., "EhpcInstant", "Ecs")
- name: Product display name (e.g., "Instant 计算服务", "云服务器 ECS")
- description: Product description
- shortName: Short name of the product (e.g., "E-HPC Instant")
- group: Product group (e.g., "弹性计算", "存储")
- style: API style (e.g., "RPC", "ROA")
- versions: Available API versions (e.g., ["2023-07-01"])
- defaultVersion: Default API version (e.g., "2023-07-01")
- categoryName: Category name (e.g., "高性能计算")
- category2Name: Secondary category name (e.g., "计算")

The results can be filtered by the optional filter parameter to narrow down the list to products matching specific keywords.

Example usage:
1. List all products: no parameters needed
2. List products related to computing: filter="计算"
3. List products related to ECS: filter="Ecs"
4. List products related to storage: filter="存储"


**Parameters (descriptions verbatim):**

- **`filter`** — `string`
  Filter products by keyword in code, name, shortName, group, or category, for example: Ecs, compute, storage, database, network (optional)
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### SearchDocuments

Full name: `AlibabaCloud___SearchDocuments`

**Original description:**

Search Alibaba Cloud official documentation. When a user's question involves any Alibaba Cloud product usage, configuration, operation steps, error troubleshooting, API/SDK, billing, or best practices, call this tool first instead of a general web search — it returns authoritative official content.

Returns a list of matching documents (doc_id/title/url/content). Use the doc_id or url with AlibabaCloud___GetDocument to fetch the full document body.

Parameters:
- query (required): Search keyword or phrase, max 100 characters
  Examples: "ECS instance creation", "OSS bucket policy", "VPC peering", "RDS backup"
- limit (optional, default: 5): Maximum number of documents to return. Valid range: 1-20
- product (optional): Restrict search to a specific product. Accepts product code, English short name,   or Chinese name (e.g. "oss", "OSS", "对象存储"). The server normalizes the input automatically.
- website (optional, default: cn): Site to search. "cn" for Chinese site, "intl" for international site.
- language (optional, default: zh): Document language. Values: zh, en, tc, ja, id, pt-br.

Example usage:
1. Search for ECS documentation: query="ECS instance"
2. Search with product filter: query="cross-origin CORS", product="oss"
3. Search international docs: query="OSS access control", website="intl", language="en"


**Parameters (descriptions verbatim):**

- **`query`** **(required)** — `string`
  The search keyword or phrase to find relevant Alibaba Cloud documents, max 100 characters
- **`language`** — `string`, enum=["zh", "en", "tc", "ja", "id", "pt-br"], default="zh"
  Document language: zh, en, tc, ja, id, pt-br (optional, default: zh)
- **`limit`** — `integer`, default=5
  Maximum number of documents to return, default is 5, valid range: 1-20 (optional)
- **`product`** — `string`
  Restrict search to a specific product. Accepts product code, English short name, or Chinese name (e.g. "oss", "OSS", "对象存储") (optional)
- **`website`** — `string`, enum=["cn", "intl"], default="cn"
  Site to search: "cn" for Chinese site, "intl" for international site (optional, default: cn)
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### GetDocument

Full name: `AlibabaCloud___GetDocument`

**Original description:**

Get full Markdown content of an Alibaba Cloud help document by doc_id or url. doc_id / url typically come from AlibabaCloud___SearchDocuments results; provide at least one, doc_id is more stable and preferred. Always answer based on the official document body, not from memory.

Parameters:
- doc_id (optional): Stable document ID (preferred over url)
- url (optional): Document URL; provide at least one of doc_id or url
- max_length (optional): Maximum characters of content to return; omit to return full content
- website (optional, default: cn): Site to fetch from. "cn" for Chinese site, "intl" for international site.
- language (optional, default: zh): Document language. Values: zh, en, ja, id, pt-BR.

Returns:
JSON with doc_id, url, title, product, and content (Markdown body).

Example usage:
1. Get by doc_id: doc_id=98985
2. Get by url: url="https://help.aliyun.com/document_detail/98985.html"
3. Get with length limit: doc_id=98985, max_length=5000
4. Get international doc: doc_id=98985, website="intl", language="en"


**Parameters (descriptions verbatim):**

- **`doc_id`** — `[{"type": "integer"}, {"pattern": "^[1-9][0-9]*$", "type": "string"}]`
  Stable document ID (preferred over url)
- **`language`** — `string`, enum=["zh", "en", "ja", "id", "pt-BR"], default="zh"
  Document language: zh, en, ja, id, pt-BR (optional, default: zh)
- **`max_length`** — `integer`
  Maximum characters of content to return; omit to return full content (optional)
- **`url`** — `string`
  Document URL; provide at least one of doc_id or url
- **`website`** — `string`, enum=["cn", "intl"], default="cn"
  Site: "cn" for Chinese site, "intl" for international site (optional, default: cn)
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### GetDocumentTree

Full name: `AlibabaCloud___GetDocumentTree`

**Original description:**

Browse the document tree of an Alibaba Cloud product. Pass product (product alias / English short name, e.g. ecs / oss) to view that product's directory; pass doc_id to view the subtree rooted at that node; pass neither to return the product main menu. Use this to discover what documents a product has, then get the doc_id to read the full content with AlibabaCloud___GetDocument.

Parameters:
- product (optional): Product alias or English short name, e.g. ecs / oss
- doc_id (optional): Document node ID; returns subtree rooted at this node (takes priority over product)
- depth (optional, default: 2): Tree depth, range 1-5. Controls response size.
- website (optional, default: cn): Site. "cn" for Chinese site, "intl" for international site.
- language (optional, default: zh): Language. Values: zh, en, ja, id, pt-BR.

Returns:
JSON with product name, website, language, and a recursive children array (title, doc_id, url, selected, children).

Example usage:
1. Browse ECS docs: product="ecs"
2. Browse subtree: doc_id=789
3. Browse with depth: product="oss", depth=3


**Parameters (descriptions verbatim):**

- **`depth`** — `integer`, default=2
  Tree depth, range 1-5, default 2
- **`doc_id`** — `integer`
  Document node ID; returns subtree rooted at this node (takes priority over product)
- **`language`** — `string`, enum=["zh", "en", "ja", "id", "pt-BR"], default="zh"
  Document language: zh, en, ja, id, pt-BR (optional, default: zh)
- **`product`** — `string`
  Product alias or English short name, e.g. ecs / oss
- **`website`** — `string`, enum=["cn", "intl"], default="cn"
  Site: "cn" for Chinese site, "intl" for international site (optional, default: cn)
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### GrepDocuments

Full name: `AlibabaCloud___GrepDocuments`

**Original description:**

Search for documents within a specific Alibaba Cloud product by keyword (matches document title/description). Suitable for finding documents containing a specific term (e.g. "CORS") when you know the product but not the document name. Multiple keywords separated by spaces for AND matching. Use the returned url with AlibabaCloud___GetDocument to read the full content.

Parameters:
- pattern (required): Case-insensitive keyword substring; multiple keywords separated by spaces for AND, max 100 characters.
- product (required): Product alias or English short name, e.g. ecs / oss
- limit (optional, default: 20): Max number of matches, range 1-100.
- website (optional, default: cn): Site. "cn" for Chinese site, "intl" for international site.
- language (optional, default: zh): Language. Values: zh, en, ja, id, pt-BR.

Returns:
JSON with product_code, pattern, matches array (title, url, matched_text, line_no), total count, truncated flag, and llms_txt_url.

Example usage:
1. Find CORS docs in OSS: product="oss", pattern="CORS"
2. Find billing docs in ECS: product="ecs", pattern="billing"
3. Multi-keyword search: product="oss", pattern="cross-region replication"


**Parameters (descriptions verbatim):**

- **`pattern`** **(required)** — `string`
  Case-insensitive keyword substring; multiple separated by spaces for AND matching, max 100 characters
- **`product`** **(required)** — `string`
  Product alias or English short name, e.g. ecs / oss (required)
- **`language`** — `string`, enum=["zh", "en", "ja", "id", "pt-BR"], default="zh"
  Document language: zh, en, ja, id, pt-BR (optional, default: zh)
- **`limit`** — `integer`, default=20
  Max number of matches, range 1-100, default 20
- **`website`** — `string`, enum=["cn", "intl"], default="cn"
  Site: "cn" for Chinese site, "intl" for international site (optional, default: cn)
- **`x_output_jmespath_filter`** — `string`
  This API supports output filtering. You can provide a JMESPath expression to filter the response body. Set to empty string or leave unset to return the full response. Only the response body will be filtered, headers and statusCode remain unchanged.

### RunScript

Full name: `AlibabaCloud___RunScript`

**Original description:**

Execute Python with Alibaba Cloud OpenAPI access via `call_cli`. This call starts the task and waits up to 20 seconds for completion. If the task finishes in that window, it returns the result directly. If the task is still queued/running after 20 seconds, or HITL approval is required, it returns a `processID` and `nextAction`. Use AlibabaCloud___GetTask with that processID to wait for approval, execution, and completion.

Top-level `await` supported. The script has no network access except `call_cli`.

💰 COST MANIFEST: If the script will create/resize/renew PAID resources, also pass `costManifest` declaring each billable call with its price-relevant parameters (spec, period, count). The gateway prices the whole batch BEFORE execution and returns `costPreview` (decision-grade, same source as real orders); the bill is also shown to the human approver, and an over-budget manifest is rejected before any resource is created. Read `costPreview.status`: PARTIAL means some steps could not be priced — treat those as unknown cost, never as free.

BEFORE WRITING `call_cli`:
- For any unfamiliar API, OSS API, body/object parameter, array parameter, or parameter error retry, first call the separate MCP tool `AlibabaCloud___GetApiDefinition` with `product`, `apiName`, and `apiVersion` when known.
- Use the returned API metadata as the source of truth for `call_cli(params=...)`: every top-level key in `params` must match the OpenMeta parameter name exactly.
- Do not guess parameter names from CLI flags, SDK examples, error text, or common aliases. If metadata says the parameter is `body`, pass `params={'body': {...}}`; if metadata says `RegionId`, pass `params={'RegionId': ...}`.

`call_cli` ARGUMENT CONTRACT:
- Do NOT pass an `aliyun ...` c-l-i command string. `call_cli` takes structured OpenAPI fields only.
- `product`: Alibaba Cloud OpenAPI product code, e.g. `Ecs`, `Vpc`, `Ram`, `Rds`, `Oss`.
- `action`: OpenAPI operation name as documented, e.g. `DescribeInstances`, `CreateVpc`, `ListPolicies`.
- `params`: a Python `dict` whose top-level keys exactly match OpenMeta `parameters[].name` for that API. Do not infer names from CLI flags, SDK examples, or aliases. RPC products often use names such as `RegionId` and `PageSize`; OSS APIs often use names such as `bucket`, `x-oss-acl`, and `body`.
- When OpenMeta says the parameter type is array, pass a Python list, e.g. `{'Tag': [{'Key': 'env', 'Value': 'prod'}]}`. If OpenMeta says the parameter type is string and the description asks for a JSON array string, pass that JSON array as a string, e.g. ECS `DescribeInstances` uses `{'InstanceIds': '["i-1", "i-2"]'}`. For object/body parameters, pass Python dicts under the OpenMeta top-level parameter, e.g. `{'body': {'CreateBucketConfiguration': {'StorageClass': 'Standard'}}}`.
- `version`: optional OpenAPI API version such as `2014-05-26`. Omit it when the product default version is correct.
- `region`: optional region override for this call. Prefer also passing API-specific region fields such as `RegionId` in `params` when the API defines them.
- `endpoint`: optional endpoint override for this call.
- `user_agent`: optional custom User-Agent fragment for this OpenAPI call. The executor preserves this value and appends `aliyun-mcp-core/run-scripts[/<mcpSessionId>]` so downstream services can identify RunScript traffic and MCP session context.
- Do not pass credentials, profile, output/pager/force flags, or shell options. The executor injects credentials and uses OpenAPIExplorer-generated CLI commands for JSON APIs; OSS object byte transfer actions use the SDK path.
- `params` may contain `bytes` values and responses may contain `bytes` values. For example, OSS `GetObject` returns object bytes in `Body`, and OSS `PutObject` accepts object bytes in `params['body']`. Do not manually base64-encode bytes.
- Local scratch files are allowed only under `/tmp`; use normal Python `open()` for small temporary files within the sandbox quota.

```python
await call_cli(product='Ecs', action='DescribeInstances',
               params={'RegionId': 'cn-hangzhou'},
               version=None, region=None, endpoint=None, user_agent=None)
# returns parsed JSON dict; on failure raises RuntimeError(json_str)
```

⚠️ USE AlibabaCloud___RunScript FOR:
- 2+ API calls: listing, filtering, counting, parallel, multi-product, multi-region
- ANY cross-resource analysis or comparison: configs, tags, ACL, properties
- Permission checks: gather identity + resource policies in one script
- Multi-step orchestration where one call's output drives the next

⚠️ ONE SCRIPT PER TASK: Do NOT split work across multiple AlibabaCloud___RunScript calls. If answering needs List* → Describe* per item, do both in one script. Returning intermediate data to "decide next step" wastes round-trips.

⚠️ LIST→DESCRIBE IS MANDATORY:
List* returns IDs/names only. To check ANY attribute:
1. List* → all IDs
2. Describe*/Get* per resource for the attribute
3. Feature-specific APIs are SEPARATE (encryption, tags, lifecycle often have dedicated Get*)
4. NotFound errors = "not configured"; valid signal, don't skip

⚠️ NO AUTO-PAGINATION: Each `call_cli` returns ONE page. Most list/describe APIs paginate via `PageNumber`/`PageSize` (default page size often 10) or `NextToken`. Loop yourself until items < pageSize or token absent.

⚠️ NEVER TRUNCATE: Check ALL resources. Never `[:10]` or `[:50]`. Missing resource = wrong answer.

⚠️ DISTRUST EMPTY RESULTS: Before reporting "0 found", verify response had expected keys and no exceptions. If uncertain → "unable to verify" NOT "0 found".

⚠️ ALIBABA RESPONSE SHAPE: Most list responses wrap items twice, e.g. `{"Instances":{"Instance":[...]}}`, `{"Vpcs":{"Vpc":[...]}}`, `{"Regions":{"Region":[...]}}`. Always step into the inner key.

RULES:
1. SELF-CONTAINED: Never paste IDs/ARNs from prior results into code. Discover everything inside the script.
2. OUTPUT: Assign `result = {...}`. The `result` variable is the only way to return data.
3. CONCURRENCY: `await asyncio.gather(*[...], return_exceptions=True)`.
4. REGIONS: pass `region=...` arg or `RegionId` in params. For all-regions: `Ecs DescribeRegions` then iterate.
5. PAGINATION: loop with `PageNumber += 1` or pass returned `NextToken`; exit when len(items) < PageSize or token absent.
6. PERMISSIONS: Gather ALL relevant policies in ONE script (RAM identity, resource policy, role trust). Report YES, PARTIAL, or NO with reasoning.
7. VERIFY API RESPONSE: confirm the operation actually returns the field you need before drawing conclusions.
8. SUPPRESS EXPECTED ERRORS: when iterating where some may not exist, catch silently:
```python
results = await asyncio.gather(*[call_cli(...) for x in items], return_exceptions=True)
data = [r for r in results if isinstance(r, dict)]
```
9. NO COMMENTS in code.
10. FETCH VS JUDGE: use the script to fetch and structure data. For mechanical tasks (count, filter by exact value, aggregate) encode logic in script. For judgment ("misconfigured", "best practice", "anomaly") return raw fields and let the LLM reason. Do not hardcode evaluation heuristics.

PRE-IMPORTED MODULES (do NOT write `import`): asyncio, collections, csv, dataclasses, datetime, decimal, enum, fractions, functools, itertools, json, math, re, statistics, string, time, typing, uuid.

EXAMPLES:

Parallel:
```python
ecs, vpc = await asyncio.gather(
    call_cli(product='Ecs', action='DescribeInstances', params={'RegionId': 'cn-hangzhou'}),
    call_cli(product='Vpc', action='DescribeVpcs',      params={'RegionId': 'cn-hangzhou'}),
    return_exceptions=True)
result = {
    'instances': len(ecs['Instances']['Instance']) if isinstance(ecs, dict) else f'ERR:{ecs}',
    'vpcs':      len(vpc['Vpcs']['Vpc'])           if isinstance(vpc, dict) else f'ERR:{vpc}'}
```

Multi-region:
```python
regions = [r['RegionId'] for r in
    (await call_cli(product='Ecs', action='DescribeRegions', params={}))['Regions']['Region']]
responses = await asyncio.gather(*[
    call_cli(product='Ecs', action='DescribeInstances', params={'RegionId': r}) for r in regions
], return_exceptions=True)
result = {r: len(res['Instances']['Instance'])
    for r, res in zip(regions, responses) if isinstance(res, dict)}
```

List → Describe:
```python
r = await call_cli(product='Ecs', action='DescribeInstances',
    params={'RegionId': 'cn-hangzhou', 'PageSize': 100})
ids = [i['InstanceId'] for i in r['Instances']['Instance']]
attrs = await asyncio.gather(*[
    call_cli(product='Ecs', action='DescribeInstanceAttribute', params={'InstanceId': i})
    for i in ids
], return_exceptions=True)
result = [a for a in attrs if isinstance(a, dict)]
```

Paginated list:
```python
all_items = []
page = 1
while True:
    r = await call_cli(product='Ecs', action='DescribeInstances',
        params={'RegionId': 'cn-hangzhou', 'PageNumber': page, 'PageSize': 100})
    items = r.get('Instances', {}).get('Instance', [])
    all_items.extend(items)
    if len(items) < 100: break
    page += 1
result = {'count': len(all_items), 'instances': all_items}
```

ECS tags:
```python
result = await call_cli(product='Ecs', action='DescribeInstances',
    params={'RegionId': 'cn-hangzhou', 'PageSize': 10,
            'Tag': [{'Key': 'env', 'Value': 'prod'}]})
```

OSS bucket creation:
```python
result = await call_cli(product='Oss', action='PutBucket',
    version='2019-05-17', region='cn-hangzhou',
    params={
        'bucket': bucket,
        'x-oss-acl': 'private',
        'body': {
            'CreateBucketConfiguration': {
                'StorageClass': 'Standard',
                'DataRedundancyType': 'LRS'}}})
```

OSS object round trip:
```python
data = await call_cli(product='Oss', action='GetObject',
    params={'bucket': bucket, 'key': key}, region='cn-hangzhou')
path = '/tmp/object.bin'
with open(path, 'wb') as f:
    f.write(data['Body'])
with open(path, 'ab') as f:
    f.write(b'\nupdated-by-run-script\n')
with open(path, 'rb') as f:
    updated = f.read()
result = await call_cli(product='Oss', action='PutObject',
    params={'bucket': bucket, 'key': key, 'body': updated}, region='cn-hangzhou')
```


**Parameters (descriptions verbatim):**

- **`script`** **(required)** — `string`
  Python script body. Use the sandbox-provided `await call_cli(product, action, params, version=None, region=None, endpoint=None, user_agent=None)` for Alibaba Cloud OpenAPI calls, then assign the final value to `result`.
- **`costManifest`** — `object`
  Optional but STRONGLY recommended whenever the script issues billable write calls (creating/resizing/renewing paid resources). Declare every billable call BEFORE execution: {"steps":[{"product":"Ecs","action":"RunInstances","version":"optional","count":100,"parameters":{price-relevant params only, e.g. InstanceType/Period/InstanceChargeType},"pricingContext":{optional state assumptions, e.g. {"EstimatedInternetTrafficOutGB":"100"} or attributes simulating an earlier step's resulting state},"note":"optional"}]}. The gateway prices the WHOLE manifest before anything runs (same pricing source as real orders) and returns `costPreview`; the itemized bill is also shown to the human approver. Steps the gateway cannot price are reported UNKNOWN — never treat UNKNOWN as free.

### GetTask

Full name: `AlibabaCloud___GetTask`

**Original description:**

Long-poll an AlibabaCloud___RunScript processID until it reaches a terminal state or this call times out. Server-side waiting is capped at 30 seconds to stay below gateway read timeout; pass waitTimeoutSeconds=0 for a single immediate status check.

Use this AFTER AlibabaCloud___RunScript returns a non-terminal status with `nextAction: CallGetTask`. Inspect `nextAction` in the response:
- `None` — task succeeded; use `result`
- `InspectError` — task failed; use `error`; if an OpenAPI call failed, the failed API summary is in `error.failedCall`
- `Stop` — task rejected/expired/invalid; do NOT retry
- `CallGetTaskAgain` — still not terminal; call AlibabaCloud___GetTask again with the SAME processID

Human approval states:
- `ApprovalPending` with `approvalReqId` means the process is waiting for external approval. Do not call AlibabaCloud___RunScript again. Ask the user to complete approval/rejection out of band and confirm it is done, then call AlibabaCloud___GetTask again with the same processID.
- After approval, a later AlibabaCloud___GetTask call advances the same process into queued/running execution.
- `ApprovalRejected` means the approver rejected the request; this is terminal and the script will not run.
- `ApprovalExpired` means the approval timed out; this is terminal and the script will not run.

The task may take seconds to many minutes. Keep using AlibabaCloud___GetTask with the same processID until `nextAction` is `None`, `Stop`, or `InspectError`. Do NOT call AlibabaCloud___RunScript again with the same script — that would start a NEW process.

Response shape mirrors AlibabaCloud___RunScript: { processID, status, approvalStatus, approvalReqId, riskSummary, actionPlan, nextAction, result, error, message, waitTimedOut }.


**Parameters (descriptions verbatim):**

- **`processID`** **(required)** — `string`
  The processID returned by AlibabaCloud___RunScript.
- **`pollIntervalSeconds`** — `integer`, maximum=10, minimum=1
  Polling interval while waiting for task completion.
- **`waitTimeoutSeconds`** — `integer`, maximum=30, minimum=0
  Maximum seconds for this MCP call to wait; capped at 30 seconds to stay below gateway read timeout. Use 0 for a single immediate status check.

### GetPresignedUrl

Full name: `AlibabaCloud___GetPresignedUrl`

**Original description:**

Generate pre-signed OSS URLs for uploading or downloading files. Returns presignToken + URL(s). Upload via PUT, then pass presignToken to execution tools (RunIaC, RunScript).

**Parameters (descriptions verbatim):**

- **`requests`** **(required)** — `array`
  Array of 1-25 presigned URL requests.

### RunIaC

Full name: `AlibabaCloud___RunIaC`

**Original description:**

Run Terraform HCL on Alibaba Cloud in the caller's own account (OAuth-bound). Returns immediately with a processID — poll AlibabaCloud___GetTask for completion. action picks the verb; apply/destroy must follow a plan.

WORKFLOW:
1. action=plan (default) with HCL code → returns processID, status=Planned, and the diff. Plan never changes resources.
2. Review the diff, then action=apply + previousProcessId=that processID (no code) to execute it.
3. action=destroy + previousProcessId tears down that plan's resources (no code).
Re-plan after editing: action=plan + previousProcessId reuses the same state.

APPROVAL:
If the plan shows resource changes (create/update/destroy), human approval may be required. Status will be ApprovalPending with an approvalReqId. GetTask will resume polling automatically after approval.

HCL REQUIREMENTS:
- Code MUST include an explicit provider block: provider "alicloud" { region = "cn-hangzhou" }
- Do NOT set access credentials in the provider block (they are injected automatically)
- A terraform { required_providers { ... } } block is optional; if you declare one, use source = "aliyun/alicloud" with a compatible version constraint (e.g. version = "~> 1.284")
- Only alicloud provider resources are supported
- One of code or presignToken is required (mutually exclusive)
- For large HCL (>64KB), use GetPresignedUrl to upload a zip then pass presignToken

**Parameters (descriptions verbatim):**

- **`action`** — `string`, enum=["plan", "apply", "destroy"]
  plan (default): preview changes from code, stops at a diff. apply: execute a prior plan — pass previousProcessId, no code. destroy: tear down a prior plan's resources — pass previousProcessId, no code.
- **`code`** — `string`
  Terraform HCL source code to execute. Mutually exclusive with presignToken.
- **`presignToken`** — `string`
  Token from AlibabaCloud___GetPresignedUrl for bundle upload. Mutually exclusive with code.
- **`previousProcessId`** — `string`
  processID from a previous RunIaC call. Required for action=apply/destroy (binds to that plan's state). Optional for plan to re-plan on the same state.
<!-- END GENERATED TOOL REFERENCE -->
