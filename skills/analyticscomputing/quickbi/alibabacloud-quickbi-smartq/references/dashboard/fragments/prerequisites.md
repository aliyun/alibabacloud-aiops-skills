## Prerequisites

- Built-in utilities: `scripts/quickbi_openapi.py` and `scripts/config_loader.py`
- Valid API credentials are required (four-layer config loading, priority: env vars > workspace > global > package default)
- Automatic dashboard update detection is supported (compares `skill_generated_at` in metadata with the current `gmtModified`)

### Config Loading Priority

Four layers: env vars > workspace-level > global `~/.qbi/config.yaml` > package `config.yaml`

### First-Time Configuration Guidance

1. Call `load_config()` to load configuration (replace `__SKILL_DIR__` with the actual path)
2. Check the three fields `api_key`, `api_secret`, `user_token` — **if complete, continue silently; otherwise run the guidance flow**
3. Guidance flow (only when config is incomplete):
   - Read and show `./example/copy_skill_config.png`
   - Prompt the user in their language to copy the config (zh: Click "One-click copy skill configuration" and paste | en: Click "One-click copy skill configuration" and paste)
   - Parse and write the config; if `save_global_property` is true, also write to the global config
