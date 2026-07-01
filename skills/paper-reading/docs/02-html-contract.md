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

## 必需类名

```text
paper-askbar
paper-askbar__form
paper-askbar__input
paper-askbar__button
paper-mark-panel
paper-annotation
paper-question-marker
paper-answer-note
annotation-highlight
svg-text-annotation-highlight
svg-inline-highlight
svg-figure
formula-card
formula-card__label
formula-card__equation
formula-symbol
formula-card__caption
formula-legend
formula-legend__row
formula-card__intuition
term-bridge
concept-visual
```

## 公式组件

核心公式使用独立 `formula-card`，不要只用普通段落解释。建议结构：

```html
<div class="formula-card" aria-label="公式说明">
  <div class="formula-card__label">公式拆解</div>
  <div class="formula-card__equation">
    <span class="formula-symbol">A</span> = <span class="formula-symbol">B</span> / <span class="formula-symbol">C</span>
  </div>
  <p class="formula-card__caption">这条公式在回答什么问题。</p>
  <dl class="formula-legend">
    <div class="formula-legend__row">
      <dt>A</dt>
      <dd>符号含义，以及它在论文机制里扮演什么角色。</dd>
    </div>
  </dl>
  <div class="formula-card__intuition">公式的直觉读法，以及它为什么导向论文的关键动作。</div>
</div>
```

- `formula-card` 用于关键公式；普通 `.formula` 只用于次要短公式或推导片段。
- 每个变量必须有独立解释，不把多个变量挤在一句话里。
- `formula-card__intuition` 要把公式和论文动作接起来，例如成本、吞吐、误差、验证预算或训练目标。
- 公式组件作为正文的一部分，不放进批注侧栏。

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

## SVG 图解规则

- 稍微复杂的内容必须进入 `svg-figure`：机制链、流程、对照、公式关系、调度逻辑、瓶颈链和概念间依赖。
- 概念级小图使用 `svg-figure concept-visual`，图后必须跟 `read-guide`。
- 英文术语解释块使用 `term-bridge`，承接“英译中 / 怎么理解 / 避免误解”。
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
  --log <annotation_requests.jsonl 绝对路径>
```

Bridge 只负责写 JSONL、持久化高亮和插入疑问卡片，不生成解释。

## 浏览器验证

- Codex 修改 HTML 后，刷新当前 Codex 内置浏览器的 localhost 页面。
- 普通刷新读到旧 DOM 时，追加 `_refresh=<timestamp>`。
- 不用外部浏览器或 `file://` 结果替代自动化验证。

## 页面读取对象

页面可暴露通用对象：

```js
window.paperReadingMarks = { load, render, bridgeUrl };
```
