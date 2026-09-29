# RAM Policy (read-only investigation)

This skill is read-only end to end and performs no write operations. It reads WAF configuration across
both API generations plus one CAS read action to resolve WAF 3.0 certificate expiry. Least-privilege policy:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "yundun-waf:DescribeInstance",
        "yundun-waf:DescribeDomains",
        "yundun-waf:DescribeDomainDetail",
        "yundun-waf:DescribeInstanceInfo",
        "yundun-waf:DescribeDomainNames",
        "yundun-waf:DescribeCertificates"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "yundun-cert:GetUserCertificateDetail"
      ],
      "Resource": "*"
    }
  ]
}
```

## Notes

- Each action maps one-to-one to a read-only OpenAPI call, all at list/get level. Action names are taken
  from the `ramActions` field of the public OpenAPI metadata endpoint (verified):

  | API | Version | Authorization action | Level |
  |-----|---------|----------------------|-------|
  | DescribeInstance | 2021-10-01 (WAF 3.0) | yundun-waf:DescribeInstance | get |
  | DescribeDomains | 2021-10-01 (WAF 3.0) | yundun-waf:DescribeDomains | list |
  | DescribeDomainDetail | 2021-10-01 (WAF 3.0) | yundun-waf:DescribeDomainDetail | get |
  | DescribeInstanceInfo | 2019-09-10 (WAF 2.0) | yundun-waf:DescribeInstanceInfo | get |
  | DescribeDomainNames | 2019-09-10 (WAF 2.0) | yundun-waf:DescribeDomainNames | list |
  | DescribeCertificates | 2019-09-10 (WAF 2.0) | yundun-waf:DescribeCertificates | list |
  | GetUserCertificateDetail | cas 2020-04-07 | yundun-cert:GetUserCertificateDetail | get |

- The `yundun-cert:GetUserCertificateDetail` permission is only needed for **WAF 3.0**, whose
  `DescribeDomainDetail` returns a `CertId` but no expiry. WAF 2.0's `DescribeCertificates` returns
  `EndTime` directly and needs no CAS permission. If the customer only uses WAF 2.0, the second statement
  can be dropped.
- **This skill always calls `GetUserCertificateDetail` with `CertFilter=true`**, so the certificate
  content and private key are never returned. The permission grants metadata read only (EndDate / Expired /
  Common / Sans), not key material.
- If RAM policy validation does not recognize the `yundun-waf:` prefix, the equivalent `waf:` prefix can be
  used instead (e.g. `waf:DescribeDomains`).
- No `Modify*` / `Create*` / `Delete*` / `Upload*` / `Deploy*` permission should **ever** be granted to
  this skill — renewal and deployment are executed by the customer in the console.
