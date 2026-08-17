# Unable to use the newly added secondary ENI

## Determine whether this is a GuestOS issue

1. Use `DescribeInstances` to obtain the instance type and confirm whether the instance type supports NIC hot-plug: [Elastic network interface (ENI)](https://help.aliyun.com/zh/ecs/user-guide/eni-overview#7d95612e86k74). Otherwise, the newly added secondary ENI requires an instance restart before it can be seen inside GuestOS.

## Troubleshooting process inside GuestOS

### Related components

- NIC driver
- IP and route configuration

### Problem diagnosis

1. Run `ip addr` or `ls /sys/class/net/` to check whether the NIC device reported by the user exists:
   - Does not exist: common causes include lack of hot-plug support, insufficient memory, NIC driver issues, interrupt conflicts, and so on. Check system logs for troubleshooting. Note: if the system logs contain messages such as "pci xxx failed to assign xxx io/mem", this is usually normal, not an exception.
   - Exists: in most cases, no IP address has been configured for the secondary ENI. The customer must manually configure it or install a multi-NIC tool. See [Create and configure an elastic network interface](https://help.aliyun.com/zh/ecs/user-guide/configure-a-secondary-eni#e0f99dc02bgz1).
