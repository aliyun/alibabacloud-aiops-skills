# Dashboard subscriptions

A subscription delivers a dashboard on a schedule. Each dashboard has at most one
subscription, with a schedule, query window and one or more notification channels.

## Inspect subscriptions

`dashboard subscription list` finds subscriptions for a dashboard;
`dashboard subscription get` returns a subscription's settings.

The [profile and region](../../profile-configuration.md) select the account and location.

## Create

The [schedule](../assets/subscriptions/schedule.json) and
[notification](../assets/subscriptions/notifications.json) examples show the JSON
inputs. Create a paused daily email subscription with:

```sh
aliyun sls dashboard subscription create --project PROJECT --subscription-name SUBSCRIPTION --type Report \
  --state Disabled \
  --schedule '{"type":"Daily","hour":9,"timeZone":"+0800","runImmediately":false}' \
  --configuration '{"dashboard":"DASHBOARD","notificationList":[{"type":"Email","emailList":["recipient@example.com"]}]}'
```

Enabling a schedule or setting `runImmediately=true` can send notifications.
The [safety rules](../../../SKILL.md#safety-rules) apply to recipients and delivery scope.

## Update, pause and remove

Update requires the complete schedule and configuration. Comparing the proposed settings
with the existing JSON helps identify omitted fields. For example, a display-name change
to an already paused subscription can use:

```sh
aliyun sls dashboard subscription update --project PROJECT \
  --subscription-name SUBSCRIPTION --type Report --state Disabled --display-name 'Daily overview' \
  --schedule "$(jq -c '.schedule' subscription.json)" \
  --configuration "$(jq -c '.configuration' subscription.json)"
```

Include any other top-level settings to retain, such as the description. If the command
cannot preserve a required existing field, do not silently drop it from a replacement.

`dashboard subscription delete` removes the selected subscription.
After a timeout, `get` or `list` can establish the current state.
Delivery records describe whether a report was sent.

## Configuration and delivery limits

[Subscription configuration](../model/subscription.md) describes schedules, channels
and delivery options.

- A recipient mailbox can receive at most 50 emails per day from the service.
- Report data comes from the dashboard's Project, including named-view members.
- A paginated table contributes its first page's screenshot.

See [subscription guidance](https://help.aliyun.com/zh/sls/subscribe-to-a-dashboard)
and [permissions](../ram-policies.md#optional-report-subscription-permissions).
