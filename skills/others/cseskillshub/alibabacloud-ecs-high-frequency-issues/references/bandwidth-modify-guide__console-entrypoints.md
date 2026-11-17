# Console entry points and official references

Entry points the customer needs, and the official pages this skill quotes. Region placeholders are
written as `{region-id}`; substitute the region the script reported and say so out loud, because
the EIP and OOS consoles are region scoped and an empty page is otherwise read as "the feature does
not exist".

## Console

| Purpose | Entry |
| --- | --- |
| Instance list, source of the bandwidth change entry | `https://ecs.console.aliyun.com/server/region` |
| EIP list for the instance region, where binding and release happen | `https://vpc.console.aliyun.com/eip/{region-id}/eips` |
| OOS bandwidth maintenance task, for a repeating temporary upgrade | `https://oos.console.aliyun.com/{region-id}/maintenance/bandwidth` |
| Price configurator, list-price estimate for a new purchase | `https://www.aliyun.com/price/cpq/` |
| Campaign page, covers fixed configurations only | `https://www.aliyun.com/daily-act/ecs/99program` |

The bandwidth change entry is reached from the instance list, not from a standalone page: select the
instance, open its bandwidth change action, and the page then offers the normal change, the
temporary upgrade and the billing mode conversion as separate choices.

## Official pages, configuration changes and billing modes

| Topic | Page |
| --- | --- |
| Instance configuration change overview | `https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes.md` |
| Renewal with a configuration change | `https://help.aliyun.com/zh/ecs/user-guide/renewal-change` |
| Temporary bandwidth upgrade | `https://help.aliyun.com/zh/ecs/user-guide/temporary-upgrade-bandwidth-on-a-daily-basis#title-jcy-ddl-31o` |
| Changing the public bandwidth billing mode | `https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-for-network-usage-1` |
| Choosing between billing modes | `https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-ecs-billing-methods.md` |
| Feature overview index | `https://help.aliyun.com/zh/ecs/user-guide/product-function-custom-node-ecs-normal.md` |
| Snapshot billing | `https://help.aliyun.com/zh/ecs/product-overview/snapshots-1` |

## Official pages, the public IP replacement path

| Step | Page |
| --- | --- |
| Convert a fixed public IP into an EIP | `https://help.aliyun.com/document_detail/61290.html` |
| Unbind an EIP | `https://help.aliyun.com/document_detail/65204.html` |
| Apply for an EIP | `https://help.aliyun.com/document_detail/65203.html` |
| Bind an EIP to an instance | `https://help.aliyun.com/document_detail/72125.html` |

## Related products, mentioned only when handing off

* Global acceleration for cross-border quality: `https://help.aliyun.com/zh/ga`.

## Rules for quoting this list

1. Quote a page only when it answers the question actually asked. A wall of links is how a ticket
   conversation loses the customer.
2. Nothing outside this list and [related_apis.yaml](../related_apis.yaml) may be presented as an
   official reference. If a case needs a page that is not here, say the answer is not verified and
   record it as a gap rather than guessing a URL.
3. The pages above are Chinese-language documentation. Summarise the relevant sentence in English
   in the answer instead of dropping a bare link on a customer who cannot read it.
4. Prices, durations and limits shown on a page are read at the time of the case and quoted as what
   the page currently says. They are not memorised between cases, and never restated as a number by
   this skill. See [evidence-gaps.md](bandwidth-modify-guide__evidence-gaps.md).
