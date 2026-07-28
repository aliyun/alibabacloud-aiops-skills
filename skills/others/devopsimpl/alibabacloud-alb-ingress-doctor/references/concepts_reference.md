# ALB Ingress Core Concepts Quick Reference

## Key Resources

- **AlbConfig**: CRD resource defining ALB instance configuration (listeners, certificates, availability zones, etc.)
- **IngressClass**: Bridges Ingress with AlbConfig; `spec.parameters.name` points to the AlbConfig
- **Ingress**: Defines routing rules; associated with IngressClass via `spec.ingressClassName`
- **ALB Ingress Controller**: Managed component that watches Ingress/AlbConfig changes and syncs to ALB
- **Reconcile**: The process where the Controller syncs desired state to the ALB instance

## Common Annotation Prefix

All annotations use the prefix `alb.ingress.kubernetes.io/`:

| Annotation | Description | Example |
|------------|-------------|---------|
| `listen-ports` | Listener ports | `'[{"HTTP":80},{"HTTPS":443}]'` |
| `backend-protocol` | Backend protocol | `https` / `grpc` |
| `ssl-redirect` | HTTP to HTTPS redirect (auto-references port 80) | `true` |
| `use-regex` | Enable regex path matching | `true` |
| `rewrite-target` | URL rewrite with regex capture groups | `${1}` |
| `canary` | Canary deployment marker | `true` |
| `conditions` | Custom forwarding conditions | JSON string |
| `actions` | Custom forwarding actions | JSON string |

## Resource Relationship

```
Ingress
  └── spec.ingressClassName → IngressClass
                              └── spec.parameters.name → AlbConfig
                                                          └── ALB Instance
```

## Reconcile Flow

1. User creates/updates Ingress or AlbConfig
2. ALB Ingress Controller detects the change
3. Controller translates desired state to ALB API calls
4. If translation fails, a Warning event is generated
5. If successful, ALB instance is updated

## Certificate Matching Priority

When multiple certificates are configured, ALB selects certificates by priority:
1. **ECC > RSA**: ECC certificates have higher priority than RSA
2. **Extension > Default**: Extension certificates (SAN) take priority over default certificates
3. **Auto-discovery**: ALB can auto-discover certificates from SSL Certificates Service

Common certificate issues:
- Certificate updated but ALB still shows old certificate (auto-discovery cache)
- Multiple certificates matching the same domain (priority conflict)
- Certificate association compatibility between AlbConfig and Ingress
