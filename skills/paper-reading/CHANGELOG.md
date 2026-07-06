# Changelog

## v0.2.1 - contract gate and release polish

### P1 稳定性修复

- 修复 `examples/minimal-paper.html` 直接打开时公式可能不可见的问题：最小示例默认显示 `equation-plain` 纯文字回退，KaTeX 成功渲染后再由脚本隐藏。
- 修正 `docs/03-layout-standard.md` 中 `fallback-svg` 的表述：脚本只显示已预填充 SVG，不在浏览器端自动生成公式 SVG。
- 强化 `.npmignore` / `.gitignore` / `package.json.files` 的 Python 缓存排除规则，递归排除 `**/__pycache__/`、`**/*.pyc` 和 pytest 缓存。

### P2 Agent 调用与验收升级

- 修复 `SKILL.md` description 中英文粘连问题。
- 调整 `docs/02-html-contract.md`：将 `paper-askbar` 从“必需类名”拆为“交互增强类名”，避免和最小只读示例冲突。
- `validate_paper_html.py` 新增 `--contract`：检查 `.paper-doc`、`.paper-main`、稳定 `section id`、`.paper-mark-panel`、`.paper-annotation`、`.paper-askbar` 等协作契约。
- `validate_paper_html.py` 新增 `--strict`：warning 也会导致失败退出码，适合发布前 / Agent 最终交付验收。
- smoke test 扩展覆盖 `--contract --strict --json` 和 strict warning 失败行为。

---

## v0.2.0 - stability and Agent routing upgrade

### 必修稳定性修复

- 修复 `validate_paper_html.py` 对已有 `xmlns` 的标准 SVG 误报 `duplicate attribute` 的问题。
- 修复 KaTeX 文档与脚本不一致：浏览器端不再声称自动生成 SVG；脚本只在 `formula-card__fallback-svg` 已预填充时显示 SVG，否则回退到 `equation-plain`。
- installer 增加 Windows / 受限环境兜底：优先 symlink / junction，失败后自动复制到 Codex skill 目录。
- 移除仓库根目录 `SKILL.md`，改为 `PACKAGE.md`，避免用户把仓库根目录误当 Skill 入口。真正入口只有 `skills/paper-reading/SKILL.md`。
- README 同步真实目录结构、安装行为、边界和脚本命令。

### Agent 匹配调用升级

- 重写 `skills/paper-reading/SKILL.md` description，加入适用场景与排除场景。
- 在 `SKILL.md` 增加任务决策树：论文材料、已有 HTML、划线写回、正文重组分别走不同路径。
- 所有脚本命令补充安装后的绝对路径示例：`~/.claude/skills/paper-reading/scripts/...`。
- 新增 `examples/minimal-paper.html`，覆盖公式卡片、标准 `xmlns` SVG、Mermaid、阅读地图、协作区，并通过 validator。
- 新增 `tests/smoke_test.py`，覆盖 installer、validator、bridge。

### 后续优化项落地

- `bridge.py` 增加可选 `--token`，请求需带 `X-Paper-Bridge-Token` 或 `Authorization: Bearer <token>`。
- Mermaid 初始化脚本增加 `window.__paperMermaidRendered` 防重复渲染。
- `formula-card__equation-plain` 的显示/隐藏同步更新 `aria-hidden`，避免无障碍状态和视觉状态不一致。
- validator 增加 `--json` 输出，方便 Agent / CI wrapper 解析。
- `.gitignore` 和 `.npmignore` 增加 Python 缓存排除规则。

---

## fork-enhancement: KaTeX 公式渲染集成

基于 [Agentchengfeng/paper-reading-skills](https://github.com/Agentchengfeng/paper-reading-skills) 原版的公式渲染增强。

### 问题

原版 `formula-card` 的 `equation` 层只用 `<span>` 拼接纯 HTML 文字（如 `A = B / C`），无法渲染论文中真实的数学排版（分式、求和、矩阵、嵌套上下标）。对深度学习、优化理论、统计学等公式密集的论文，公式会退化为难以阅读的文字近似。

### 改进

**1. KaTeX 双层渲染**

公式本体从单层纯文字升级为三层结构：

| 层级 | 元素 | 职责 |
|------|------|------|
| 渲染层 | `.formula-card__equation-rendered[data-katex]` | KaTeX 渲染真正的数学排版 |
| 文字层 | `.formula-card__equation-plain` | Unicode 纯文字回退（无障碍/复制） |
| SVG 回退 | `.formula-card__fallback-svg` | 预渲染 SVG（离线场景） |

KaTeX 可用时显示渲染层，隐藏文字层；KaTeX 不可用（离线/加载失败）时自动退到文字层。

**2. 新增 `docs/04-katex-setup.md`**

完整的 KaTeX 集成技术指南：
- CDN 引入和本地离线引入两种方案
- 自动渲染脚本（含三层回退逻辑）
- KaTeX 支持的 LaTeX 子集速查表
- SVG 预渲染回退方案
- 验证清单

**3. 文档同步更新**

- `01-paper-prompt.md`：公式处理增加 LaTeX 源码要求 + 自检清单新增双层渲染检查
- `02-html-contract.md`：`formula-card` 结构重写，新增 3 个必需类名
- `03-layout-standard.md`：公式版式规则同步双层渲染
- `SKILL.md`：组件清单、资源路由、硬规则同步更新

### 新增必需类名

```text
formula-card__equation-rendered    # KaTeX 渲染层
formula-card__equation-plain       # 纯文字回退层
formula-card__fallback-svg         # SVG 预渲染回退层
```

### 兼容性

- 不修改 `bridge.py`（划线写回逻辑不变）
- 不修改 section id 结构（标记定位不受影响）
- 原 `formula-card__equation` 仍可用（向后兼容），新增的 `__equation-rendered` 和 `__equation-plain` 是子类
- 原 `formula-symbol` 仍用于变量表里的符号高亮

### 致谢

原版 skill 由 **成峰 / AI产品自由** 设计开发，Apache-2.0 协议。本次增强保留原作者信息和原始仓库链接。

---

## 公式关系图（结合 mono-diagram 思路）

### 问题

KaTeX 只渲染**单个公式**。论文里多个公式之间的推导链、变量依赖、损失组合关系，无法用单个 `formula-card` 表达。

### 改进

借鉴 [mono-diagram](https://github.com/techdou/mono-diagram) 的结构化模板思路（architecture/process/compare/matrix），新增**公式关系图**（`svg-figure formula-relation`），专门用于公式间关系的可视化。

### 4 种模板

| 模板 | 用途 | 例子 |
|------|------|------|
| derivation-chain | 推导链 | 交叉熵 → 温度交叉熵 → 蒸馏总损失 |
| variable-dependency | 变量依赖 | Q,K,V → QK^T/√d → softmax → Attention |
| loss-composition | 损失组合 | 总损失 = 重构损失 + KL散度 + 对比损失 |
| formula-compare | 方法对比 | 硬注意力 vs 软注意力 |

### 设计原则

- **与 mono-diagram 分工**：mono-diagram 生成纯黑白可打印图（Word/PDF）；公式关系图用于 HTML 在线阅读，允许颜色。
- **与 formula-card 配合**：`formula-relation` 节点放公式缩写，相邻 `formula-card` 放完整公式。
- **颜色语义统一**：蓝=输入，橙=中间计算，绿+粗框=结果，灰=组成项。
- 每张图必须配 `read-guide`。

### 文件更新

- `04-katex-setup.md`：新增"公式关系图"章节（4 种模板 + 设计规则）
- `02-html-contract.md`：必需类名增加 `formula-relation`；SVG 图解规则增加公式关系图指引
- `01-paper-prompt.md`：公式处理增加"多公式场景"，明确何时用 formula-card vs formula-relation

---

## fork-enhancement: Mermaid UML 图集成

### 问题

公式关系图（手写 SVG）适合表达公式间关系。但论文里还有 UML 标准内容——类继承（空心三角箭头）、接口实现（虚线）、组合（菱形）、调用时序（生命线、激活块）。手写 SVG 还原这些标准符号成本高、易错。

### 改进

**1. 新增 `docs/05-mermaid-diagrams.md`**

Mermaid.js 10.9.1 集成，浏览器端实时渲染 UML 类图与时序图：

- CDN / 本地两种引入方案
- `initPaperMermaid()` 初始化脚本（strict 安全模式 + 中文字体链 + 黑白 themeVariables）
- 回退机制：Mermaid 加载失败时 `<pre class="mermaid">` 源码可读（优于图片回退）
- 类图模板：继承/实现/组合/聚合完整 UML 符号速查
- 时序图模板：同步/异步/激活/注释/循环语法
- 何时用 Mermaid vs 手写 SVG vs KaTeX 的决策表

**2. 关键坑：`<pre>` 内的 `<` 必须转义**

这是 Mermaid + HTML 集成最容易踩的坑。`<pre class="mermaid">` 里的 `<<interface>>`、`<|--`、`<|..` 含 `<` 字符，浏览器 DOM 解析器会把它当成 HTML 标签开始，吃掉后续内容导致 Mermaid Syntax error。正确做法：所有 `<` 写成 `&lt;`。时序图的 `>` 不需要转义。

文档第 1 条设计规则强制要求此转义，符号速查表增加 "`<pre>` 内写法" 列，验证清单增加转义检查项。

**3. 文档同步更新**

- `02-html-contract.md`：必需类名增加 `mermaid-figure`/`uml-class`/`uml-sequence`，新增 UML 图规则段
- `03-layout-standard.md`：版式规则同步 Mermaid 图
- `SKILL.md`：组件清单加 05 文件，路由表加 Mermaid 入口，硬规则同步

---

## fork-enhancement: HTML 质量校验脚本

### 问题

skill 生成的 HTML 缺少自动校验。三类常见错误靠 Agent 自觉避免，但实际频繁踩坑：

- `formula-card` 忘填 `data-katex` 或 `equation-plain`
- SVG 元素超出 viewBox 被裁切
- Mermaid `<pre>` 内的 `<` 未转义

### 改进

**新增 `scripts/validate_paper_html.py`**

零依赖（只用标准库）的 HTML 质量校验脚本，CI 友好（有 error 退出码 1）：

| 校验类 | 检查项 |
|---|---|
| formula-card | 缺 data-katex、data-katex 空/误填 HTML、缺 equation-plain |
| SVG | XML 合法性、元素超出 viewBox、缺 width/height/font-family、非语义色 |
| Mermaid | `<pre>` 内未转义的 `<`（附上下文和修复建议） |

退出码：有 error = 1（CI 失败），只有 warn = 0。每条问题带行号和具体修复建议。

**验证有效性**：测试用例覆盖 6 类错误全部准确抓出（缺 data-katex、误填 HTML、viewBox 裁切、非语义色、Mermaid 未转义、XML 不合法），好文件零误报。
