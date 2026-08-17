
# PAM Module and Configuration Troubleshooting

This document describes troubleshooting steps for PAM (Pluggable Authentication Modules) modules and configuration inside GuestOS.

## Troubleshooting Steps

1. Compare the files under `/etc/pam.d/` with those on a normal instance using the same image, and check whether differences exist.
2. Compare the file size, modification time, or hash of PAM module shared libraries under `/usr/lib64/security/` (RHEL/SUSE) or `/usr/lib/x86_64-linux-gnu/security/` (Debian) with those on a normal instance, and check whether differences exist.
3. Run `ldd <module-path>` on the preceding modules to check whether any dependent shared libraries are missing.
