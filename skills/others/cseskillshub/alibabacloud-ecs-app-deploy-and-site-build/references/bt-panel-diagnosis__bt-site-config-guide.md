# BT panel use and site configuration — guidance the skill can give

Guidance grounded in the scenario's cases and the official pages listed at
the end. Anything the panel itself does as an application (plugin behavior,
certificate issuance dialogs, product bugs) is the vendor's layer: this
document gives the customer the right clicks and the right expectations, and
routes the rest (see handoff-boundaries.md (in alibabacloud-ecs-high-frequency-issues)).

## 1. Recovering the panel entry (address, port, login)

The panel's entry is printed only from inside the instance; there is no
cloud-side record of it. The recovery flow the support threads used verbatim
(T-7AD5DAC8, T-C9CE1F85):

1. Connect to the instance OS — Workbench or SSH (Windows: RDP). Official
   page in the list below.
2. Run `bt default` — the echo contains the access URL with the CURRENT
   port, plus the username and password lines. Or run `bt 14` for the
   external/internal address list with the entry path.
3. Copy the ADDRESS line (scheme, host, port, entry path). Do not paste the
   credential lines into any chat or ticket; if they were ever exposed,
   change the panel password inside the panel afterwards.
4. Open that URL. If the browser cannot establish a connection at all
   (ERR_CONNECTION_RESET shaped failures), the port is admitted nowhere in
   front of the panel — go to
   [bt-access-triage.md](bt-panel-diagnosis__bt-access-triage.md) layer 1 with the REAL port,
   not with 8888.

Expectation to state plainly: the panel's port is frequently changed or
randomized (observed in this scenario: 39575, 51973, 19356). "I bought BT
panel support" does not mean the cloud side holds or can restore the
credentials — they live in the guest only (case T-4B98459C: an outsourcing
handover that withheld them left two certificates unmanaged; recovery always
runs through the instance, never through the vendor or Alibaba Cloud).

## 2. Login failures and account lock

- Wrong password once the entry is right: recover or reset inside the panel
  menu the customer runs themselves (`bt` menu option 5 in the field threads
  — printed as a step, never dispatched).
- Locked after repeated failures: the panel's own security page lifts the
  lock, or wait out the panel's lock duration.
- Lost INSTANCE login (not the panel): that is the credential area; the
  console password reset (online, or offline when it fails) is a customer
  operation — create a snapshot in the console first. Case T-43233650 was
  recovered exactly that way. This skill performs no resets.

## 3. SSL certificates and HTTPS sites

- Per-site panel certificates live under
  `/www/server/panel/vhost/cert/<domain>/`, in the format the chosen web
  server loads (Apache and Nginx expect different bundles; converting a
  certificate is the customer's step, usually re-download in the right
  format).
- A recurring silent killer is a PATH or FORMAT mismatch: case T-76855857 —
  Apache refused to start because the configured path missed one directory
  level (the `www` segment) versus where the files actually were. Compare
  the error's stated path against the real listing with the consented
  read-only probes (`ls_dir`, `stat_path`) — that comparison is this skill's
  part; placing files is the customer's.
- Forced HTTPS with nothing listening on 443 makes the site unreachable
  over https while the panel still works (T-21252C12): check 443 in the
  `listen_ports` reading before touching certificates again.
- One-click certificate application inside the panel can fail its domain
  control validation (T-9B0DD777): collect which validation method (file vs
  DNS record) and the exact failing wording; ACME-side behavior is the CA's
  and the panel's layer — route there with evidence if the record itself is
  correct.
- Certificate expiry management: the certificate console can issue free
  certificates the customer then installs on the site (T-4B98459C's recovery
  path for the abandoned ones).

## 4. Sites returning 502/504 and slow loads

The 5xx comes from the web/service layer behind the panel UI, not from the
panel address. Sequence that worked (T-EF5FB057, T-13B097B7):

1. Which URL fails — site path vs `/login` panel path (a dead site with a
   living panel is a service-layer case);
2. customer readings: `systemctl status nginx|httpd|php-fpm`
   (`service_status` self-check), plus `resource_readings`;
3. whitelisted disk watermark (`df_h`) to exclude the volume;
4. a service restart by the customer clears a hung pool (snapshot first as
   the standing reminder); recurrence with high TIME_WAIT or queue numbers
   is tuning work — manual, in the customer's editor, with this report as
   the before-picture;
5. readings that show saturation hand off to the resource area.

## 5. WordPress and plugin-side oddities

Admin redirects to 127.0.0.1 and similar loops can come from a security
plugin's settings, not the server (T-76855857: renaming the
`all-in-one-wp-security-and-firewall` plugin directory restored the wp-admin
page). That is application layer: state the boundary, give the
rename/disable step as the customer's own action with a snapshot reminder,
and keep the server layer's clean bill of evidence attached.

## 6. Windows panel instances

Windows hosts run the panel too, including ASP sites through IIS installed
via the panel's software manager (T-EF9EA87F). What this skill can prove on
Windows stays narrow: volume health and directory contents (whitelisted).
Service state and IIS site bindings have no whitelisted equivalent: those
conclusions are explicitly low-confidence and ride on the customer's panel
UI and Services console readings. The WordPress-on-Windows official page
below is the reference for stack questions.

## 7. Files without the panel

Uploading a verification file does not require the panel at all (T-DFBE216E):
SFTP/scp to the site directory, or the panel's file page — either way the
customer moves the file; the site root is visible in the panel's site list.
CDN in front and sub-domains complicate WHICH host serves the path: check
the DNS resolution of the exact hostname before assuming the ECS box answers
for it.

## Official documentation (verified in this batch — group A)

| Topic | URL |
| --- | --- |
| Buy a Linux instance and deploy the BT panel from the console | https://help.aliyun.com/zh/ecs/user-guide/purchase-a-linux-instance-and-deploy-bt-panel-from-the-console.md |
| Deploy the BT panel | https://help.aliyun.com/zh/ecs/user-guide/installation-of-pagoda-panel.md |
| Marketplace images (what "BT image" actually ships) | https://help.aliyun.com/zh/ecs/user-guide/alibaba-cloud-market-mirror-images.md |
| WordPress on a Windows instance | https://help.aliyun.com/zh/ecs/user-guide/build-a-wordpress-website-on-a-windows-instance.md |
| Network connectivity FAQ | https://help.aliyun.com/zh/ecs/network-connectivity-faqs.md |

Cited by support threads but awaiting a fresh link check before quoting to a
customer (group B): connecting to a Linux instance by password or key
(https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-or-key),
and getting started with security groups
(https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups) —
the latter carries the console's one-click entry for common web ports.

Gap, stated honestly: no Alibaba Cloud documentation page was verified in
this batch for the panel's port mechanism or the `bt default` / `bt 14`
echo format; the entry facts above come from the cases themselves. Panel
product behavior (dialogs, bugs, the official repair tool) is the vendor's
support domain.
