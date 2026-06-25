## User Language Detection Rules

User language is determined solely from the user's input text (`zh_CN` or `en_US`), unaffected by API responses, script output, or system configuration. All user-facing output must use the detected language.

The intent routing matrix contains bilingual keywords; both EN and CN columns are matched simultaneously. Dataset field names remain in their original API form.
