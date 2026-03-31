# Acceptance Criteria: alibabacloud-nginx-ingress-to-api-gateway

**Scenario**: Nginx Ingress to APIG Migration
**Purpose**: Skill testing acceptance criteria

---

## Correct Annotation Classification Patterns

### 1. Compatible Annotations — Must be kept in migrated YAML

#### ✅ CORRECT
```yaml
# These annotations should be preserved in migrated Ingress
annotations:
  nginx.ingress.kubernetes.io/rewrite-target: /
  nginx.ingress.kubernetes.io/enable-cors: "true"
  nginx.ingress.kubernetes.io/canary: "true"
  nginx.ingress.kubernetes.io/canary-weight: "20"
  nginx.ingress.kubernetes.io/ssl-redirect: "true"
  nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8"
  nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"
```

#### ❌ INCORRECT
```yaml
# These annotations should NOT be kept — they are ignorable
annotations:
  nginx.ingress.kubernetes.io/proxy-connect-timeout: "30"  # Ignorable
  nginx.ingress.kubernetes.io/proxy-read-timeout: "60"     # Ignorable
  nginx.ingress.kubernetes.io/proxy-body-size: "10m"       # Ignorable
```

### 2. Special Value Handling — Must change values

#### ✅ CORRECT
```yaml
# load-balance: ewma must be changed
nginx.ingress.kubernetes.io/load-balance: round_robin

# ssl-ciphers must be renamed to ssl-cipher (singular)
nginx.ingress.kubernetes.io/ssl-cipher: "ECDHE-RSA-AES128-GCM-SHA256"
```

#### ❌ INCORRECT
```yaml
# EWMA is not supported by APIG
nginx.ingress.kubernetes.io/load-balance: ewma

# Plural form is not supported
nginx.ingress.kubernetes.io/ssl-ciphers: "ECDHE-RSA-AES128-GCM-SHA256"
```

### 3. Migrated Ingress YAML — Must have correct structure

#### ✅ CORRECT
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: my-app-ingress-apig          # -apig suffix added
  namespace: production
  labels:
    migration.higress.io/source: nginx  # migration label
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /  # compatible, kept
spec:
  ingressClassName: apig              # changed from nginx to apig
```

#### ❌ INCORRECT
```yaml
metadata:
  name: my-app-ingress               # Missing -apig suffix
spec:
  ingressClassName: nginx             # Not changed to apig
```

### 4. WasmPlugin — Must use correct SDK patterns

#### ✅ CORRECT
```go
import "github.com/alibaba/higress/plugins/wasm-go/pkg/wrapper"

func (ctx *MyPlugin) OnHttpRequestHeaders(numHeaders int, endOfStream bool) types.Action {
    return types.ActionContinue
}
```

#### ❌ INCORRECT
```go
// types.BodyContinue does not exist in proxy-wasm-go-sdk
return types.BodyContinue

// Never call ResumeHttpRequest after SendHttpResponse
proxywasm.SendHttpResponse(403, nil, nil, -1)
proxywasm.ResumeHttpRequest()  // WRONG — auto-resumes internally
```

### 5. Migration Step Guidance — Must match analysis result

#### ✅ CORRECT — No unsupported annotations: direct migration reference
```
迁移步骤指引：
所有注解均为兼容或可忽略类型，无需额外插件开发。
请直接参考阿里云官方文档完成迁移：
https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/migrating-from-nginx-ingress-to-cloud-native-api-gateway
```

#### ✅ CORRECT — Has unsupported annotations: deploy new Ingress YAML + IngressClass apig + version requirement
```
迁移步骤指引：
存在不兼容注解，需要将新生成的 Ingress YAML 部署到网关中。
请参考阿里云官方文档操作：
https://help.aliyun.com/zh/api-gateway/cloud-native-api-gateway/user-guide/migrating-from-nginx-ingress-to-cloud-native-api-gateway
注意：在步骤一「指定 IngressClass」处需指定为 apig。
网关版本要求：必须确保云原生 API 网关版本在 2.1.16 及以上，否则需要升级网关版本或创建新网关。
```

#### ❌ INCORRECT — Missing version requirement when unsupported annotations exist
```
# Wrong: has unsupported annotations but does not mention gateway version 2.1.16 requirement
迁移步骤指引：
存在不兼容注解，请参考文档操作。
```

#### ❌ INCORRECT — Missing migration doc link
```
# Wrong: no reference to the official migration document
迁移步骤指引：
所有注解均兼容，可以直接迁移。
```

### 6. Higress Native Mapping — Must use correct annotation names

#### ✅ CORRECT
```yaml
# denylist-source-range maps to higress.io/blacklist-source-range
higress.io/blacklist-source-range: "192.168.1.0/24,10.0.0.5"
```

#### ❌ INCORRECT
```yaml
# Wrong: keeping nginx annotation for unsupported feature
nginx.ingress.kubernetes.io/denylist-source-range: "192.168.1.0/24"
```
