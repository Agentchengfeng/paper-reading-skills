<!--
input: 论文解读 HTML 需要渲染数学公式时
output: KaTeX 集成方案、CDN/本地引入、自动渲染脚本、预渲染 SVG 回退、离线策略
pos: paper-reading 的公式渲染技术指南
-->

# KaTeX 公式渲染集成

## 为什么用 KaTeX

论文公式不能只用纯 HTML 文字。KaTeX 是最快的数学排版引擎（比 MathJax 快 100 倍），支持分式、求和、矩阵、上下标嵌套，CDN 引入一行即可用，离线也可下载到本地。

## HTML head 引入

### 方案 A：CDN（默认，最简）

在 HTML 的 `<head>` 里加入：

```html
<!-- KaTeX CSS -->
<link rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
      crossorigin="anonymous">

<!-- KaTeX JS（放在 body 末尾或 defer） -->
<script defer
        src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
        crossorigin="anonymous"></script>

<!-- auto-render 扩展（自动扫描 data-katex 属性） -->
<script defer
        src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
        crossorigin="anonymous"
        onload="renderPaperFormulas()"></script>
```

### 方案 B：本地（离线优先）

当目标 HTML 需要离线打开（`file://` 或内网），把 KaTeX 下载到项目本地：

```text
论文项目/
├── index.html
└── assets/
    └── katex/
        ├── katex.min.css
        ├── katex.min.js
        └── contrib/
            └── auto-render.min.js
```

```html
<link rel="stylesheet" href="assets/katex/katex.min.css">
<script defer src="assets/katex/katex.min.js"></script>
<script defer src="assets/katex/contrib/auto-render.min.js"
        onload="renderPaperFormulas()"></script>
```

下载地址：`https://github.com/KaTeX/KaTeX/releases`

## 自动渲染脚本

在 HTML `<body>` 末尾加入这段脚本。它会扫描所有 `data-katex` 属性，用 KaTeX 渲染，并处理“KaTeX → 预渲染 SVG → 纯文字”的回退：

```html
<script>
function showFormulaFallback(card, renderedEl) {
  var plain = card ? card.querySelector('.formula-card__equation-plain') : null;
  var svgFallback = card ? card.querySelector('.formula-card__fallback-svg') : null;
  var hasSvgFallback = svgFallback && svgFallback.textContent.trim().length > 0;

  if (renderedEl) renderedEl.hidden = true;

  if (hasSvgFallback) {
    svgFallback.hidden = false;
    svgFallback.setAttribute('aria-hidden', 'false');
    if (plain) {
      plain.hidden = true;
      plain.setAttribute('aria-hidden', 'true');
    }
    return;
  }

  if (plain) {
    plain.hidden = false;
    plain.setAttribute('aria-hidden', 'false');
  }
}

function renderPaperFormulas() {
  if (window.__paperFormulasRendered) return;
  window.__paperFormulasRendered = true;

  if (typeof katex === 'undefined') {
    document.querySelectorAll('.formula-card').forEach(function(card) {
      var rendered = card.querySelector('.formula-card__equation-rendered');
      showFormulaFallback(card, rendered);
    });
    console.warn('KaTeX not loaded, using SVG/plain text fallback');
    return;
  }

  document.querySelectorAll('[data-katex]').forEach(function(el) {
    var latex = el.getAttribute('data-katex') || '';
    try {
      var displayMode = el.classList.contains('formula-card__equation-rendered');
      katex.render(latex, el, {
        displayMode: displayMode,
        throwOnError: false,
        output: 'htmlAndMathml'
      });
      var card = el.closest('.formula-card');
      if (card) {
        var plain = card.querySelector('.formula-card__equation-plain');
        var svgFallback = card.querySelector('.formula-card__fallback-svg');
        if (plain) {
          plain.hidden = true;
          plain.setAttribute('aria-hidden', 'true');
        }
        if (svgFallback) {
          svgFallback.hidden = true;
          svgFallback.setAttribute('aria-hidden', 'true');
        }
      }
    } catch (err) {
      console.warn('KaTeX render failed for:', latex, err);
      showFormulaFallback(el.closest('.formula-card'), el);
    }
  });

  document.querySelectorAll('span.formula[data-katex]').forEach(function(el) {
    var latex = el.getAttribute('data-katex') || '';
    var fallback = el.textContent;
    try {
      katex.render(latex, el, { displayMode: false, throwOnError: false });
    } catch (err) {
      el.textContent = fallback;
    }
  });
}

window.addEventListener('DOMContentLoaded', function() {
  if (typeof renderPaperFormulas === 'function') {
    renderPaperFormulas();
  }
});
</script>
```

## 三层回退机制

```text
层级 1：KaTeX 渲染（data-katex → 数学排版）
  ↓ KaTeX 未加载或渲染失败
层级 2：预渲染 SVG（如果 formula-card__fallback-svg 已经填充）
  ↓ 没有预渲染 SVG
层级 3：equation-plain 纯文字（Unicode 近似，始终可用）
```

### 各层职责

| 层级 | 元素 | 显示条件 | 内容 |
|------|------|---------|------|
| 渲染层 | `.formula-card__equation-rendered` | KaTeX 可用 | KaTeX 生成的 HTML |
| 文字层 | `.formula-card__equation-plain` | KaTeX 不可用 / 失败 | Unicode 纯文字 |
| SVG 回退 | `.formula-card__fallback-svg` | KaTeX 失败且该层已预填充 | 预生成的 SVG |

### 回退触发时机

- **CDN 不可达**：离线打开 `file://` 且无本地 KaTeX → 显示 plain
- **LaTeX 语法错误**：`data-katex` 里的 LaTeX 有问题 → 该公式退到 plain
- **KaTeX JS 加载失败**：网络阻断 → 全部公式退到 plain

## SVG 预渲染回退（可选）

当目标环境明确无法加载 KaTeX（如某些企业内网），可以预先生成 SVG 嵌入 `fallback-svg`：

```html
<div class="formula-card__fallback-svg" data-katex-fallback="true">
  <svg viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
    <!-- 预渲染的公式 SVG -->
  </svg>
</div>
```

生成方式：
- `latex2svg`（Node.js）：`npx latex2svg "\\frac{a}{b}" > formula.svg`
- `matplotlib`（Python）：`matplotlib.pyplot.text` + `mathtext` + 导出 SVG
- `Pandoc` + `--mathml`：转 MathML 后浏览器渲染

SVG 回退层默认 `hidden`，只有 KaTeX 失败且该层已经有内容时才显示。脚本不会在浏览器端把 LaTeX 自动转换成 SVG。

## KaTeX 支持的 LaTeX 子集

| 支持 | 示例 |
|------|------|
| 分式 | `\frac{a}{b}` |
| 求和/积分 | `\sum_{i=1}^{n}`, `\int_0^{\infty}` |
| 矩阵 | `\begin{pmatrix} a & b \\\\ c & d \end{pmatrix}` |
| 上下标 | `x^{2}`, `\alpha_{i}` |
| 希腊字母 | `\alpha \beta \gamma \Sigma \Pi` |
| 根号 | `\sqrt{x}`, `\sqrt[3]{x}` |
| 极限 | `\lim_{x \to 0}` |
| 多行对齐 | `\begin{aligned} ... \end{aligned}` |
| 文字标注 | `\text{when}`, `\underbrace{...}_{\text{label}}` |

**不支持**：`\begin{equation}`、`\section`、`\label`、`\ref`、`\cite`、TikZ、`minipage`、自定义 `\newcommand`（用 `\def` 或展开后再写入 `data-katex`）。

## 验证清单

生成 HTML 后检查：

- [ ] 每个 `formula-card` 有 `data-katex` 属性且值为合法 LaTeX
- [ ] 每个 `formula-card` 有 `equation-plain` 纯文字版（非空）
- [ ] KaTeX CSS 和 JS 已引入（CDN 或本地）
- [ ] `renderPaperFormulas()` 脚本在 body 末尾
- [ ] 断网测试：KaTeX CDN 不可达时，预渲染 SVG 或 plain 层正常显示
- [ ] 复杂公式（矩阵、嵌套分式）在 KaTeX 下渲染正确
- [ ] 行内短公式 `span.formula[data-katex]` 也能渲染

## 公式关系图（Formula Relationship Diagrams）

KaTeX 渲染**单个公式**的数学排版。但论文经常需要表达**多个公式之间的关系**——推导链、变量依赖、损失函数组合。这是 KaTeX 做不了的，需要用 `svg-figure` 结构化图表表达。

这部分借鉴 [mono-diagram](https://github.com/techdou/mono-diagram) 的结构化模板思路（architecture/process/compare/matrix），适配为 HTML 彩色环境，专门用于公式关系可视化。

### 何时用 KaTeX vs 公式关系图

| 场景 | 工具 |
|------|------|
| 单个公式的数学排版 | `formula-card` + KaTeX |
| 2 个以上公式的推导顺序 | 公式关系图（`svg-figure formula-relation`） |
| 变量在多个公式间的流动关系 | 公式关系图 |
| 损失函数的组合结构（总损失 = 各项之和） | 公式关系图 |
| 两种方法的公式对比 | 公式关系图（对照型） |

### 4 种公式关系图模板

#### 模板 1：推导链（derivation-chain）

表达"A → B → C"的推导顺序，每个节点是一个公式缩写，箭头标注推导依据。

```html
<svg class="svg-figure formula-relation" width="800" height="120" viewBox="0 0 800 120" font-family="'-apple-system','Segoe UI','PingFang SC','Microsoft YaHei','SimHei','Noto Sans CJK SC',sans-serif" aria-label="推导链">
  <rect x="0" y="0" width="800" height="120" fill="#ffffff"/>
  <!-- 节点 1 -->
  <rect x="20" y="30" width="160" height="60" rx="8" fill="#f8f9fa" stroke="#333" stroke-width="1.5"/>
  <text x="100" y="60" text-anchor="middle" font-size="14">交叉熵</text>
  <text x="100" y="78" text-anchor="middle" font-size="11" fill="#666">L_CE = -Σ y log(p)</text>

  <!-- 箭头 + 标注 -->
  <line x1="185" y1="60" x2="235" y2="60" stroke="#333" stroke-width="1.5" marker-end="url(#arrow)"/>
  <text x="210" y="50" text-anchor="middle" font-size="10" fill="#888">加温度</text>

  <!-- 节点 2 -->
  <rect x="240" y="30" width="160" height="60" rx="8" fill="#f8f9fa" stroke="#333" stroke-width="1.5"/>
  <text x="320" y="60" text-anchor="middle" font-size="14">温度交叉熵</text>
  <text x="320" y="78" text-anchor="middle" font-size="11" fill="#666">L_T = -Σ y log(softmax(z/T))</text>

  <!-- 箭头 -->
  <line x1="405" y1="60" x2="455" y2="60" stroke="#333" stroke-width="1.5" marker-end="url(#arrow)"/>
  <text x="430" y="50" text-anchor="middle" font-size="10" fill="#888">蒸馏</text>

  <!-- 节点 3 -->
  <rect x="460" y="30" width="160" height="60" rx="8" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2"/>
  <text x="540" y="60" text-anchor="middle" font-size="14">总蒸馏损失</text>
  <text x="540" y="78" text-anchor="middle" font-size="11" fill="#666">L = αL_T + (1-α)L_CE</text>

  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="6" refX="7" refY="3" orient="auto">
      <path d="M0,0 L8,3 L0,6 Z" fill="#333"/>
    </marker>
  </defs>

</svg>
<p class="read-guide">读法：从左到右是推导顺序。基础交叉熵加温度参数后得到温度交叉熵，再与原始损失加权组合成蒸馏总损失。绿色框是最终目标。</p>
```

适用场景：论文的核心推导链、损失函数的演化、训练目标的组合过程。

#### 模板 2：变量依赖图（variable-dependency）

表达"哪些变量影响哪些结果"，类似计算图，但聚焦公式层面的变量关系。

```html
<svg class="svg-figure formula-relation" width="600" height="260" viewBox="0 0 600 260" font-family="'-apple-system','Segoe UI','PingFang SC','Microsoft YaHei','SimHei','Noto Sans CJK SC',sans-serif" aria-label="变量依赖">
  <rect x="0" y="0" width="600" height="260" fill="#ffffff"/>
  <!-- 输入层 -->
  <circle cx="80" cy="60" r="30" fill="#e3f2fd" stroke="#1565c0" stroke-width="1.5"/>
  <text x="80" y="65" text-anchor="middle" font-size="13">Q</text>

  <circle cx="80" cy="140" r="30" fill="#e3f2fd" stroke="#1565c0" stroke-width="1.5"/>
  <text x="80" y="145" text-anchor="middle" font-size="13">K</text>

  <circle cx="80" cy="220" r="30" fill="#e3f2fd" stroke="#1565c0" stroke-width="1.5"/>
  <text x="80" y="225" text-anchor="middle" font-size="13">V</text>

  <!-- 中间计算 -->
  <rect x="220" y="45" width="120" height="40" rx="6" fill="#fff3e0" stroke="#e65100" stroke-width="1.5"/>
  <text x="280" y="70" text-anchor="middle" font-size="12">QK^T / √d_k</text>

  <!-- 连线 -->
  <line x1="110" y1="60" x2="215" y2="60" stroke="#999" stroke-width="1"/>
  <line x1="110" y1="140" x2="215" y2="65" stroke="#999" stroke-width="1"/>

  <line x1="345" y1="65" x2="420" y2="100" stroke="#999" stroke-width="1"/>
  <text x="380" y="75" text-anchor="middle" font-size="10" fill="#888">softmax</text>

  <!-- 输出 -->
  <rect x="420" y="80" width="120" height="40" rx="6" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2"/>
  <text x="480" y="105" text-anchor="middle" font-size="12">Attention(Q,K,V)</text>

  <line x1="110" y1="220" x2="475" y2="125" stroke="#999" stroke-width="1" stroke-dasharray="4,3"/>
  <text x="280" y="185" text-anchor="middle" font-size="10" fill="#888">直接相乘</text>

</svg>
<p class="read-guide">读法：Q 和 K 先做点积并缩放，经过 softmax 得到注意力权重，再与 V 相乘得到最终输出。虚线表示 V 直接参与最终计算，不经过 softmax。</p>
```

适用场景：Attention 计算图、前向传播的变量流、梯度回传路径。

#### 模板 3：损失组合图（loss-composition）

表达"总损失 = 各项之和"，用堆叠/分支结构展示损失的组成。

```html
<svg class="svg-figure formula-relation" width="700" height="160" viewBox="0 0 700 160" font-family="'-apple-system','Segoe UI','PingFang SC','Microsoft YaHei','SimHei','Noto Sans CJK SC',sans-serif" aria-label="损失组合">
  <rect x="0" y="0" width="700" height="160" fill="#ffffff"/>
  <!-- 总损失 -->
  <rect x="280" y="20" width="140" height="50" rx="8" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2.5"/>
  <text x="350" y="45" text-anchor="middle" font-size="14" font-weight="bold">总损失 L</text>
  <text x="350" y="62" text-anchor="middle" font-size="11" fill="#555">L_total</text>

  <!-- 加号 -->
  <text x="350" y="100" text-anchor="middle" font-size="20">+</text>

  <!-- 分支项 -->
  <rect x="80" y="115" width="140" height="40" rx="6" fill="#fafafa" stroke="#666" stroke-width="1.5"/>
  <text x="150" y="140" text-anchor="middle" font-size="12">重构损失</text>

  <rect x="280" y="115" width="140" height="40" rx="6" fill="#fafafa" stroke="#666" stroke-width="1.5"/>
  <text x="350" y="140" text-anchor="middle" font-size="12">KL 散度</text>

  <rect x="480" y="115" width="140" height="40" rx="6" fill="#fafafa" stroke="#666" stroke-width="1.5"/>
  <text x="550" y="140" text-anchor="middle" font-size="12">对比损失</text>

  <!-- 连线 -->
  <line x1="150" y1="115" x2="320" y2="72" stroke="#999" stroke-width="1"/>
  <line x1="350" y1="115" x2="350" y2="72" stroke="#999" stroke-width="1"/>
  <line x1="550" y1="115" x2="380" y2="72" stroke="#999" stroke-width="1"/>

  <!-- 权重标注 -->
  <text x="220" y="100" text-anchor="middle" font-size="10" fill="#888">× β</text>
  <text x="465" y="100" text-anchor="middle" font-size="10" fill="#888">× γ</text>

</svg>
<p class="read-guide">读法：总损失由三项组成——重构损失（主任务）、KL 散度（正则项，权重 β）、对比损失（辅助任务，权重 γ）。粗框是总损失，细框是组成项。</p>
```

适用场景：VAE/GAN/多任务学习的损失分解、正则化项的关系、多目标优化的权衡。

#### 模板 4：方法对比图（formula-compare）

左右对照两种方法的公式，突出关键差异。

```html
<svg class="svg-figure formula-relation" width="700" height="200" viewBox="0 0 700 200" font-family="'-apple-system','Segoe UI','PingFang SC','Microsoft YaHei','SimHei','Noto Sans CJK SC',sans-serif" aria-label="方法对比">
  <rect x="0" y="0" width="700" height="200" fill="#ffffff"/>
  <!-- 分割线 -->
  <line x1="350" y1="20" x2="350" y2="180" stroke="#ddd" stroke-width="1" stroke-dasharray="6,4"/>

  <!-- 左：方法 A -->
  <text x="175" y="35" text-anchor="middle" font-size="13" font-weight="bold">硬注意力</text>
  <rect x="60" y="50" width="230" height="50" rx="6" fill="#fafafa" stroke="#666" stroke-width="1.5"/>
  <text x="175" y="80" text-anchor="middle" font-size="13">α = onehot(argmax(z))</text>
  <text x="175" y="125" text-anchor="middle" font-size="11" fill="#888">不可微，需强化学习</text>

  <!-- 右：方法 B -->
  <text x="525" y="35" text-anchor="middle" font-size="13" font-weight="bold">软注意力</text>
  <rect x="410" y="50" width="230" height="50" rx="6" fill="#e8f5e9" stroke="#2e7d32" stroke-width="2"/>
  <text x="525" y="80" text-anchor="middle" font-size="13">α = softmax(z)</text>
  <text x="525" y="125" text-anchor="middle" font-size="11" fill="#888">可微，端到端训练</text>

  <!-- 底部结论 -->
  <text x="350" y="170" text-anchor="middle" font-size="12" fill="#c62828">关键差异：softmax 让注意力可微分</text>

</svg>
<p class="read-guide">读法：左右对比硬/软注意力。硬注意力用 argmax 不可微，软注意力用 softmax 可微。绿色框标记论文采用的方法。</p>
```

适用场景：论文方法 vs 基线方法、新旧方案对比、A/B 选择的关键差异。

### 公式关系图的设计规则

1. **节点内只放公式缩写**（符号形式），不放完整 LaTeX——完整公式放在相邻的 `formula-card` 里。
2. **箭头标注"推导依据"**（加温度、蒸馏、softmax），不放公式本身。
3. **颜色语义统一**：
   - 蓝色 `#e3f2fd`：输入/原始变量
   - 橙色 `#fff3e0`：中间计算
   - 绿色 `#e8f5e9` + 粗框：最终结果/论文方法
   - 灰色 `#fafafa`：组成项/基线
4. **必须配 `read-guide`**：图后写"读法"，解释连线含义和颜色逻辑。
5. **与 mono-diagram 的关系**：mono-diagram 生成纯黑白可打印的学术配图（Word/PDF 用）；公式关系图用于 HTML 在线阅读，允许颜色。如果需要打印版，用 mono-diagram 的 process/compare 模板重新渲染为黑白。
