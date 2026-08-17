
# Shell Programs, Startup Configuration, and Dependency Library Troubleshooting

Troubleshooting steps for Shell programs (`/bin/sh` and user login shells), Shell startup configuration files, and their dependency libraries (dynamic linker and glibc) inside GuestOS.

## Troubleshooting Steps

1. Check whether Shell startup configuration files, such as `/etc/profile`, `/etc/bashrc`, `~/.bash_profile`, `~/.bashrc`, and `~/.profile`, contain abnormal commands.
    - Focus on content that may block login or hang non-interactive execution, such as `exit`, `logout`, `read`, `stty`, infinite loops, long-blocking external commands, obviously nonexistent commands, or commands that apply only to interactive terminals but are not guarded by conditional checks.
    - If only individual accounts are affected, first check the startup configuration files under the corresponding user's home directory.
2. Use `less /etc/passwd` to view the system account file. It is separated by `:`, and the last column is the Shell program path configured by the login account. Use it as the target `<SHELL>` for further troubleshooting.
3. Execute `<SHELL>`. If it cannot be launched successfully, focus on checking the following based on the error message: the dynamic linker `/lib64/ld-linux-x86-64.so.2` (RHEL/SUSE) or `/lib/x86_64-linux-gnu/ld-*.so` (Debian), and the base libc shared library `libc.so.6`. If the paths or versions differ from those on a normal instance, the glibc version may be inconsistent. You can refer to a normal instance to repair symbolic links or overwrite with the correct library files.
