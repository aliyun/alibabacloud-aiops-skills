# Event Notification Rules & Not-Triggering Checklist

Reference for the OSS event-notification mechanism and the "notification
not triggering" investigation sequence. All mechanism facts are verified
against the official documentation:

- https://help.aliyun.com/zh/oss/user-guide/event-notifications/
- https://help.aliyun.com/zh/oss/user-guide/real-time-processing-file-changes-oss-event-notifications

## Mechanism facts (official, verified)

| Fact | Value |
|------|-------|
| Dependent service (legacy path) | SMQ (formerly MNS) must be activated before rules can be created |
| Rules per region | at most **10** event-notification rules per region (more requires contacting technical support) |
| Propagation delay | a newly created/updated rule takes **about 10 minutes** to take effect |
| Bucket requirement | only buckets WITH a region attribute support event notification |
| Object-match conditions | up to **5** prefix/suffix match conditions per rule |
| Multi-rule constraint | two rules covering the same target object may NOT share the same event type |
| Versioning caveat | on a versioning-enabled bucket, deleting an object WITHOUT a versionId only adds a delete marker. **Official positions differ**: the event-notification doc says neither DeleteObject nor DeleteObjects fires without a versionId, while the dedicated FAQ (why-does-deleting-a-file-not-trigger-an-event-notification) says DeleteObject DOES fire and only DeleteObjects does not. Safest guidance: always pass versionId when you need the deletion event to be certain. |
| RTMP caveat | TS/M3U8 files produced by RTMP push do not trigger event notifications |
| Trigger self-check | the upload response header `x-oss-event-status` (Base64): decoded `{"Result": "Ok"}` means OSS successfully triggered the messaging service; any other value means the trigger failed |
| Message format | notification messages are Base64-encoded JSON (`events[].eventName`, `oss.bucket.name`, `oss.object.key`, `ruleId`, ...) |
| Message detail fields | `deltaSize` = object size delta (NEGATIVE when an overwrite shrinks the file); `position` = append start offset (AppendObject only); `readFrom`/`readTo` = byte range read (GetObject only; `readTo` = range end + 1); `requestParameters.sourceIPAddress` = requester IP |
| Billing note | event notifications incur SMQ (formerly MNS) message fees in addition to OSS fees |

## Supported event types (official list)

| Group | Event types |
|-------|-------------|
| ObjectCreated | PutObject, PostObject, CopyObject, AppendObject, InitiateMultipartUpload, UploadPart, UploadPartCopy, CompleteMultipartUpload, PutSymlink, Mirror (application required), `*` wildcard |
| ObjectDownloaded | GetObject |
| ObjectModified | UpdateObjectMeta, ChangeStorageClass, `*` wildcard |
| ObjectRemoved | DeleteObject, DeleteObjects, AbortMultipartUpload, `*` wildcard |
| ObjectReplication | ObjectCreated, ObjectRemoved, ObjectModified, `*` wildcard |
| ObjectRestore | FinishRestore (cold / deep cold archive objects only) |

A group wildcard (`ObjectCreated:*`) covers every event of that group,
including future additions. Event-type names are case-sensitive.

Media-transcoding/data-processing completion is NOT an OSS event type -
those belong to IMM/MPS and must be notified through their own
Notification parameter (do not look for them in OSS event types).

## Dependent services - honest limitation

This skill CANNOT directly query the activation or delivery state of the
dependent messaging services:

- **SMQ (formerly MNS)**: verify activation in the SMQ/MNS console; the
  OSS console rule editor (Data Processing > Event Notifications) also
  fails rule creation with confusing messages (e.g. an "instance ID is
  not unique" style prompt) when the service is not activated.
- **EventBridge**: verify delivery in the EventBridge console event
  tracing page; OSS events delivered to the default bus can be delayed.

No read API for these states is available to this skill - NEVER fabricate
an activation status; state the limitation and give the console path.

## Not-triggering checklist (investigation sequence)

1. **Rule existence** (GetBucketNotification, done by the script): no rule
   configured means nothing can ever trigger - the most common root cause.
2. **Event type match**: the rule's event types must include the operation
   actually performed (exact type or `Group:*` wildcard).
3. **Object match**: the object key must match a rule's prefix/suffix
   conditions (empty prefix+suffix matches everything).
4. **Propagation window**: rule created/updated less than 10 minutes ago -
   wait and re-test.
5. **Versioning caveat**: delete without versionId never fires events.
6. **Dependent service**: SMQ/MNS activated? EventBridge delivery visible
   in event tracing? (console check paths above)
7. **Trigger self-check**: perform a fresh upload and Base64-decode the
   `x-oss-event-status` response header; not `{"Result": "Ok"}` means OSS
   failed to hand the event to the messaging service.
8. **Region support**: buckets without a region attribute cannot carry
   rules at all.

## Rule creation (manual console task - this skill never does it)

OSS console > Buckets > target bucket > Data Processing > Event
Notifications > Create Rule: rule name (letters/digits/hyphen, <=85 chars,
unique per region), event types, object prefix/suffix matching, and the
subscription endpoint (HTTP / queue). If the rule dropdown shows no
buckets, the console region selector is likely wrong - switch to the
bucket's actual region.
