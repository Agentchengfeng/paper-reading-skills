# paper-reading-skills package metadata

This repository is an installer package. The operational Skill is only:

```text
skills/paper-reading/SKILL.md
```

Do not copy the repository root as a Skill directory. If installing manually, copy only `skills/paper-reading/` into one of these locations:

```text
~/.claude/skills/paper-reading
~/.codex/skills/paper-reading
```

Install from GitHub:

```bash
npx -y github:Agentchengfeng/paper-reading-skills install
```

The installer copies `skills/paper-reading` into `~/.claude/skills/paper-reading` and mirrors it into `~/.codex/skills/paper-reading` by symlink/junction when possible, or by copy when symlink is unavailable.

This package contains only reusable skill instructions, examples, tests, and scripts. It does not contain generated paper-reading HTML files, annotation logs, paper PDFs, API keys, or private workspaces.

Official source: `https://github.com/Agentchengfeng/paper-reading-skills`

License: Apache-2.0. Keep `LICENSE` and `NOTICE.md` when copying, redistributing, or adapting this package.
