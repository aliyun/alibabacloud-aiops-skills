# The instance stays in the "Starting" state

## Determine whether this is a GuestOS issue

This phenomenon domain focuses on the phase in which the instance state is `Starting`, that is, before the platform hands control over to GuestOS. Because GuestOS has not taken over yet, no data can be collected inside the instance during this phase.

1. Use `DescribeInstances` to confirm whether the instance state is `Running`.
   - Yes: the platform has already handed control over to GuestOS. Troubleshoot according to [guestos-not-running](guestos-not-running.md).
   - No, it is still `Starting`: continue.
2. Use `DescribeImageSupportInstanceTypes` to verify whether the image of the instance supports the current instance type.
   - Incompatible: an incompatible image and instance type cause startup failure. Provide the conclusion and recommend replacing the image or changing the instance type.
   - Compatible: continue.
3. Use `DescribeInstanceHistoryEvents` to check whether system events related to instance startup or maintenance exist.
   - Related events exist: follow the handling recommendation in the event details. This is not a GuestOS issue.
   - No related events: continue.

## Troubleshooting process inside GuestOS

### Related components

- Not applicable. GuestOS has not started in this phase, so there is no in-instance component to investigate.

### Problem diagnosis

The `Starting` state normally lasts less than one minute. If it lasts significantly longer, the startup phase on the platform side is abnormal, and the investigation available to the user is limited to the following steps:

1. Confirm with the user whether the instance type, image, or disk configuration was changed just before this startup, and whether the startup follows a resource change.
   - A change exists: verify the compatibility of the new configuration according to the boundary determination steps above.
   - No change exists: continue.
2. Ask the user whether the instance can be restarted, and after explicit confirmation, stop the instance and start it again once. Then poll the state with `DescribeInstances`.
   - It becomes `Running`: the startup phase recovered. Continue with the phenomenon domain that matches the remaining symptom, if any.
   - It stays in `Starting`: continue.
3. If the instance is still stuck in `Starting` after the retry, the abnormality is on the platform side. Recommend that the user submit an [Alibaba Cloud support ticket](https://help.aliyun.com/zh/support/) and provide the instance ID, region, the time when the startup began, and the operation history.
