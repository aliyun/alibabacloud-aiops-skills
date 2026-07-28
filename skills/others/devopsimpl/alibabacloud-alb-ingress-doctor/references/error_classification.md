# Error Classification Quick Reference

## Error Categories and Typical Keywords

| Category | Typical Error Keywords |
|----------|----------------------|
| Listener | listener is not exist, listener not found, Listener is not fulfilled |
| Certificate | empty https listener default certs, none certificate found, CERT expired, certificate not updating after change |
| Path/Rules | PathConfig.Values is illegal, prefix path wildcards, RuleActions mandatory |
| Server Group | ServerGroupName illegal, server group Cookie, servicePort unmarshal |
| Quota/Rate Limit | quota exceeded, flow control |
| Network Config | zone mapping, vSwitch not found, IPv6 |
| ALB Instance | resource not found, Basic edition, order config parameter |
| Binding | IngressClass not found, ingressClassName not match |
| YAML Syntax | invalid character, unexpected end of JSON, listen-ports JSON error |
| Silent Failure | actions/conditions annotation not taking effect, forwarding rules not as expected |

## Error Pattern Matching

Each error in the knowledge base follows this structure:

```
Category → Error → Causes → Solutions
```

- **Category**: High-level grouping (listener, certificate, etc.)
- **Error**: Specific error pattern with regex for matching
- **Causes**: One or more possible root causes, each with diagnostic commands
- **Solutions**: Corresponding fix for each cause

## Common Diagnostic Commands by Category

### Listener Errors
```bash
# Check AlbConfig listener configuration
kubectl get albconfig.alibabacloud.com {name} -o jsonpath='{.spec.listeners}'
# Check Ingress listen-ports annotation
kubectl get ingress -n {namespace} {name} -o jsonpath='{.metadata.annotations.alb\.ingress\.kubernetes\.io/listen-ports}'
```

### Certificate Errors
```bash
# Check certificate configuration in AlbConfig
kubectl get albconfig.alibabacloud.com {name} -o jsonpath='{.spec.certificate}'
# Check associated Secret
kubectl get secret -n {namespace} {secret_name} -o yaml
```

### Binding Errors
```bash
# Check IngressClass
kubectl get ingressclass {name} -o yaml
# Verify IngressClass references correct AlbConfig
kubectl get ingressclass {name} -o jsonpath='{.spec.parameters.name}'
```
