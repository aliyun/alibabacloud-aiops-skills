
# Network-Related Kernel Parameter Troubleshooting

Troubleshooting steps for network-related kernel parameters (sysctl/kconfig) inside GuestOS.

## Troubleshooting Steps

Run `sysctl -a` to check whether any configuration items may cause network anomalies.
   - Yes: It is recommended to compare against and correct based on a newly created public image.
   - No: Continue troubleshooting other possible causes.
