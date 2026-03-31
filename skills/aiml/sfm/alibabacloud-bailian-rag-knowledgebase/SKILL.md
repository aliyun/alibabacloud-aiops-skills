---
name: alibabacloud-bailian-rag-knowledgebase
description: "Alibaba Cloud Bailian Knowledge Base Retrieval Tool. Use Alibaba Cloud Bailian SDK to query and retrieve knowledge base content. Use when: User needs to query knowledge base, retrieve document content, or answer questions based on knowledge base. Prerequisites: (1) Install npm packages (2) Configure Alibaba Cloud credentials (via Alibaba Cloud CLI or environment variables). (3) Need to activate Bailian service."
---

# Bailian Knowledge Base Retrieval

This Skill provides query and retrieval capabilities for Alibaba Cloud Bailian Knowledge Base, supporting intelligent selection across multiple knowledge bases.

## 🚀 Initial Setup (Required for First-time Use)

### 1. Install Dependencies

```bash
npm install
```

This will install all dependencies defined in package.json:
- `@alicloud/bailian20231229` - Bailian Knowledge Base SDK
- `@alicloud/modelstudio20260210` - Modelstudio Workspace SDK
- `@alicloud/openapi-client` - OpenAPI Client

### 2. Configure Alibaba Cloud Credentials

This tool uses the Alibaba Cloud default credential chain, supporting multiple credential configuration methods (in order of priority):

**Method 1: Alibaba Cloud CLI (Recommended)**
```bash
# Configure credentials using Alibaba Cloud CLI
aliyun configure
```

**Method 2: Configuration File**
Alibaba Cloud SDK will automatically read credential configuration from `~/.aliyun/config.json` or `~/.acs/credentials`.

**Note:** 
- For first-time use, if credentials are not detected, guide users to configure using `aliyun configure`
- Do not explicitly handle user's AK/SK credentials, rely on Alibaba Cloud default credential chain

### 3. Important Prerequisite: Activate Bailian and Knowledge Base Service

**Before using this skill, you must first activate the knowledge base service in the Alibaba Cloud Bailian console!**

1. Visit [Bailian Knowledge Base page](https://bailian.console.aliyun.com/cn-beijing/?tab=app#/knowledge-base)
2. Click the **"Activate Now"** button
3. Confirm activation and wait for the service to take effect (usually 1-2 minutes)

### 4. Important Prerequisite: Guide Users to Grant Permissions in Alibaba Cloud Access Control and Bailian

**Before using this skill, you must grant the following permissions to the previously configured AK, otherwise calls will fail and may cause 403 errors**

#### 1) RAM Permission Grant
1. Visit [Alibaba Cloud RAM Access Control](https://ram.console.aliyun.com/users)
2. Select the RAM user corresponding to the AK, click the "Add Permission" button, select **AliyunBailianFullAccess** and **AliyunModelStudioReadOnlyAccess** permission in the permission policy, and confirm to add the permission.
#### 2) Bailian Workspace Permission Grant
1. Visit [Alibaba Cloud Bailian Permission Management](https://bailian.console.aliyun.com/cn-beijing?tab=app#/authority)
2. If the RAM user corresponding to the AK does not exist, click **"Add User"** in the upper right corner of the page, select the corresponding RAM user and click confirm to add.
3. Click **"Permission Management"** on the right side of the RAM user corresponding to the AK, click edit, and grant knowledge base related permissions.
4. There is a 30s effective time after configuration, please wait patiently for a while.

## Available Scripts

All scripts are located in the `scripts/` directory:

| Script | Purpose | Parameters |
|--------|---------|------------|
| `check_env.js` | Check environment configuration | None |
| `list_workspace.js` | Query workspace list | `[maxResults]` |
| `list_indices.js` | Query knowledge base list | `workspaceId pageNumber pageSize` |
| `retrieve.js` | Retrieve from specified knowledge base | `workspaceId indexId query` |

## Workflow

### Step 1: Environment Check

Run `scripts/check_env.js` to check:
- Whether npm packages are installed
- Whether environment variables are configured

If not ready, prompt the user:
- Packages not installed → Run `npm install` to install all dependencies in package.json
- Missing environment variables → Guide user to configure

### Step 2: Get Workspace ID

**Do not directly ask the user for workspaceId**, instead automatically get the workspace list through the script.

Run `scripts/list_workspace.js` to get all available workspaces:

```bash
node scripts/list_workspace.js
```

Return format:
```json
{
  "workspaces": [
    {
      "workspaceId": "llm-bpp1p29i34jvoybx",
      "name": "Main Account Space"
    },
    {
      "workspaceId": "llm-hcghrtsbma82bwks",
      "name": "Podcast"
    }
  ]
}
```

**Processing Logic:**
1. Get the workspace list
2. If there is only one workspace, use it automatically and inform the user
3. If there are multiple workspaces, display the list for user to select
4. Record user selection to avoid repeated inquiries (until user wants to switch)

### Step 3: Query Knowledge Base List

For each workspace, run `scripts/list_indices.js workspaceId pageNumber pageSize` to get the knowledge base list.

**Batch Retrieval Strategy:**
1. Get all workspace lists from Step 2
2. Iterate through each workspace, call `list_indices.js` to retrieve its knowledge bases
3. Merge all knowledge base results, annotate the workspace they belong to
4. pageNumber starts from 1, pageSize defaults to 100, if current page is not fully retrieved then continue to retrieve next page

**Examples:**
```bash
# Get knowledge bases from the first workspace
node scripts/list_indices.js llm-bpp1p29i34jvoybx 1 100

# Get knowledge bases from the second workspace
node scripts/list_indices.js llm-hcghrtsbma82bwks 1 100
```

Return format:
```json
[
  {
    "indexId": "qf91w6402d",
    "name": "Product Documentation",
    "description": "Contains product user manuals, API documentation, etc."
  },
  {
    "indexId": "ip93d2pyvz",
    "name": "Customer Service Q&A",
    "description": "FAQ, customer service scripts"
  }
]
```

### Step 4: Intelligent Knowledge Base Selection

Based on the user's question and knowledge base descriptions, select **1-3 most relevant knowledge bases** for retrieval.

Selection Strategy:
- Match keywords (keywords in question vs knowledge base name/description)
- Prioritize knowledge bases that explicitly contain relevant fields in their descriptions
- If uncertain, select all or let user manually select

### Step 5: Execute Retrieval

For each selected knowledge base, run `scripts/retrieve.js workspaceId indexId query`.

Return format, content inside each chunk represents chunk content, doc_name represents source document, score represents match score, title represents chunk section title:
```json
{
  "indexId": "6fd13emwyj",
  "chunks": [
    {
      "content": "C. A small ball collides with a wall at 10 m/s, and bounces back with the same speed of 10 m/s. The magnitude of the ball's velocity change is 20 m/s. D. When an object's acceleration is positive, its velocity must increase. Example 1√ Problem Situation: As shown in the figure, Figure 2. Question 1. In the previous class, we drew the velocity-time relationship graph using a dot timer. Can you find the acceleration from it? 3. The ______________ from the v-t graph determines the magnitude of acceleration. Slope. 2. The slope value of the v-t graph represents: Acceleration value. 1. Calculate the magnitude of acceleration from the v-t graph. 4. If the v-t graph line is a sloping straight line, then the object's velocity changes uniformly, its acceleration is constant, and it moves with uniformly accelerated motion. Example 2. The three lines a, b, c in Figure 1.4-6 describe the motion of three objects A, B, C. First make a preliminary judgment about which object has the greatest acceleration, then calculate their accelerations based on the data in the graph, and explain the direction of acceleration. Analysis: Slope represents acceleration, acceleration tilts to the upper right, acceleration is positive, tilts to the lower right, acceleration is negative; so a and b are accelerating, c is decelerating, the object with the greatest acceleration, i.e., the steepest slope, is a. Description of velocity change - Acceleration. 1. Physical meaning: Describes how fast an object's velocity changes. 2. Definition: The ratio of the change in velocity to the time taken for that change. 3. Definition formula: 4. Vector nature: 5. Acceleration and velocity. Acceleration and velocity change. 6. Viewing acceleration from v-t graph: The slope value of the graph represents the acceleration value. Direction of a, accelerating motion. Direction of a, decelerating motion. Same as v0 direction.",
      "score": 0.6040189862251282,
      "doc_name": "Description of velocity change acceleration pptx-18 pages",
      "title": ""
    },
    {
      "content": "Section 4: Description of velocity change rate - Acceleration. High school physics, compulsory course 1, chapter 1. Learning objectives: Task 1: Understand the physical meaning of acceleration, be able to state the definition formula and unit of acceleration. Task 2: Be able to describe the relationship between the direction of acceleration and the direction of velocity. Task 3: Be able to distinguish between velocity, velocity change, and velocity change rate (acceleration). Understand variable speed motion. Task 4: Be able to determine acceleration from v-t graphs. 1. What is the reason for the distance between each car's final speed of 100 km/h? 2. What is the difference in their acceleration process motion? 3. Can you accurately compare the performance of these cars? Different rates of velocity change || Initial velocity (km/h) | Final velocity (km/h) | Time taken (s) | | A car start | 0 | 100 | 8.02 | | B car start | 0 | 100 | 9.53 | | C car start | 0 | 100 | 5.43 | | D car start | 0 | 100 | 4.47 | Table 1: Racing car 0~100 km/h sprint record. 4. With precise data, how to accurately compare the acceleration rate of cars? 5. Which car has the fastest velocity change? 6. Can you use other ways to compare the rate of velocity change? Observe the self-study draft Table 1, which object's velocity changes faster, A or B? | Time/s | 0 | 5 | 10 | 15 | | A v/(m·s-1) | 20 | 25 | 30 | 35 | | B v/(m·s-1) | 10 | 30 | 50 | 70 | | C v/(m·s-1) | 35 | 30 | 25 | 20 | | D v/(m·s-1) | 50 | 35 | 20 | 5 | Self-study draft Table 1: | Change | | 10 | | 40 |",
      "score": 0.6966111660003662,
      "doc_name": "Description of velocity change acceleration pptx-18 pages",
      "title": ""
    }
  ]
}
```

### Step 6: Integrate Answer

Based on retrieval results:
1. Sort by relevance (score descending)
2. Extract key information
3. Organize answer in natural language
4. Please annotate the information source at the end of the generated answer (knowledge base name; document name; section name), can reference multiple documents and sections.

## Common Permission Errors:
```
{
  "code": "Index.NoWorkspacePermissions",
  "message": "No workspace permissions can be used, workspace: ssss",
  "requestId": "05072729-7958-5FE7-8F97-B54032231CCD",
  "status": "403"
}
```
If you see the above message, there may be 2 reasons: 1. The workspace does not exist. 2. The user has not completed the 2-step authorization above, please guide to check permissions and workspace existence.

## Usage Example

**User:** "What authentication methods does our product support?"

**Flow:**
1. Check environment → Ready
2. Get workspaceId → `ws-123456`
3. Query knowledge base → Returns 3 knowledge bases
4. Select knowledge base → "Product Documentation" (most relevant)
5. Retrieve → Get authentication-related document chunks
6. Answer → "According to product documentation, OAuth2.0, SAML, and API Key authentication methods are supported..."

## Notes

- Confirm workspaceId is correct before each retrieval
- When retrieving from multiple knowledge bases, merge results and deduplicate
- Sort retrieval results by score, prioritize high-relevance content
- Credential configuration relies on Alibaba Cloud default credential chain, do not explicitly handle AK/SK