# Aliyun CLI Installation and Profile Checks

## Version

~~~bash
aliyun version
~~~

Aliyun CLI 3.3.3 or later is required. If it is missing or too old, install or
upgrade it by following the official Aliyun CLI documentation, then repeat the
version check. This Skill does not install software for the user.

## Plugin

~~~bash
aliyun configure set --auto-plugin-install true
aliyun plugin update
aliyun ddoscoo help
~~~

## Profile

Use only a profile that the user has already configured. Never read, display,
or set credential values.

~~~bash
aliyun configure list
~~~

The selected profile name must exist exactly and use a valid authentication
mode. A similar name is not an alias, and the default profile must never be
selected silently. If no valid profile exists, stop and ask the user to
configure one outside this session.

## Troubleshooting

- `command not found`: the CLI is absent or not on `PATH`.
- Missing Action: verify the CLI version and update the plugin; do not guess
  another Action.
- Missing profile: repeat `aliyun configure list` and let the user select an
  exact existing name.
- Region mismatch: Mainland China DDoS Pro normally uses `cn-hangzhou` and
  service outside Mainland China normally uses `ap-southeast-1`. The user's
  selection and the instance control plane remain authoritative.
- Permission error: grant the least permissions from `ram-policies.md`. A
  permission failure is not an empty configuration.

Every cloud API command still requires the selected profile, region, and
session User-Agent. Local version, plugin, and profile-list commands do not.
