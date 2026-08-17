# Instance Cannot Connect to the Network

## Confirm Whether It Is a GuestOS Issue

1. Collect network information inside the instance and determine whether a NIC device already exists inside the instance.
   - Does not exist: submit a support ticket.
   - Exists: continue.

## GuestOS-Internal Troubleshooting Workflow

### Related Components

- Network configuration service
- NIC IP address, routes, and DNS

### Issue Localization

1. Run `ip addr` to check whether the NIC IP address meets expectations.
   - No: troubleshoot according to [guestos-nic-route](utils/guestos-nic-route.md).
   - Yes: continue.
2. Run `ip route` to check whether routes meet expectations.
   - No: follow the route section in [guestos-nic-route](utils/guestos-nic-route.md).
   - Yes: continue.
3. Run `cat /etc/resolv.conf` to check whether DNS meets expectations.
   - No: follow [guestos-dns](utils/guestos-dns.md).
   - Yes: continue.
4. Troubleshoot according to [guestos-net-sysctl](utils/guestos-net-sysctl.md).
