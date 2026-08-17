# High network retransmission rate

## Determine whether this is a GuestOS issue

1. Check whether related business processes have abnormal logs.
2. TCP packet loss causes retransmissions. If packet loss is confirmed, troubleshoot according to [network-packet-loss](network-packet-loss.md) first.

## Troubleshooting process inside GuestOS

### Related components

- TCP network stack
- Business process

### Problem diagnosis

1. Follow [cloudmonitor-metrics](utils/cloudmonitor-metrics.md) to obtain the network rate trend and determine whether network congestion exists.
2. Capture packets with `tcpdump` and analyze the cause of retransmissions.
   - Abnormality found: provide the conclusion and repair suggestions.
   - Not found: continue troubleshooting other possible causes.
