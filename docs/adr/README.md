# ADRs moved

The qute-essentials plugin left this repo on 2026-07-29. It now ships from
**[`tomlupo/qute-plugins`](https://github.com/tomlupo/qute-plugins)**
(`plugins/qute-essentials/`, marketplace `qute-plugins`), which keeps its own
decision records at `docs/adr/` in that repo.

The eight records that used to live here (ADR-0001 through ADR-0008) were not
carried across under those numbers — qute-plugins started a fresh ADR sequence.
They are preserved in this repo's git history:

```bash
git log --oneline -- docs/adr/
git show <commit>:docs/adr/0006-essentials-platform-contract-realignment.md
```

This repo is a personal skills + templates library and keeps no ADRs of its
own. Do not add new ADRs here — decisions about the plugin, its guards, or the
review/release regime belong in qute-plugins.
