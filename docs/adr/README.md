# ADRs moved

The qute-essentials plugin — and its decision records (ADR-0001 through
ADR-0008) — moved to **tomlupo/qute-platform** on 2026-07-29. The ADRs now live
there at:

    agent-kit/plugins/qute-essentials/docs/adr/

This repo is a personal skills + templates library and keeps no ADRs of its
own. The full history of the records that used to live here is preserved in
git:

```bash
git log --oneline -- docs/adr/
git show <commit>:docs/adr/0006-essentials-platform-contract-realignment.md
```

Do not add new ADRs here — decisions about the plugin, its guards, or the
review/release regime belong in qute-platform.
