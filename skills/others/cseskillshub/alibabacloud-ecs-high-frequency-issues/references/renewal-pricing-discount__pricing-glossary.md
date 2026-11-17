# Renewal Pricing Glossary (customer-language terms this skill must use precisely)

Machine-compact copy embedded in `scripts/areas/renewal_pricing_discount/_constants.py` (`GLOSSARY`). Every
definition below reflects what the injected ticket evidence actually
established; anything time-sensitive is marked and the order page stays
authoritative.

## list price vs paid price

The quote a renewal page composes is built from billing modules at catalog
prices, then discount tiers, activity prices and vouchers act on it. The
`quote` mode reproduces only the MODULE COMPOSITION (list-price trial); the
account's actual entitlement is applied by the ordering system at checkout.
That is why the skill says "composition" and never "you will pay".

## discount tier (duration-bound)

A percentage-off level matched automatically to how much subscription
remainder (or requested new period) crosses whole-year thresholds. Key
customer-relevant facts: crossing DOWN past a threshold silently drops the
tier; the console shows the best price for the CURRENT remainder; single-month
renewals typically carry no tier discount at all. Cannot be manually
requested higher - extra commercial discount is a business-manager matter.

## activity price (promotion)

Time-boxed offers (e.g. a 99-CNY/year economy-instance program). Ticket-
sourced program facts, all TIME-SENSITIVE and page-authoritative: renewal at
the same 99 level was stated valid until a specific cut-off (recorded as
2029-03-31 in one agent reply), the plan includes a FIXED public IPv4 that
does not change, activity bundles are independent commodities (no difference
swap), participation can be gated by same-person account history, and
configuring the instance can forfeit discounted renewals (see B11).

## pro-rata remainder difference

A charge that covers only the time between "now" and the current
`ExpiredTime`, not a full cycle. Commonly misread as "the whole month is
this cheap/expensive". Explain the semantics; send the customer to the page
that shows both the remainder difference and the full-cycle renewal.

## pay-by-bandwidth vs pay-by-traffic

Fixed bandwidth bills a flat fee and caps the peak rate (no traffic quota);
pay-by-traffic bills outbound internet GB (publicly documented reference
0.8 CNY/GB; inbound is not billed). Converting methods can trigger a new
payment (B6) and the bandwidth-balance refund after conversion can be 0 when
discounts applied (B7 mechanics).

## Independent billing items (do not merge them)
<!-- anchor: independent-items -->

Each of these pays, expires and stops ON ITS OWN: the ECS instance
subscription; the public bandwidth item; elastic IP addresses (configuration
+ traffic fees; the source ticket noted a configuration-fee exemption while
bound to an ECS instance under a quota - verify current rules); ECS snapshot
storage (post-pay; a ticket-stated risk line: an account overdue beyond
about 15 days can have snapshots and associated custom images auto-released
irreversibly); Cloud Security Center pay-as-you-go items (trial items may
keep accruing); domain registrations (a paid domain renewal NEVER renews a
server). When the customer says "I paid but it stopped", name the item that
actually lapsed with inventory/expiring facts.

## unsubscription (full vs non-full)

Full unsubscription windows refund near-completely; NON-FULL unsubscription
re-prices the used period at ORIGINAL prices, so deeply discounted purchases
often refund to 0 (B7). Refund of not-yet-effective renewal orders goes
through the dedicated renewal-refund page. Special cases exist only as human
applications; any issued confirm link is time-limited and the refundable
amount shrinks over time.

## downgrade refund formula (as documented by support)

remaining cost of the old spec - purchase cost of the new spec; consumed
amount re-priced at original price and discount rules; usage under 30 days
MAY multiply the consumed amount by 1.5. The system computes it; staff do
not. The downgrade checkout page displays the expected refund before
confirming.

## auto-renewal attributes

A subscription instance carries an auto-renew switch with a period unit;
`off` while inside the expiry window is the classic surprise-stop cause. The
switch state is a FACT this skill reads (`ecs:DescribeInstanceAutoRenewAttribute`);
changing it is a console action the customer performs.
