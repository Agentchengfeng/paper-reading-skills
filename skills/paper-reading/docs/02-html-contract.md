<!--
input: 论文解读 HTML 的创建、修复、协作标记或正文重组任务
output: HTML 结构、协作组件和 bridge 契约
pos: paper-reading 的 HTML 协作契约
-->

# HTML 协作契约

## 结构

```text
paper-doc
├── paper-sidebar      内容阅读地图
└── paper-main         正文长文
    ├── section#thesis
    ├── section#concepts
    ├── section#problem-chain
    ├── section#mechanism
    ├── section#evidence
    ├── section#limits
    ├── section#sources
    └── section#paper-mark-panel
```

稳定 `section id` 用于写回标记和刷新定位；入口文案按当次论文生成。

## 核心类名与交互增强类名

核心结构类名用于页面识别、正文定位和 bridge 写回，生成完整 paper-reading HTML 时应优先保留：

```text
paper-doc
paper-sidebar
paper-main
paper-mark-panel
paper-annotation
paper-question-marker
paper-answer-note
annotation-highlight
svg-text-annotation-highlight
svg-inline-highlight
svg-figure
formula-relation
mermaid-figure
uml-class
uml-sequence
formula-card
formula-card__label
formula-card__equation
formula-card__equation-rendered
formula-card__equation-plain
formula-card__fallback-svg
formula-symbol
formula-card__caption
formula-legend
formula-legend__row
formula-card__intuition
term-bridge
concept-visual
```

交互增强类名用于页面内追问输入区。最小只读示例可以省略；需要用户在 HTML 内继续提问、记录请求或联动 bridge 时应完整提供：

```text
paper-askbar
paper-askbar__form
paper-askbar__input
paper-askbar__button
```

## 公式组件（KaTeX 双层渲染）

核心公式使用独立 `formula-card`，不要只用普通段落解释。

公式本体采用**双层渲染**：优先用 KaTeX 渲染真正的数学排版（分式、求和、矩阵、上下标），同时保留纯文字回退层用于无障碍访问和复制粘贴。当 KaTeX 不可用时（离线且无本地库），优先显示可选的预渲染 SVG 回退，否则显示纯文字回退。脚本不会在浏览器端自动生成 SVG；`formula-card__fallback-svg` 需要预先填充。详见 `docs/04-katex-setup.md`。

### 标准结构

```html
<div class="formula-card" aria-label="公式说明">
  <div class="formula-card__label">公式拆解</div>

  <!-- 第一层：KaTeX 渲染的数学排版 -->
  <div class="formula-card__equation formula-card__equation-rendered"
       data-katex="\alpha_{i,m}=\frac{\exp(z_{i,m})}{\sum_{m'}\exp(z_{i,m'})}">
  </div>

  <!-- 第二层：纯文字回退（无障碍 / 屏幕阅读器 / 复制粘贴） -->
  <div class="formula-card__equation formula-card__equation-plain"
       aria-label="公式纯文字回退" aria-hidden="false">
    α(i,m) = exp(z(i,m)) / Σ(m') exp(z(i,m'))
  </div>

  <!-- 可选：预渲染 SVG 回退层。KaTeX 加载失败时 JS 只负责显示它，不负责生成 SVG。 -->
  <div class="formula-card__fallback-svg" data-katex-fallback="true" hidden></div>

  <p class="formula-card__caption">这条公式在回答什么问题。</p>
  <dl class="formula-legend">
    <div class="formula-legend__row">
      <dt><span class="formula-symbol">α(i,m)</span></dt>
      <dd>路由权重，越大表示该模态被选中的概率越高。</dd>
    </div>
    <div class="formula-legend__row">
      <dt><span class="formula-symbol">z(i,m)</span></dt>
      <dd>路由 logit，是路由网络对第 i 个样本第 m 个模态的打分。</dd>
    </div>
  </dl>
  <div class="formula-card__intuition">公式的直觉读法，以及它为什么导向论文的关键动作。</div>
</div>
```

### 渲染层级与回退顺序

```text
1. KaTeX 可用（CDN 或本地）
   → 渲染 data-katex 里的 LaTeX，显示真正的分式/求和/矩阵
   → 隐藏 equation-plain

2. KaTeX 不可用，但存在预渲染 `formula-card__fallback-svg`
   → 显示 fallback-svg
   → 隐藏 equation-rendered 和 equation-plain

3. 没有预渲染 SVG
   → 显示 equation-plain 纯文字版
   → 至少保证可读性
```

### 生成规则

- **`data-katex` 必须填 LaTeX 源码**，不是渲染后的 HTML。例如 `\frac{a}{b}` 而不是 `<frac>a</frac>`。
- LaTeX 只用 KaTeX 支持的子集：分式 `\frac`、求和 `\sum`、积分 `\int`、矩阵 `\begin{pmatrix}`、上下标 `^{}` `_{}`、希腊字母 `\alpha` 等。不要用 `\begin{equation}`、`\section` 等文档级命令。
- **`equation-plain` 必须手写纯文字版**，用 Unicode 符号近似（α、Σ、√、≤），不要留空。这一层用于屏幕阅读器和复制粘贴。建议默认可见；KaTeX 成功渲染后再由脚本隐藏它，这样 HTML 直接打开或 JS 失败时公式也可见。
- `formula-card` 用于关键公式；普通 `.formula` 只用于次要短公式或推导片段，可只用 `equation-plain` 不需要完整双层。
- 每个变量必须有独立解释，不把多个变量挤在一句话里。
- `formula-card__intuition` 要把公式和论文动作接起来，例如成本、吞吐、误差、验证预算或训练目标。
- 公式组件作为正文的一部分，不放进批注侧栏。
- 行内短公式可用 `<span class="formula" data-katex="...">文字回退</span>`，KaTeX 加载后自动替换为渲染版。

## 标记语义

```text
term     名词讲解
logic    逻辑梳理
diagram  作图理解
```

标记对象至少包含：

```json
{
  "id": "mark-id",
  "anchorId": "paper-anchor-mark-id",
  "kind": "logic",
  "text": "selected text",
  "anchorText": "containing block text",
  "question": "user supplement",
  "sectionId": "section id",
  "sectionTitle": "section title",
  "pageTitle": "page title",
  "url": "page url",
  "createdAt": "ISO time"
}
```

## 写回规则

- `paper-question-marker` 只显示动作按钮和用户补充，不重复原文、章节或时间。
- 文字解释写入同一 `paper-annotation` 内的 `paper-answer-note`。
- 作图解释写入相邻 `svg-figure`，并附“这张图怎么读”。
- 如果用户要求解释核心公式，优先重写或新增 `formula-card`，而不是新增普通批注段。
- 普通正文选区使用 `annotation-highlight`；SVG `<text>` 选区使用 `svg-text-annotation-highlight`，图内精确标记优先用 `svg-inline-highlight` 做红色底部虚线；必要时退化为整张图或图内卡片的可见描边。
- 已补过的标记不重复插入。
- 用户要求重组时，把标记、解释和原文改写成新正文，删除对应批注块；有用图保留为普通正文图。

## Mermaid UML 图规则

- 类继承、接口实现、聚合组合关系使用 `mermaid-figure uml-class`。
- 对象调用时序、前向传播流程、训练循环使用 `mermaid-figure uml-sequence`。
- 模板和规则详见 `docs/05-mermaid-diagrams.md`。
- **UML vs SVG 判断**：需要 UML 标准符号（`+/-/#`、空心三角、菱形、生命线）用 Mermaid；只是流程/对照/公式关系用手写 `svg-figure`。
- `mermaid-figure` 内的 `<pre class="mermaid">` 放 Mermaid 源码；图后必须跟 `read-guide`。
- Mermaid 源码失败时可读，因此不需要额外的纯文字回退层（与 KaTeX 的 `equation-plain` 不同）。

## SVG 图解规则

- 稍微复杂的内容必须进入 `svg-figure`：机制链、流程、对照、公式关系、调度逻辑、瓶颈链和概念间依赖。
- 概念级小图使用 `svg-figure concept-visual`，图后必须跟 `read-guide`。
- **公式之间的关系**使用 `svg-figure formula-relation`：推导链、变量依赖、损失组合、方法对比。模板和规则详见 `docs/04-katex-setup.md` 的”公式关系图”章节。单个公式用 `formula-card` + KaTeX，多个公式的关系用 `formula-relation`。
- 英文术语解释块使用 `term-bridge`，承接”英译中 / 怎么理解 / 避免误解”。
- SVG 内只放短标签和箭头关系；完整解释放在正文段落或 `read-guide` 中。
- 作图解释写回时，优先复用或新增相邻 SVG，而不是只新增文字批注。

## Bridge

默认接口：

```text
POST http://127.0.0.1:8766/__paper_annotation
GET  http://127.0.0.1:8766/healthz
GET  http://127.0.0.1:8766/requests
```

启动：

```bash
python3 ~/.claude/skills/paper-reading/scripts/bridge.py \
  --page <HTML 绝对路径> \
  --log <annotation_requests.jsonl 绝对路径> \
  --token <local-random-token>
```

Bridge 只负责写 JSONL、持久化高亮和插入疑问卡片，不生成解释。使用 `--token` 后，页面请求必须带 `X-Paper-Bridge-Token: <token>` 或 `Authorization: Bearer <token>`。

## 浏览器验证

- Codex 修改 HTML 后，刷新当前 Codex 内置浏览器的 localhost 页面。
- 普通刷新读到旧 DOM 时，追加 `_refresh=<timestamp>`。
- 不用外部浏览器或 `file://` 结果替代自动化验证。
- 交付前运行质量校验脚本：

```bash
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html
# 或批量校验整个目录
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py dist/ --recursive
# Agent / CI wrapper 需要机器解析时
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --json
# 检查 paper-reading HTML 协作契约
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --contract
# 最严格验收：检查契约，并把 warning 也当作失败
python3 ~/.claude/skills/paper-reading/scripts/validate_paper_html.py paper.html --contract --strict --json
```

默认校验三类组件问题：
- `formula-card` 缺 `data-katex`（LaTeX 源码）或缺 `equation-plain`（纯文字回退）
- SVG 元素超出 viewBox（会被裁切）、XML 不合法、缺必备属性、用了非语义色
- `<pre class="mermaid">` 内有未转义的 `<`（浏览器会当成 HTML 标签吃掉，导致 Mermaid Syntax error）

`--contract` 额外校验页面协作契约：`.paper-doc`、`.paper-main`、稳定 `section id`、`.paper-mark-panel`、`.paper-annotation`、`.paper-askbar` 等结构是否完整。

退出码：默认有 error 返回 1，只有 warn 返回 0；`--strict` 模式下 warning 也返回 1。脚本零依赖，只用标准库。

## 页面读取对象

页面可暴露通用对象：

```js
window.paperReadingMarks = { load, render, bridgeUrl };
```
