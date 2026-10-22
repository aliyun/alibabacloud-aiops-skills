# Console links by account site

Use the site where the account was registered. An international-site account can
have assets in China; a China-site account can have assets outside China. Prompt
language and service RegionId do not identify the account site. Reuse an explicitly
provided site; otherwise ask once before sending the user to a login page.

| Purpose | International site | China site |
|---|---|---|
| RAM console | [International RAM](https://ram.console.alibabacloud.com/) | [China RAM](https://ram.console.aliyun.com/) |
| Security Center | [International Security Center](https://yundun.console.alibabacloud.com/?p=sas) | [China Security Center](https://yundun.console.aliyun.com/?p=sas) |

For AccessKey management, enter the selected RAM console and use its identity /
credential navigation. Configure credentials outside the conversation; never paste
secrets here. A login redirect is expected and does not prove account access.

When publishing to the international Skills portal, navigation shown to those users
must use the international column. China URLs are explicitly labeled alternatives,
not international defaults. Keep installation/CDN endpoints and API service endpoints
unchanged; they are not console navigation links.

Sources checked 2026-10-18: [RAM console navigation](https://www.alibabacloud.com/help/en/ram/user-guide/create-an-accesskey-pair),
[Security Center console navigation](https://www.alibabacloud.com/help/en/security-center/user-guide/enable-log-analysis).
