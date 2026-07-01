# paper-reading-skills

> 给 Claude Code / Codex 使用的论文解读 Skill。

这个项目把我的论文解读流程做成了一个可安装的 Skill：先抓论文目的，再拆问题链、机制链和实验结论，最后输出文档式 HTML 长文。复杂概念默认用 SVG 图解，阅读过程中可以划线提问，再通过本地 bridge 把问题写回 HTML。

它不是论文搜索工具，也不是 PDF 阅读器。它聚焦一件事：让 Agent 把一篇论文讲成“能读懂、能追问、能继续补充”的长文档。

这个仓库只包含可复用的 Skill 指令、HTML 协作约定和 bridge 脚本，不包含论文 PDF、生成后的 HTML、划线日志、API key 或私人工作区内容。

## 官方来源

本项目由 **成峰 / AI产品自由** 原创并维护。

```text
GitHub: Agentchengfeng
X: chengfeng240928
小红书: AI产品自由
公众号: AI产品自由
B站: AI产品自由
抖音 / 视频号: AI产品自由
```

原始仓库：

```text
https://github.com/Agentchengfeng/paper-reading-skills
```

本项目沿用 `chengfeng-videocut-skills` 的协议和来源注明方式：

```text
https://github.com/Agentchengfeng/chengfeng-videocut-skills
```

如果你使用、转载、翻译、二次发布或改造成自己的 Skill，请保留原作者、原始仓库链接、`LICENSE` 和 `NOTICE.md`。

## 一句话安装

直接从 GitHub 安装：

```bash
npx -y github:Agentchengfeng/paper-reading-skills install
```

也支持 `cpm` 兼容命令：

```bash
npx -y github:Agentchengfeng/paper-reading-skills cpm install
```

安装后重新打开 Claude Code / Codex 会话，让 Skill 列表重新加载。

## 安装器做了什么

默认安装到：

```text
~/.claude/skills/paper-reading
~/.codex/skills/paper-reading
```

具体动作：

1. 把 `skills/paper-reading/` 复制到 `~/.claude/skills/paper-reading`。
2. 把 `~/.codex/skills/paper-reading` 软链到 Claude 的同一个 Skill 目录。
3. 替换旧版本前自动备份。
4. 把 `LICENSE`、`NOTICE.md`、`CITATION.cff` 一起复制进安装目录。
5. 检查 `python3` 是否可用，因为本地划线协作 bridge 需要它。

检查安装状态：

```bash
npx -y github:Agentchengfeng/paper-reading-skills doctor
```

卸载并保留备份：

```bash
npx -y github:Agentchengfeng/paper-reading-skills uninstall
```

## 最短使用方式

在 Claude Code 或 Codex 里直接说：

```text
用 paper-reading 解读这篇论文，输出文档式 HTML，复杂机制用 SVG 图解。
```

也可以给论文 repo：

```text
用 paper-reading 整理这个论文仓库，先讲研究目的，再讲核心机制和实验结论。
```

## 划线协作

生成的 HTML 支持三类划线动作：

```text
名词讲解
逻辑梳理
作图理解
```

如果需要让页面把划线问题写回本地文件，启动 bridge：

```bash
python3 ~/.claude/skills/paper-reading/scripts/bridge.py \
  --page /absolute/path/to/paper-reading.html \
  --log /absolute/path/to/paper_annotation_requests.jsonl
```

bridge 默认监听：

```text
127.0.0.1:8766
```

bridge 只做本地写回：接收标记、写 JSONL、修改 HTML。它不调用模型，也不保存 API key。

## 工作流

```text
论文 / repo / PDF
    |
    v
先判断研究目的
这篇论文到底想解决什么问题？
    |
    v
拆问题链
为什么原有方法不够？
瓶颈在哪里？
    |
    v
拆机制链
作者提出了什么结构、流程或训练方式？
每一步解决哪个瓶颈？
    |
    v
拆证据链
实验指标、对照对象、消融结果分别证明什么？
    |
    v
生成文档式 HTML
长文解释 + SVG 图解 + 可划线追问
    |
    v
继续补充 / 重组正文
用户划线提问后，把解释补进原文结构
```

核心原则是：不要把论文翻译成一堆段落，而是把它讲成一条能追踪的逻辑链。

## 仓库结构

```text
paper-reading-skills/
├── README.md
├── LICENSE
├── NOTICE.md
├── CITATION.cff
├── package.json
├── bin/
│   └── install.js
└── skills/
    └── paper-reading/
        ├── SKILL.md
        ├── agents/
        │   └── openai.yaml
        ├── docs/
        │   ├── 01-paper-prompt.md
        │   ├── 02-html-contract.md
        │   └── 03-layout-standard.md
        └── scripts/
            └── bridge.py
```

## 安全边界

- 不包含任何 API key。
- 不包含私人论文、生成页面或划线日志。
- 不把 HTML 直接连到模型服务。
- 本地安装替换前会自动备份旧版本。
- Codex 目录是 Claude Skill 的软链，两边共用一个源目录。

## 协议

Apache-2.0。详见 `LICENSE` 和 `NOTICE.md`。
