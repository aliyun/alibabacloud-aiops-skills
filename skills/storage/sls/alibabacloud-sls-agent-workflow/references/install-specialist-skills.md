# Install Specialist Skills

Use this reference only after routing has selected one or more specialist skills that are not available in the current runtime.

## Goal

Make the required specialists available with one user decision and no unrelated installations.

## Installation

Collect the exact full names of all missing selected skills. Tell the user which skills are missing, that the installation is global, and ask once for permission to install the whole set. Do not run an installation command until the user explicitly agrees.

After approval, run the following command once for each missing skill, substituting its exact full name:

```bash
npx -y skills add aliyun/alibabacloud-aiops-skills --skill <full-skill-name> -y --full-depth -g
```

The first `-y` answers the `npx` package-bootstrap prompt; the second answers the skill installer's prompt. Neither replaces the user's prior permission. If several skills are missing, do not ask separately for each one.

Verify that each requested skill is discoverable after installation, then load it and resume the original outcome. If the current runtime does not reload newly installed skills, tell the user that a session reload is needed and preserve the pending workflow.

If an installation fails or the user declines it, continue only with capabilities that are actually available. Report the affected stage and do not imitate the missing specialist from this routing skill.
