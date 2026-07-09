---
name: 成峰论文Skills
description: chengfeng / AI产品自由 原创维护的论文解读 Skills 下载入口。通过一条 npx 命令从 GitHub 安装最新版到 Claude Code 或 Codex。
version: 0.1.0
---

# paper-reading-skills 下载说明

这是 **chengfeng / AI产品自由** 原创维护的论文解读 Skills 下载入口。

它会从 GitHub 安装最新版 `paper-reading` Skill 到 Claude Code / Codex 的本地 skills 目录。

安装命令：

```bash
npx -y github:Agentchengfeng/paper-reading-skills install
```

源码地址：

```text
https://github.com/Agentchengfeng/paper-reading-skills
```

安装后会把最新版 Skills 下载到：

```text
~/.claude/skills/paper-reading
~/.codex/skills/paper-reading
```

检查安装状态：

```bash
npx -y github:Agentchengfeng/paper-reading-skills doctor
```

这个 Skill 用来读论文、技术报告、arXiv PDF 或论文 repo。它不是单纯翻译论文，而是先抓研究目的，再拆问题链、机制链和证据链，最后整理成能继续追问、补充和进知识库的中文材料。

请以 GitHub 仓库为最新来源；如果转载、二次发布或改造，请保留原作者和源码链接。
