# Channel Matrix: Login Methods, Entry Paths and Fallback Chains

Five ways into an instance, what each one depends on, and what to switch to
when it fails. This is the rescue-channel playbook: a failure on one path
is a fact about THAT path's dependencies, not a verdict on the server.

## Method comparison

| Method | Path it uses | Needs from the guest | Needs from your side | Typical failure it exposes |
| --- | --- | --- | --- | --- |
| VNC / management terminal | out-of-band console | only a powered-on, booting instance | browser | shows boot/hang screens; blind to sshd, ports, security groups |
| Workbench password / key login | Alibaba Cloud internal path to the ssh port | ssh service up, port reachable internally | browser | broken by guest hangs, non-standard port with one-click (see below), local-egress issues do NOT hit it |
| Workbench one-click | internal path, port 22 ONLY | sshd listening on 22 | browser + logged-in console account | the first thing to die after an ssh port change |
| Session manager (Cloud Assistant based) | Cloud Assistant channel | agent installed and online | console/CLI session | dies when the guest is hung or the agent is gone - independent of ssh |
| Native SSH client (or RDP on Windows) | public network path end to end | ssh service + public IP + ingress for your source IP | your whole local path | the layer separator: works while web paths fail (or the reverse) pinpoints WHERE the break is |

## Entry paths (console)

* ECS console > Instances > select region > instance row > **Remote
  Connection** > choose the method; VNC family opens in a browser window.
  Official walkthroughs: connecting by VNC
  <https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc.md>,
  choosing among the five login methods
  <https://help.aliyun.com/zh/ecs/user-guide/guide-and-best-practices-for-logging-into-ecs-5-methods-and-how-to-choose.md>,
  and the general connection guide
  <https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md>.
* Workbench Linux login (password or key):
  <https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-or-key.md>.
* File upload through the web terminal (size limit per the document):
  <https://help.aliyun.com/zh/ecs/user-guide/manage-files.md>; from
  Windows desktop, WinSCP
  <https://help.aliyun.com/zh/ecs/use-cases/use-winscp-to-upload-a-file-to-a-linux-instance>.

## Fallback chains (what to try next, in order)

1. **Any web path refused, instance reported reachable?** First separate
   lifecycle: is the instance Running (console or `diagnose` output)? A
   stopped or transitioning instance refuses every channel with
   state-support wording - that is L1, not the channel.
2. **SSH client dead, need in right now:** VNC (needs nothing from the
   guest network stack) or session manager (needs only the agent).
3. **Workbench passwordless / one-click blocked:** switch to the terminal
   connection form with user name + password, or to VNC; if the same
   machine answers VNC slowly or not at all, that pattern is the hang
   family - go gather the monitoring leg before anyone restarts.
4. **One-click broken after an ssh port change:** expected - one-click is
   fixed to port 22. Use password login on the new port or a native
   client; restoring one-click needs the customer to move sshd back to 22
   (their configuration decision).
5. **Workbench fine but own computer cannot connect:** do NOT troubleshoot
   the server first; run the local ladder (telnet, hotspot, mtr, security
   software, security-center IP whitelist review) -
   [diagnosis-playbook.md](console-channel-diagnosis__diagnosis-playbook.md) C5.
6. **VNC garbled keys / dead modifier keys:** English input method, other
   browser, other machine - and prefer a real client once logged in. The
   VNC path is a rescue console, not a daily driver.
7. **Web session dropped mid-task:** reconnect; for long jobs run them
   under nohup/screen so a browser hiccup stops costing work:
   <https://help.aliyun.com/zh/ecs/configure-linux-to-keep-the-process-running-after-the-ssh-client-is-disconnected>.

## Password facts worth stating plainly

* A password reset performed while the instance runs takes effect only
  after the next restart for the offline type of reset - the console
  dialog states which type it is:
  <https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance>.
* Restarting the instance is a human console action
  (<https://help.aliyun.com/zh/ecs/user-guide/restart-instances>) and
  MUST be preceded by the snapshot-first warning; this skill never
  performs either.
* Instance lifecycle states and what each allows:
  <https://help.aliyun.com/zh/ecs/user-guide/overview-52.md>.

## Windows note

RDP (3389) rides the same matrix with the native-client row replaced by
"mstsc over the public path". VNC onto the desktop works while mstsc
refuses = remote-desktop service area -> the Windows remote-desktop
diagnosis skill (see [handoff-playbook.md](console-channel-diagnosis__handoff-playbook.md)), not this
package.
