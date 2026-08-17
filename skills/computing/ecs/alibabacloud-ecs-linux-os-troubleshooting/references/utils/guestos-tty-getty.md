
# tty Terminal and getty Troubleshooting

Troubleshooting steps for tty and getty/mintty inside GuestOS.

## Troubleshooting Steps

1. On VNC, try Ctrl+Alt+F2…F6 to switch terminals and log in. Can you log in?
2. Run `ps -ef` to view the process corresponding to the tty where login failed. Is getty/mintty bound to that terminal?
3. Compare the getty/mintty configuration between the abnormal instance and a normal instance, and check whether there are differences.
4. Run `systemctl status getty@tty<tty-number>.service` to check the corresponding getty status and whether it has obviously failed.
5. Run `journalctl -xe -u getty@tty<tty-number>.service` to view logs and check whether there are obvious errors.
6. If the tty is being contended for by multiple processes: trace back the process tree, observe the characteristics of the root process, and provide a conclusion and repair suggestions.
