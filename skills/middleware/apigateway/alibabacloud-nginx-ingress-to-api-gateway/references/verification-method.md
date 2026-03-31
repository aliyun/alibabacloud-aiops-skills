# Verification Method

## Step-by-Step Verification

### Step 1: Parse and Archive Verification

```bash
# Verify original YAML is saved
ls -la migration-output/original-ingress.yaml

# Verify Ingress count matches expected
python3 -c "
import yaml
with open('migration-output/original-ingress.yaml', 'r') as f:
    docs = list(yaml.safe_load_all(f))
    ingresses = [d for d in docs if d and d.get('kind') == 'Ingress']
    print(f'Total Ingress resources: {len(ingresses)}')
"
```

### Step 2: Compatibility Analysis Verification

```bash
# Verify analysis files exist
ls -la migration-output/reports/analysis.json
ls -la migration-output/reports/compatibility-analysis.txt

# Verify JSON is valid
jq '.' migration-output/reports/analysis.json

# Count Ingress by category
jq '[.[] | .classification] | group_by(.) | map({category: .[0], count: length})' migration-output/reports/analysis.json
```

### Step 3: Resolution Verification

For each Ingress with unsupported annotations, verify one of:
- Higress native mapping applied
- Safe-to-drop confirmed
- Built-in plugin selected
- Custom WasmPlugin developed and compiled

```bash
# Verify custom WasmPlugins compile
for plugin_dir in migration-output/plugins/*/; do
    if [ -d "$plugin_dir" ]; then
        echo "Checking plugin: $plugin_dir"
        ls -la "${plugin_dir}main.wasm" 2>/dev/null || echo "WARNING: main.wasm not found in $plugin_dir"
    fi
done
```

### Step 4: Migrated YAML Verification

```bash
# Verify individual Ingress files exist
ls -la migration-output/ingresses/

# Verify combined YAML exists
ls -la migration-output/all-migrated-ingress.yaml

# Verify YAML is valid Kubernetes Ingress
python3 -c "
import yaml
with open('migration-output/all-migrated-ingress.yaml', 'r') as f:
    docs = list(yaml.safe_load_all(f))
    for doc in docs:
        if doc:
            assert doc.get('kind') == 'Ingress', f'Invalid kind: {doc.get(\"kind\")}'
            assert doc.get('spec', {}).get('ingressClassName') == 'apig', 'ingressClassName must be apig'
    print(f'All {len([d for d in docs if d])} Ingress resources are valid')
"

# Verify ingressClassName is set to apig
grep -c "ingressClassName: apig" migration-output/all-migrated-ingress.yaml

# Verify migration label is added
grep -c "migration.higress.io/source: nginx" migration-output/all-migrated-ingress.yaml
```

### Step 5: Report Verification

```bash
# Verify migration report exists
ls -la migration-output/migration-report.md

# Verify report sections
echo "Checking report sections..."
grep -q "## Overview" migration-output/migration-report.md && echo "✓ Overview"
grep -q "## Compatibility Analysis" migration-output/migration-report.md && echo "✓ Compatibility Analysis"
grep -q "## Deployment Guide" migration-output/migration-report.md && echo "✓ Deployment Guide"
```

## Docker Image Verification

```bash
# List built images
docker images | grep higress-wasm

# Verify image contents (optional)
docker run --rm higress-wasm-<plugin-name>:v1 ls -la /plugin.wasm
```

## Complete Verification Checklist

- [ ] `migration-output/original-ingress.yaml` exists and contains all input Ingress
- [ ] `migration-output/reports/analysis.json` is valid JSON with classification for each Ingress
- [ ] `migration-output/reports/compatibility-analysis.txt` contains human-readable report
- [ ] All custom WasmPlugins have compiled `main.wasm`
- [ ] `migration-output/ingresses/` contains individual migrated YAML files
- [ ] `migration-output/all-migrated-ingress.yaml` contains all migrated Ingress
- [ ] All migrated Ingress have `ingressClassName: apig`
- [ ] All migrated Ingress have label `migration.higress.io/source: nginx`
- [ ] `migration-output/migration-report.md` is complete with all sections
- [ ] Docker images are built for custom plugins (if any)
