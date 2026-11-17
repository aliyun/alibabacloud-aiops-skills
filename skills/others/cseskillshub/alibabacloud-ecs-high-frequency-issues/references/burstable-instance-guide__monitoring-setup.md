# M4: Monitoring Burstable Instances — Credits, Alarms, Metric Visibility

Three different jobs, three different tools. Tickets show customers
discovering credit exhaustion only when the service crawled (T-584B88C6) and
mistaking "metric has no data" for "credits broken" (T-094911FC).

## 1. Watching credits (customer console / CloudMonitor)

- CPU-credit curves (accrued / consumed / remaining, and the unlimited-mode
  advance & excess portions) are read on the instance's monitoring page in
  the ECS console or CloudMonitor:
  https://help.aliyun.com/zh/ecs/user-guide/monitor-burstable-instances#title-u46-0k1-kwy
- The **exact per-instance credit readings are customer-read**: this skill's
  injected API contract did NOT verify a machine-readable credit field, so
  the entry script never guesses them and the report asks the customer for a
  console reading or screenshot when a number is needed.

## 2. Getting warned before things break

Two independent features — configure both (their confusion caused tickets
T-6F237607 / T-0495147E):

1. **CloudMonitor credit-threshold alarm** on the instance: warns when the
   remaining credit curve crosses the chosen threshold (setup steps in the
   monitor-burstable-instances document above; the same document lists the
   alertable credit metrics).
2. **Account cost alert** (balance / bill threshold notifications):
   https://help.aliyun.com/zh/user-center/cost-alert — per that page, daily
   SMS/email/station-letter reminders; this warns about money, not about
   credits, and vice versa.
3. The platform-side **"burstable instance performance constrained" system
   notification** tells you exhaustion already happened:
   https://help.aliyun.com/document_detail/143663.html#section-glx-g6x-cn4 —
   it is the last-warning, not the early one.

## 3. Metric shows no data ("collecting" state)

- Symptom (ticket T-094911FC): OS-level monitoring curves stay empty. Usual
  cause: the **CloudMonitor agent is not installed** on the instance — not a
  credit problem.
- Fix route: the customer installs the agent following
  https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/install-and-uninstall-the-cloudmonitor-agent-for-cpp
  (this skill never runs anything inside the instance; recommend a snapshot
  before any in-guest maintenance, per support practice).
- Re-check semantics: `--check-metrics` in the entry script queries the
  **basic hypervisor-reported CPU metric**
  (`acs_ecs_dashboard` / `CPUUtilization`) for datapoint freshness only.
  Empty results must be interpreted as "this one metric leg has no data":
  the credit-curve metrics were not machine-verified for this skill and the
  script never queries guessed metric names for them.

## 4. Attribution stays customer-side

- OS tools keep no history (support wording in T-584B88C6): look at the
  process list **while** CPU is high, or deploy a self-managed collector
  (e.g. atop on Linux — suggested in tickets; on Windows use the performance
  view at the spike moment). The cloud API surface cannot replay "which
  site/process caused the spike yesterday".
