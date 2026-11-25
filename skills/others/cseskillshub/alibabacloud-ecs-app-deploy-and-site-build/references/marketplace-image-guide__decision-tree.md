# Decision tree and symptom routing

The script routes on a symptom token; this file is the human-readable version of the
same table. Run `python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --list-symptoms` to
print the vocabulary the script actually accepts.

## Step 1: is this the paid-image axis at all?

| Signal in the customer's wording | Move |
|---|---|
| Names a Marketplace product, a vendor image, a preinstalled stack, or an image licence fee | Continue to step 2 |
| Quotes the console message about a Marketplace image blocking a conversion | Continue to step 2, then split by operation (step 3) |
| Says "image" but means a Docker or container image, or describes a pull failure | Stop. `handoff.md`, container channel |
| Describes software inside the image failing while the instance itself boots | Stop. `handoff.md`, vendor support entry |
| Asks to install from an ISO, or to upload an image file | Stop after stating the rule. `handoff.md`, image-import channel |
| Instance will not boot and the attached image is public | Stop. `handoff.md`, instance-boot channel |

## Step 2: read the facts that drive every branch

| Fact | Source | Branches that need it |
|---|---|---|
| Attached image identifier | `DescribeInstances` | all |
| Image name, owner alias, product code, operating-system name, size, status | `DescribeImages` | all |
| Instance type and zone | `DescribeInstances` | compatibility, transfer |
| Lifecycle state | `DescribeInstanceStatus` | system-disk change, cancellation |
| Charge mode | `DescribeInstances` | conversion, billing, refund |
| Resource group of the instance | `DescribeInstances` | authorization |

The verdict printed by the script names the field that drove it. Where the image does
not resolve in the requested region, say "not visible in this region for this
credential" and ask the customer to switch region or account.

## Step 3: symptom routes

| Symptom token | Customer-visible message or situation | Underlying rule | First question to ask |
|---|---|---|---|
| `conversion-blocked` | Console states the instance image is a Marketplace image and conversion is not supported | A Marketplace-image instance cannot move between charge modes | Which operation were you performing when it appeared? |
| `boot-stuck-old-image` | Instance sits in an operating-system loading state after buying an old Marketplace image | Older Marketplace images can be limited to specific instance families | What is the exact image name shown at purchase? |
| `image-not-compatible` | Image will not install on the chosen instance type | Support lists are vendor-set and sometimes printed in the image name | Instance identifier plus image identifier or exact name |
| `renewal-charge-question` | "Does the paid image keep charging when I renew?" | The licence renews with the instance, on the instance cycle | Region and instance identifier |
| `unexpected-image-charge` | A statement line the customer does not recognise | The fee follows the attached image, not what was installed by hand | Which instance, and which statement period? |
| `duplicate-renewal-order` | Two renewal orders for one image | Order-level fact, invisible to read-only APIs | The two order numbers from the billing console |
| `refund-blocked` | Cancellation refused while a paid image is attached | Change to a free image first; a paid image fee is not refundable once consumed | Instance identifier and current attached image |
| `refund-amount-missing` | Cancellation page shows no amount after an image change | Either the image is still paid, or state propagation lags | Is the instance now on a public image? |
| `payment-failed-on-image-change` | Payment refused while selecting a Marketplace image on a disk change | The flow requires a Stopped instance | What is the instance state right now? |
| `transfer-not-supported` | Self-service transfer refused | Marketplace-image instances cannot be transferred | Read the image facts to confirm the block reason |
| `export-not-supported` | Export or download refused | Export excludes encrypted images, Marketplace-derived custom images and Windows Server | Is the goal a file copy or a migration? |
| `no-permission-on-image-change` | Permission error when selecting a community or Marketplace image, with a request identifier | Marketplace images carry no resource group, so a group-scoped check fails | Is the RAM user's permission scoped to a resource group? |
| `docker-pull-failure` | Container image will not pull | Not this tier | Confirm the word "image" means a container image |
| `image-software-failure` | Preinstalled database or panel will not start | Not this tier; the image attached fine | Does the instance itself boot? |
| `iso-install-request` | Wants to install from an ISO | ISO mounting unsupported | Which operating system, and is it licensed? |
| `unrelated-boot-failure` | Boot or network fault with a public image attached | Not this tier | Which image is attached? |

## Step 4: intent fallback

When the customer describes a goal rather than a message, use `--intent`:
`selection`, `billing`, `conversion`, `refund`, `system-disk`, `transfer`, `export`,
`authorization`, `inventory`, `triage`. An intent expands to the symptom rows above;
`inventory` skips routing and reports the region-wide paid-image census instead.

## Console-message reference

The console renders these messages in the customer's site language. Match on the
meaning, and ask the customer to paste the original text rather than translating it
yourself; `--error-text` scores the quoted text against the routing keywords.

| Message, in substance | Route to | Watch out for |
|---|---|---|
| The instance image is a Marketplace image, conversion is not supported | `conversion-blocked` | Same text appears from the public IP entry. Do not answer before step 4 of the tree in `SKILL.md`. |
| Payment or order failed during an image change | `payment-failed-on-image-change` | Check state before touching billing. |
| Permission denied on the image-selection or system-disk call, with a request identifier | `no-permission-on-image-change` | The instance being in the group is not sufficient; the image has no group. |
| A long-running loading state after purchase | `boot-stuck-old-image` | Confirm whether the refund window has already passed before suggesting a rebuild. |

No numeric error code is quoted anywhere in this package: the error-code catalogue for
this tier was not part of the verified evidence, so inventing one would send the
customer to the wrong place.
