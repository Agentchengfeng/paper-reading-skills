---
name: paper-reading-skills
description: Installer package for the paper-reading Claude Code / Codex skill.
---

# paper-reading-skills

This repository packages one installable skill:

- `paper-reading`: purpose-first paper interpretation, HTML long-form docs, SVG explanations, annotation bridge write-back, and Codex browser verification.

Install from GitHub:

```bash
npx -y github:Agentchengfeng/paper-reading-skills install
```

The installer copies `skills/paper-reading` into `~/.claude/skills/paper-reading` and symlinks it into `~/.codex/skills/paper-reading`.

This package contains only reusable skill instructions and scripts. It does not contain generated paper-reading HTML files, annotation logs, paper PDFs, or API keys.

Official source: `https://github.com/Agentchengfeng/paper-reading-skills`

License: Apache-2.0. Keep `LICENSE` and `NOTICE.md` when copying, redistributing, or adapting this package.
