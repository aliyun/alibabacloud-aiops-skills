# Dashboard subscriptions (Report Jobs)

A subscription schedules dashboard rendering and delivery through a separate
Job with `type=Report`. Each dashboard has at most one
subscription Job; multiple recipients and notification channels belong in that
Job's configuration.notificationList. A disabled Job still exists: update it
instead of creating a second one.

## API mapping

| Operation | API and resource |
| --- | --- |
| List the dashboard's subscriptions | ListJobs: GET /jobs |
| Create | CreateJob: POST /jobs with the complete Report body |
| Update | UpdateJob: PUT /jobs/{jobName} with the complete Report body |
| Delete | DeleteJob: DELETE /jobs/{jobName} |

ListJobs uses these exact filters:

```json
{"jobType":"Report","offset":"0","resourceProvider":"dashboard-id-xxx","size":"10"}
```

`resourceProvider` and `configuration.dashboard` contain the dashboard ID.
The Job's `name`, such as `report-1790061666-112087`, is a separate ID used for
update/delete.

Install the [optional Python dependencies](../cli-installation-guide.md#python-dependencies)
before online subscription work. Use the subscription
commands below with the same profile as the target dashboard.

## Configuration and channels

Use the complete [Report template](../../assets/subscriptions/report.json), replacing
its example dashboard ID, Job name, addresses and webhook URL.

| Field | Meaning |
| --- | --- |
| type | Report |
| name / displayName | Stable Job ID / human subscription name |
| state | Enabled or Disabled |
| recyclable | Preserve the supplied boolean |
| schedule | Delivery schedule; the template is Daily at hour 0, runImmediately=false |
| configuration.dashboard | Target dashboard ID |
| configuration.notificationList | Multiple notification channel objects |
| allowAnonymousAccess, attachCsv, customizePeriod, enableWatermark | Preserve requested options; do not enable them implicitly |
| extraParams | Opaque encoded render/query options; preserve the string byte-for-byte during unrelated edits |
| language | Requested render language |

Email channels use type=Email, emailList, subject and content. The UI accepts
comma-separated recipients; the helper converts a comma-separated emailList into
the API array. An omitted or empty subject uses the service-defined default subject.

Webhook destinations include DingTalk, Feishu, WeCom (WeChat Work), and custom
webhooks. Set `serviceUri` to the webhook address and `title` to the requested
notification title. Preserve channel-specific content, atAll and atMobiles.
The supplied template uses type=DingTalk. For other webhook families, preserve
the exact type and fields from a valid supplied/exported Report configuration;
do not derive API enum values from the product's display name.

Schedules support hourly, daily, weekly, fixed interval and Cron forms. Confirm the
requested frequency, timezone, dashboard query window and immediate-run behavior.
Daily/Weekly hour is 0..23; Weekly also needs dayOfWeek, FixedRate interval, and Cron
cronExpression. Preserve an existing schedule when only changing recipients.

## Workflow and commands

Run commands from the skill root. `--name` denotes the dashboard.

1. List existing Report Jobs and save the complete target-bound result:

       python3 scripts/dashboard.py subscription list --region REGION --project PROJECT --name DASHBOARD --output subscriptions.json

2. If a Job exists, copy its results[0] into report.json and edit only the requested
   fields. Keep subscriptions.json unchanged as the baseline. Add channels to the
   existing notificationList rather than replacing unrelated destinations.
   If none exists, adapt the template for a new Job.

3. Prepare/check the complete configuration offline:

       python3 scripts/dashboard.py subscription validate --region REGION --project PROJECT --name DASHBOARD --input report.json --dashboard source-dashboard.json --output report-check.json

   --dashboard is optional for preparation; without it, Project compatibility is
   explicitly unverified. View member Projects are checked online before saving.

4. Execute only when the user has authorized creating/updating the subscription
   and its destinations. Enabling a schedule can deliver notifications:

       python3 scripts/dashboard.py subscription create --region REGION --project PROJECT --name DASHBOARD --input report.json --execute
       python3 scripts/dashboard.py subscription update --region REGION --project PROJECT --name DASHBOARD --input report.json --baseline subscriptions.json --execute

5. Delete only the Report Job selected by the same dashboard-bound baseline:

       python3 scripts/dashboard.py subscription delete --region REGION --project PROJECT --name DASHBOARD --baseline subscriptions.json --execute

Create/update/delete require `--execute` for cloud requests. `list` is read-only and
fetches all matching pages before reporting completion or checking uniqueness.
An existing or changed Job blocks a conflicting mutation. Writes are not
automatically retried; readback verifies the Job state, not successful delivery.
Use `--profile` and `--endpoint` consistently for subscription operations and
dashboard/StoreView checks. `--endpoint` selects the SLS service, not the
notification's `serviceUri`.

## Product limitations

- At most 50 emails per recipient mailbox per day. This is a shared service limit,
  not a 50-recipient limit or a quota local to one Job.
- Cross-Project data is unsupported: subscriptions cannot retrieve data queried
  from another Project. The helper checks explicit query Projects and online
  StoreView member Projects before create/update. Resolve dynamic resource
  coordinates first; these checks do not prove arbitrary SQL's complete lineage.
  Disabling an existing Job is allowed even if its dashboard can no longer render.
- A paginated table contributes only the first page's screenshot.

[Official subscription guidance](https://help.aliyun.com/zh/sls/subscribe-to-a-dashboard)
also describes configuration in the console.
