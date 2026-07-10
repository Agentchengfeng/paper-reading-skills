# paper-reading-skills

> 给 Claude Code / Codex 使用的论文协作阅读 Skill。

这个项目把论文解读流程做成了一个可安装 Skill：先抓论文目的，再拆问题链、机制链和证据链，最后输出文档式 HTML 长文。复杂概念默认用 SVG / Mermaid 图解，核心公式用 KaTeX + 纯文字回退，阅读过程中可以划线提问，再通过本地 bridge 把问题写回 HTML。

它**不是论文搜索工具，也不是独立 PDF 解析器**。更准确的边界是：当 Agent 已经能读取用户给出的论文 PDF、论文 repo、技术报告、Markdown、摘录文本或已有 HTML 时，本 Skill 负责把材料讲清楚、结构化、图解化，并维护可继续追问的 HTML 协作文档。

这个仓库只包含可复用的 Skill 指令、HTML 协作约定、示例、测试和脚本，不包含论文 PDF、生成后的 HTML、划线日志、API key 或私人工作区内容。

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
2. 把 `~/.codex/skills/paper-reading` 镜像到同一个 Skill：优先软链 / Windows junction；权限不允许时自动复制，保证 Codex 侧可用。
3. 替换旧版本前自动备份。
4. 把 `LICENSE`、`NOTICE.md`、`CITATION.cff` 一起复制进安装目录。
5. 检查 `python3` 是否可用，因为本地划线协作 bridge 和 validator 需要它。

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

处理已有 HTML：

```text
用 paper-reading 检查并优化这个论文阅读 HTML，修复公式、SVG、Mermaid 和划线协作结构。
```

## Agent 触发边界

适合触发：

```text
具体论文 / arXiv PDF / 技术报告 / 论文 repo / 已有 paper-reading HTML
  -> 目的优先解读
  -> 文档式 HTML
  -> 公式卡片
  -> SVG / Mermaid 图解
  -> 划线写回和正文重组
```

不适合触发：

```text
泛泛的论文搜索
参考文献真实性核验
没有具体材料的选题调研
普通论文润色 / 普通学术写作
通用 PDF 阅读任务
```

## 常用脚本

从任意项目目录运行时，建议使用安装后的绝对路径。

校验单个 HTML：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html
```

批量校验目录：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py dist/ --recursive
```

输出机器可读 JSON，方便 Agent / CI wrapper 解析：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --json
```

检查 paper-reading HTML 协作契约，包括 `.paper-doc`、`.paper-main`、稳定 section id、mark panel 和 askbar：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --contract
```

发布 / 最终交付前的严格验收：检查契约，并把 warning 也作为失败退出码：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --contract --strict --json
```

本仓库内置最小示例，可直接校验，且可通过最严格验收：

```bash
python3 skills/paper-reading/scripts/validate_paper_html.py \
  skills/paper-reading/examples/minimal-paper.html --contract --strict
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
  --log /absolute/path/to/paper_annotation_requests.jsonl \
  --token local-random-token
```

bridge 默认监听：

```text
127.0.0.1:8766
```

配置 `--token` 后，页面请求需要带：

```http
X-Paper-Bridge-Token: local-random-token
```

或者：

```http
Authorization: Bearer local-random-token
```

Bridge 只做本地写回：接收标记、写 JSONL、修改 HTML。它不调用模型，也不保存 API key。

### 撤销划线（bridge undo）

划线写错时，可以撤销最近一条或指定一条：

```bash
# 撤销最近一条
curl -X DELETE -H "X-Paper-Bridge-Token: local-random-token" \
  http://127.0.0.1:8766/__paper_undo

# 撤销指定 mark_id 的一条
curl -X DELETE -H "X-Paper-Bridge-Token: local-random-token" \
  "http://127.0.0.1:8766/__paper_undo?id=mark-1700000000-123"
```

撤销会同时：

1. 从 JSONL 删除对应记录；
2. 从 HTML 删除对应的 `<aside>` 疑问卡片；
3. 把高亮 `<span>` 还原为纯文本（处理嵌套 span）；
4. 清理 SVG 文本上的高亮标记。

HTML 端建议提供"撤销最近一次"按钮调用此接口，撤销成功后刷新页面查看高亮还原。

## 工作流

```text
论文 / repo / PDF / 技术报告
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
长文解释 + formula-card + SVG / Mermaid 图解 + 可划线追问
    |
    v
运行 validator
修复公式、SVG、Mermaid、回退层和 HTML 协作契约问题
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
├── PACKAGE.md                         # 包说明；不要把仓库根目录当 Skill
├── LICENSE
├── NOTICE.md
├── CITATION.cff
├── package.json
├── bin/
│   └── install.js                     # 安装 / doctor / uninstall
├── tests/
│   └── smoke_test.py                  # installer / validator / bridge smoke test
└── skills/
    └── paper-reading/
        ├── SKILL.md                   # 真正的 Skill 入口
        ├── CHANGELOG.md
        ├── agents/
        │   └── openai.yaml
        ├── docs/
        │   ├── 01-paper-prompt.md
        │   ├── 02-html-contract.md
        │   ├── 03-layout-standard.md
        │   ├── 04-katex-setup.md
        │   └── 05-mermaid-diagrams.md
        ├── examples/
        │   └── minimal-paper.html
        └── scripts/
            ├── bridge.py
            └── validate_paper_html.py
```

## 根目录 `PACKAGE.md` 与 Skill 入口

根目录不再保留 `SKILL.md`，避免用户把整个仓库拷贝到 skills 目录后被 Agent 误索引。

真正的 Skill 入口只有：

```text
skills/paper-reading/SKILL.md
```

手动安装时，只复制 `skills/paper-reading/`，不要复制整个仓库根目录。

## 测试

运行 smoke test：

```bash
python3 tests/smoke_test.py
```

覆盖：

- installer 安装与 doctor 检查；
- validator 对最小示例、标准 `xmlns` SVG、`--json`、`--contract` 和 `--strict` 输出的检查；
- bridge token 写回、日志写入和 HTML 标记插入。

## 安全边界

- 不包含任何 API key。
- 不包含私人论文、生成页面或划线日志。
- 不把 HTML 直接连到模型服务。
- 本地安装替换前会自动备份旧版本。
- Codex 目录优先软链 / junction 到 Claude Skill；不支持时自动复制。
- Bridge 建议使用 `--token`，降低本地写回接口被其他网页误用的风险。
- 最小示例中的公式纯文字回退默认可见，保证直接打开 HTML 或 KaTeX 不可用时也能阅读公式。

## 协议

Apache-2.0。详见 `LICENSE` 和 `NOTICE.md`。
