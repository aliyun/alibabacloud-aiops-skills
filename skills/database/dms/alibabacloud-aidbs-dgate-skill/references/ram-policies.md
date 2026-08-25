# RAM permissions

```yaml
required_permissions: []
```

This Skill does not call Alibaba Cloud POP APIs with a RAM AccessKey, so it requests no RAM Actions. Dgate uses a user-specific, Region-bound Agent AccessToken and enforces its own Agent identity, instance ACL, security policy, masking, and audit controls.

Do not replace Dgate authorization with broad RAM permissions and do not declare wildcard permissions. Instance access must be granted to the current Agent through the Alibaba Cloud AI Data Gateway console.
