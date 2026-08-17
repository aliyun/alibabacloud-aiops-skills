
# NIC and Route Configuration Troubleshooting

Troubleshooting steps for NIC IP and route configuration inside GuestOS.

## Troubleshooting Steps

1. Use `DescribeNetworkInterfaces` to obtain the list of attached NICs, primary private IP addresses, and MAC addresses.
2. Run `ip addr` to check whether the number of NICs and their MAC addresses inside GuestOS are consistent with the information in step 1.
   - Inconsistent: submit a ticket.
   - Consistent: continue.
3. Run `ip addr` to check whether an IP address is configured on the NIC.
   - No IP: this is an issue with the network configuration service.
   - Has IP: continue.
4. Check whether the IP address of each NIC is consistent with the information in step 1.
   - Inconsistency exists: the IP configuration of that NIC is incorrect.
   - Only one primary private IP exists: it is recommended to refer to [Obtain an IP address for a secondary ENI](https://help.aliyun.com/zh/ecs/user-guide/configure-a-secondary-eni) and configure DHCP or static addressing. If the primary NIC is inconsistent, write the configuration manually.
   - A primary private IP and at least one secondary private IP exist: it is recommended to refer to [Assign secondary private IP addresses](https://help.aliyun.com/zh/ecs/user-guide/assign-secondary-private-ip-addresses) and configure static addressing. If the gateway is unclear, you can use DHCP first and then change it back to static.
5. Run `ip route` to check whether the routes meet the customer's requirements.
   > Common cases: single primary NIC with a single IP: default route `0.0.0.0/0 via <gateway> dev <primary-nic>`; primary NIC + multiple secondary NICs across multiple CIDR blocks: default route on the primary NIC, and one route for the corresponding CIDR block on each secondary NIC, such as `172.16.136.0/24 via 172.16.136.253 dev eth1`.
   - Inconsistent: provide the conclusion and repair suggestions.
   - Consistent: continue.
