## ⚠️ Entry Check (Required Before Every Query)

> **Hard constraint**: Whenever the user asks any question, **this check MUST be executed first** before any follow-up step.

**Steps**:
1. Run the following code to check whether the dashboard has been updated:
```python
import sys, os
sys.path.insert(0, os.path.join('__SKILL_DIR__', 'scripts'))
from config_loader import load_config
from quickbi_openapi import get_dashboard_update_time
config = load_config()
result = get_dashboard_update_time(host=config["server_domain"], access_id=config["api_key"], access_key=config["api_secret"], page_id="__PAGE_ID__", user_id=config["user_token"])
has_update = result["success"] and result["data"]["last_modified"] > __SKILL_GENERATED_AT__
print(f"has_update: {has_update}")
```

2. **Handle the result**:
   - `has_update == False` → silently continue with the query
   - `has_update == True` → **immediately terminate the skill** and output the update prompt **in the user's language**, including:
     - The dashboard "__DASHBOARD_NAME__" has been updated; the data structure of this skill may be outdated
     - Guide the user through two steps:
       1. Delete the current skill (`__SKILL_NAME__`)
       2. Regenerate the skill (provide the dashboard URL: `__DASHBOARD_URL__`)
     - Wrap URLs in backticks to prevent link rendering

> **LLM execution constraint**: Terminate immediately after emitting the prompt above. Do **NOT** automatically delete or regenerate the skill. The user must take action manually.

---
