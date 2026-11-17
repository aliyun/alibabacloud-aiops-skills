# M5 — Official help links used by this skill

Every URL below was **actually quoted inside a support-ticket dialogue**
this skill was distilled from, or returned by the batch document search with
its relevance labelled. **Nothing was completed, guessed, or "fixed up"** —
where a document is referenced in prose but has no evidenced URL, it is
listed under "not evidenced" and the skill must say "verify via the official
documentation / a support ticket" instead of citing a made-up link.
`scripts/axes/account_transfer_guide/transfer_guide.py --list-links` prints the same set from
`scripts/axes/account_transfer_guide/_constants.py`.

## ECS cross-account transfer (core)

* Overview + flow + limitations:
  `https://help.aliyun.com/zh/ecs/user-guide/how-to-cross-account-transfer-migration-ecs-instance`
  * `#0be63e3029ta3` — the transfer operation flow (support sent this anchor
    repeatedly; typical duration ~30 minutes)
  * `#babb9b36856x4` — the transfer limitations section (the "there are
    corresponding restrictions" reference)

## Image-share migration path

* Copy an image (required before cross-region sharing):
  `https://help.aliyun.com/zh/ecs/user-guide/copy-an-image`
* Use a shared image (target side):
  `https://help.aliyun.com/zh/ecs/user-guide/use-shared-images`
* Create a snapshot (the snapshot-first backup before OS replacement):
  `https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot`
* Snapshot storage billing note:
  `https://help.aliyun.com/zh/ecs/snapshots-1`

## Domain account transfer

* Online / offline paths:
  `https://help.aliyun.com/document_detail/124001.html#d53627b882rfn`
  (online, real-time) and
  `https://help.aliyun.com/document_detail/124001.html#a74e034dbfi3q`
  (offline, ~5 working days)
* How to operate:
  `https://help.aliyun.com/document_detail/120984.html#8bc770b0a5oqw`

## EIP transfer

* Pay-as-you-go EIP cross-account transfer (with the enterprise same-entity
  restriction):
  `https://help.aliyun.com/zh/eip/transfer-pay-as-you-go-eip`

## DNS follow-up

* Cloud DNS console: `https://dns.console.aliyun.com/#/dns/domainList`
* Modify a DNS record (48h propagation wording):
  `https://help.aliyun.com/zh/dns/modify-a-dns-record`
* Global DNS probe: `https://boce.aliyun.com/detect/dns`

## Account mechanics

* Phone-to-account binding limit (6):
  `https://help.aliyun.com/document_detail/37222.html`
* Account basics and limits:
  `https://help.aliyun.com/document_detail/2977405.html#12d241f9dcjp8`

## Campaign entry pages (time-sensitive)

Quoted verbatim from a 2025-08 ticket (tracking parameters stripped):

* `https://www.aliyun.com/benefit` — benefits page containing the product
  campaign entrances
* `https://www.aliyun.com/activity/ecs/99program` — the 99-CNY ECS campaign

**Caveat to always state:** campaign pages change over time; if a link
lands elsewhere, the customer should search the campaign name from the
aliyun.com homepage instead of trusting the cached link.

## Weakly related (batch document-search hits, labelled)

The batch help-search injection for "entity change" surfaced these; they are
ONLY related through "restart the instance after the transfer / OS
replacement" — cite them for that purpose alone:

* `https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md`
* `https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md`

(Instance-spec change documents also surfaced from the search but match
"change specification", not "change entity" — deliberately NOT referenced.)

## Not evidenced — do NOT fabricate links

Prose references that have NO URL in the ticket evidence (Phase-B rule: the
skill may mention the capability, must route to docs/ticket):

* SMC (Server Migration Center) operation guide
* ICP filing change rules (the "no re-filing, just repoint DNS" wording)
* A direct console link for the "Replace Operating System" entry
* The unsubscription / refund procedure document
