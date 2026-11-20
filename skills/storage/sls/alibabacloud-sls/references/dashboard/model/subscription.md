# Subscription configuration

The subscription [workflow](../integrations/subscriptions.md) selects the operation
and target. Supply the complete `schedule` object through `--schedule` and the
complete report configuration through `--configuration`. Its `dashboard` and
`notificationList` fields select the dashboard and notification channels.
`—` means no default is specified here.

## Schedule

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `type` | string | Yes | None | Hourly, Daily, Weekly, FixedRate or Cron. |
| `hour` | integer | Daily/Weekly | None | Delivery hour, 0–23. |
| `dayOfWeek` | integer | Weekly | None | 0 for Sunday through 6 for Saturday. |
| `interval` | string | FixedRate | None | Delivery interval, for example 1h. |
| `cronExpression` | string | Cron | None | Cron schedule expression. |
| `timeZone` | string | No | — | Delivery timezone as a UTC offset, for example +0800. |
| `delay` | integer | No | — | Seconds after the scheduled time; non-negative. |
| `runImmediately` | boolean | No | — | Send once immediately. Set false when preparing a paused subscription. |

The schedule controls when a report is sent; the query window controls which data
it contains. Preserve the intended timezone and time window when changing frequency.

## Notifications

Each entry in the notification array describes one channel.

| Parameter | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `type` | string | Yes | None | Email, DingTalk or Webhook. |
| `emailList` | string[] | Email | None | At least one recipient address. |
| `subject` | string | No | — | Email subject. |
| `serviceUri` | string | DingTalk/Webhook | None | Notification destination URL. |
| `content` | string | No | — | Message content. |
| `title` | string | No | — | DingTalk notification title. |
| `atMobiles` | string[] | No | — | Mobile numbers to mention in DingTalk. |
| `atAll` | boolean | No | — | Mention all DingTalk group members. |
| `method` | string | No | — | HTTP method for Webhook delivery. |
| `headers` | object | No | — | String-valued HTTP headers for Webhook delivery. |

A notification list describes all channels included in that setting. Webhook URLs
and private header values are sensitive configuration.

## Delivery options

| Configuration field | Type | Required | Default | Effect |
| --- | --- | --- | --- | --- |
| `configuration.enableWatermark` | boolean | No | false | Add a watermark to delivered images. |
| `configuration.allowAnonymousAccess` | boolean | No | false | Allow recipients to open the dashboard without signing in. |
| `configuration.attachCsv` | boolean | No | — | Attach CSV data. |
| `configuration.language` | string | No | zh | Render language. |
| `configuration.customizePeriod` | boolean | No | — | Use the custom query time range in `period`. |
| `configuration.period` | object | When `customizePeriod=true` | None | Query window, for example {"start":"-1h","end":"now"}. |

Create and update both require the complete schedule and configuration objects.
