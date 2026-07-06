---
name: paper-reading
description: "Use when the user asks to interpret a specific research paper, arXiv/technical report, paper repository, or an existing paper-reading HTML. Produces purpose-first paper explanations, structured long-form HTML, formula cards, SVG/Mermaid diagrams, annotation write-back, and body restructuring. Do not use for general literature search, citation verification, ordinary academic writing, or broad topic research unless a concrete paper/material has been provided."
---

# 论文协作阅读

## 原则

- 只定义方法、结构、组件契约和执行边界，不定义某篇论文、模型、系统、指标或实验内容。
- 具体内容必须来自当次论文材料、repo、用户补充或当前 HTML。
- 本 Skill 不负责检索论文、独立解析 PDF 或核验参考文献；当 Agent 已经能读取论文内容、repo 或用户给出的材料时，使用本 Skill 负责解释、重组和生成 HTML。
- `~/.codex/skills/paper-reading` 通常是 `~/.claude/skills/paper-reading` 的软链或 Windows junction；如果权限不允许，安装器会复制一份到 Codex。

## 组件

```text
paper-reading/
├── SKILL.md                         路由规则与硬约束
├── agents/openai.yaml               OpenAI/Codex 侧展示与默认提示
├── docs/01-paper-prompt.md          论文解读方法
├── docs/02-html-contract.md         HTML 协作契约
├── docs/03-layout-standard.md       页面版式标准
├── docs/04-katex-setup.md           KaTeX 公式渲染集成
├── docs/05-mermaid-diagrams.md      Mermaid UML 图集成
├── examples/minimal-paper.html      最小可运行 HTML 示例
└── scripts/
    ├── bridge.py                    本地标记写回脚本
    └── validate_paper_html.py       HTML 质量校验脚本
```

## 来源与协议

- 官方来源：`https://github.com/Agentchengfeng/paper-reading-skills`
- 作者：`成峰 / AI产品自由`
- 协议：Apache-2.0；复制、改造或二次发布时保留 `LICENSE` 和 `NOTICE.md`。

## 任务决策树

```text
用户给论文 PDF / repo / 技术报告 / 论文资料包
  -> 先读 docs/01-paper-prompt.md
  -> 若输出 HTML，再读 docs/03-layout-standard.md + docs/02-html-contract.md
  -> 若涉及核心公式，再读 docs/04-katex-setup.md
  -> 若涉及类继承、接口实现或调用时序，再读 docs/05-mermaid-diagrams.md
  -> 交付前运行 validate_paper_html.py

用户给已有 paper-reading HTML
  -> 先读 docs/02-html-contract.md
  -> 若是版式或阅读体验问题，再读 docs/03-layout-standard.md
  -> 若是公式问题，再读 docs/04-katex-setup.md
  -> 若是 Mermaid / UML 问题，再读 docs/05-mermaid-diagrams.md
  -> 修改后运行 validate_paper_html.py

用户要求划线、标记、补充解释、作图理解
  -> 读 docs/02-html-contract.md
  -> 启动 scripts/bridge.py 写回标记
  -> bridge 只写 JSONL 和 HTML 标记，不生成解释
  -> Agent 读取标记后再补解释、图解或正文重组

用户要求“重组 / 整合 / 合并到正文 / 改成新段落”
  -> 将批注解释融入正文
  -> 删除对应疑问卡片和解释块
  -> 有价值的 SVG / formula-card 保留为普通正文内容
```

## 资源路由

- 从论文或 repo 生成/重写正文：读 `docs/01-paper-prompt.md`。
- 创建、修复或优化论文 HTML：读 `docs/03-layout-standard.md`，再读 `docs/02-html-contract.md`。
- 渲染数学公式（分式/求和/矩阵）：读 `docs/04-katex-setup.md`，按 KaTeX 双层渲染生成 `formula-card`。
- 表达类继承、接口实现、模块结构或调用时序：读 `docs/05-mermaid-diagrams.md`，用 Mermaid 生成 UML 类图/时序图。
- 处理划线标记、补充解释、作图或正文重组：读 `docs/02-html-contract.md`。
- 启动本地标记写回：运行安装路径下的 `scripts/bridge.py`，不要重写 bridge 逻辑。
- 校验生成的 HTML 质量：运行安装路径下的 `scripts/validate_paper_html.py`，在交付前抓出 formula-card 缺 data-katex、SVG 元素超出 viewBox、Mermaid `<` 未转义等问题。

## 脚本命令

从任意用户项目目录运行时，优先使用安装后的绝对路径：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py dist/ --recursive
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --json
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --contract
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --contract --strict --json

python3 ~/.claude/skills/paper-reading/scripts/bridge.py \
  --page /absolute/path/to/paper-reading.html \
  --log /absolute/path/to/paper_annotation_requests.jsonl \
  --token local-random-token
```

如果当前工作目录正好是 Skill 根目录，也可以使用相对路径：

```bash
python3 scripts/validate_paper_html.py examples/minimal-paper.html
python3 scripts/bridge.py --page /absolute/path/to/paper.html --log paper_annotation_requests.jsonl
```

## 硬规则

- 解读开头先写研究目的，再写核心结论。
- 页面左侧使用内容阅读地图，不做机械章节目录。
- 稍微复杂的内容默认用 SVG 图解：机制链、流程、对照、公式关系、调度逻辑、瓶颈链和概念间依赖，不能只靠长段文字解释。
- 核心公式使用 KaTeX 双层渲染：`data-katex` 放 LaTeX 源码，`equation-plain` 放 Unicode 纯文字回退；KaTeX 不可用时显示预渲染 SVG 回退或纯文字回退。详见 `docs/04-katex-setup.md`。
- 类继承/接口实现/调用时序使用 Mermaid UML 图：`<pre class="mermaid">` 放源码，Mermaid.js 浏览器端渲染；需要 UML 标准符号（空心三角、菱形、生命线）时用 Mermaid 而非手写 SVG。详见 `docs/05-mermaid-diagrams.md`。
- 划线协作只保留三类动作：`名词讲解`、`逻辑梳理`、`作图理解`。
- 用户说 `重组`、`整合`、`合并到正文`、`改成新段落` 时，把批注内容融入正文，删除对应疑问卡片和解释块；有用 SVG 保留为普通正文图。
- 本地 HTML 的刷新、DOM 检查和交互验证默认使用 Codex 内置浏览器；验证 URL 使用 localhost，不用 `file://` 代替。
- 交付 HTML 前必须至少运行一次 validator；需要机器解析时使用 `--json`；需要检查协作页面契约时使用 `--contract`；发布/最终交付验收使用 `--contract --strict`。

## 边界

- HTML 不放 API key，不直接调用模型。
- Bridge 只接收标记、写 JSONL、改 HTML；不生成解释。
- Bridge 建议使用 `--token`；页面请求需带 `X-Paper-Bridge-Token` 或 `Authorization: Bearer <token>`。
- 允许保留通过 validator 的最小示例和 smoke test；不要新增未验证模板、运行时解释层或伪示例。
