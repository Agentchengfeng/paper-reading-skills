# paper-reading-skills

`paper-reading` is a Claude Code / Codex skill for purpose-first paper interpretation:

- research-purpose-first long-form paper reading
- HTML document output with SVG explanations
- interactive annotation markers
- local bridge write-back for highlighted questions
- Codex in-app browser refresh and DOM verification

The package contains only the reusable skill instructions and bridge script. It does not include papers, generated HTML pages, annotation logs, API keys, or private workspace material.

## Official Source

This project is created and maintained by **chengfeng / AI产品自由**.

```text
GitHub: Agentchengfeng
X: chengfeng240928
小红书: AI产品自由
公众号: AI产品自由
B站: AI产品自由
抖音 / 视频号: AI产品自由
```

Original repository:

```text
https://github.com/Agentchengfeng/paper-reading-skills
```

This repository follows the same license and attribution convention as:

```text
https://github.com/Agentchengfeng/chengfeng-videocut-skills
```

If you use, copy, translate, redistribute, or adapt this project, keep the original author, original repository link, `LICENSE`, and `NOTICE.md`.

## Install

Install directly from GitHub:

```bash
npx -y github:Agentchengfeng/paper-reading-skills install
```

The same installer also accepts a `cpm` compatibility command:

```bash
npx -y github:Agentchengfeng/paper-reading-skills cpm install
```

After installation, open a new Claude Code / Codex session so the skill list reloads.

## What The Installer Does

1. Copies `skills/paper-reading/` to `~/.claude/skills/paper-reading`.
2. Creates a symlink at `~/.codex/skills/paper-reading`.
3. Backs up any existing installed copy before replacing it.
4. Checks that `python3` is available for the local HTML annotation bridge.

Check the installation:

```bash
npx -y github:Agentchengfeng/paper-reading-skills doctor
```

Uninstall with backup:

```bash
npx -y github:Agentchengfeng/paper-reading-skills uninstall
```

## Use

In Claude Code or Codex, ask for a paper-reading task, for example:

```text
用 paper-reading 解读这篇论文，输出文档式 HTML，复杂机制用 SVG 图解。
```

For annotation bridge workflows:

```bash
python3 ~/.claude/skills/paper-reading/scripts/bridge.py \
  --page /absolute/path/to/paper-reading.html \
  --log /absolute/path/to/paper_annotation_requests.jsonl
```

The bridge listens on `127.0.0.1:8766` by default and only writes annotation requests into the configured local HTML/log files.

## Repository Layout

```text
README.md
SKILL.md
package.json
bin/install.js
skills/paper-reading/
  SKILL.md
  agents/openai.yaml
  docs/
  scripts/bridge.py
```

## Safety

- No API key is included or requested.
- No private papers or generated reading pages are included.
- Existing local installations are backed up before replacement.
- Codex installation is a symlink to the Claude skill folder, so both surfaces share one source of truth.

## License

Apache-2.0. See `LICENSE` and `NOTICE.md`.
