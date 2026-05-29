# SDK Integration Guide

## Web SDK

### Why Integration Is Mandatory

The Web SDK must be integrated on the web side; otherwise, XHR and Fetch methods cannot handle the four soft-block actions returned by WAF:
- JS Challenge (js)
- Dynamic Token Challenge (sigchl)
- Slider CAPTCHA (captcha)
- Strict Slider (captcha_strict)

Without SDK integration, all of the above actions will fail entirely, rendering Bot management ineffective. JS challenges and slider CAPTCHAs only apply to synchronous requests; asynchronous requests (XMLHttpRequest/Fetch) must have the Web SDK injected.

### Integration Methods

**Automatic Integration**: One-click enablement, no business code changes required. However, ALB/MSE/APIG/FC/SAE access methods do not support automatic integration.

**Manual Integration**:
1. When creating a protection template in the WAF console Bot management module, obtain the SDK integration code
2. Embed the SDK code into the HTML page, ensuring it is placed before all `<script>` nodes
3. Ensure the SDK is loaded on all pages that require protection

After SDK integration, the `ssxmod_itna` / `ssxmod_itna2` / `ssxmod_itna3` cookies will be injected into the request headers.

### Static File Limitations

Static files (js/css/images, etc.) cannot have the Web SDK inserted. WAF's protection mechanism requires the SDK script to be injected into HTML pages, but the loading priority of static resources and SDK insertion are parallel in the browser — SDK logic cannot intercept requests for static resources.

Static file protection approach: Use built-in Bot detection rules + slider (which does not depend on the SDK). When creating a protection template, select the "Exclude Static Files" option.

### Cross-Origin Configuration

If the web page has cross-origin requests, cross-origin options must be configured during SDK integration. In BOT 2.0, cross-origin configuration is selected at the end of the template via the integration list.

---

## App SDK

### Why Integration Is Needed

App protection integrates WAF's anti-crawling SDK to collect mobile environment data in real time to determine whether access requests are legitimate. The collected device fingerprint information can also be used for custom policies. Alibaba Cloud WAF's Bot Protection - App Protection is currently the only solution in the industry that supports APP-SDK-based protection.

App Protection targets natively developed iOS or Android apps (excluding H5 pages within apps), creating Bot-App protection templates.

### Collection Capabilities

The App SDK can collect the following device environment information:
- Root/Jailbreak status
- Multi-instance/Clone
- Emulator
- Cloud phone
- Device farm (group control)
- Abnormal ROM
- Hook framework
- Device hardware information
- Network characteristics
- Battery status
- Proxy settings
- Application package name/version/signature
- SDK version

### Integration Notes

1. When the app and web share the same domain/endpoints, the app must integrate the SDK. Because if JS challenge policies are configured under unified endpoints, native apps have no JS environment and cannot execute JS challenges, resulting in errors that affect business operations.
2. After integration is complete, configure signature anomaly detection in the Bot management template to ensure SDK signature verification takes effect.
3. Custom feature policies can be configured using fields collected by the SDK (BOT 2.0 has added controls for SDK-collected fields).
4. After integration, when JS verification or slider is enabled and the verification is passed, WAF will set `acw_sc__v2` (JS verification) or `acw_sc__v3` (slider verification) in the response header Set-Cookie.

### Obtaining the AppKey

```bash
aliyun waf-openapi describe-bot-app-key --region {region} --InstanceId {instance_id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-bot-management"
```

### Integration Steps

1. Submit a support ticket to obtain the SDK package
2. Use the CLI command above to obtain and copy the appkey for SDK initialization
3. After integrating the SDK, collect client risk features and generate a security signature

---

## Common SDK Integration Pitfalls

### Pitfall 1: Enabling Bot Rules Without Integrating the SDK

Symptom: After enabling Bot rules, normal users are blocked or pages behave abnormally.
Cause: Without SDK integration, soft-block actions such as JS challenges cannot execute properly, and WAF may degrade to hard blocking.
Solution: Integrate the SDK first, then enable Bot rules.

### Pitfall 2: Enabling JS Challenge on Static File Pages

Symptom: Static files such as js/css are blocked, and page styles/scripts fail to load.
Cause: Static files cannot have the SDK inserted, so JS challenges cannot be completed.
Solution: Do not use JS challenge for static files; use built-in Bot detection rules + slider instead. Check "Exclude Static Files" when creating templates.

### Pitfall 3: Not Integrating App SDK When App/Web Share a Domain

Symptom: App-side users encounter errors or cannot use the app normally.
Cause: JS challenge policies are configured under unified endpoints, and the app has no JS environment to execute them.
Solution: Integrate the SDK on the app side, or use custom match conditions to separate app and web traffic with different policies.

### Pitfall 4: Outdated SDK Version

Symptom: Abnormal Bot rule hit rates, or incomplete device fingerprint collection.
Cause: The customer is using an outdated SDK version that lacks new collection fields.
Solution: Upgrade the SDK to the latest version. This can be verified via the SDK version field in SLS logs.

---

## Best Practices (Production Deployment)

1. **Configure Whitelists**: Add trusted IPs to the whitelist to prevent internal monitoring and legitimate services from being incorrectly blocked
2. **Gray-Release Testing**: Apply to non-production environments first, or set monitor mode, or enable rule gray-release to gradually increase traffic coverage by dimension
3. **Analyze Test Results**: Review security reports and logs to confirm rule hit patterns
4. **Apply to Production**: After confirming the false positive rate is acceptable, adjust to the target action
5. **Continuous Monitoring and Optimization**: Regularly review traffic analysis data and adjust policies based on attack pattern changes
