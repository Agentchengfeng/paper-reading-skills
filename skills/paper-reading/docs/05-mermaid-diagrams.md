<!--
input: 论文解读 HTML 需要表达类继承、模块结构、调用时序时
output: Mermaid.js 集成方案、CDN/本地引入、UML 类图与时序图模板、回退机制
pos: paper-reading 的 UML 图渲染技术指南
-->

# Mermaid UML 图集成

## 为什么用 Mermaid

公式关系图（手写 SVG）适合表达**公式之间的推导/依赖/组合**。但论文里还有一类内容手写 SVG 很难表达：

- **类继承关系**：基类 → 派生类、接口实现、聚合/组合（`Model` extends `nn.Module`、`BertEncoder` implements `Encoder`）
- **调用时序**：用户 → 编码器 → 注意力 → 解码器的消息顺序、生命线、同步/异步调用
- **模块结构**：组件之间的依赖方向、分层架构

UML 类图和时序图有**标准符号**（`+public`、`-private`、继承空心三角、聚合空心菱形、时序图生命线+激活块）。手写 SVG 还原这些符号成本高、易错。Mermaid.js 用文本语法描述，浏览器端实时渲染，是 HTML 在线阅读场景的标准方案。

## 何时用 Mermaid vs 公式关系图 vs 概念 SVG

| 内容类型 | 工具 | 类名 |
|---|---|---|
| 单个公式的数学排版 | KaTeX | `formula-card` |
| 多个公式的关系（推导/依赖/组合/对比） | 手写 SVG | `svg-figure formula-relation` |
| 概念级小图（机制链、对照） | 手写 SVG | `svg-figure concept-visual` |
| **类的继承/实现/聚合关系** | **Mermaid** | `mermaid-figure uml-class` |
| **对象间的调用时序** | **Mermaid** | `mermaid-figure uml-sequence` |
| **模块分层依赖** | **Mermaid** | `mermaid-figure uml-class` |

判断依据：**如果图里需要 UML 标准符号（`+/-/#`、空心三角、菱形、生命线），用 Mermaid；如果只是流程/对照/公式关系，用 SVG。**

## HTML head 引入

### 方案 A：CDN（默认，最简）

在 HTML 的 `<head>` 或 `<body>` 末尾加入：

```html
<!-- Mermaid JS（defer 保证 DOM 就绪后初始化） -->
<script defer
        src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"
        crossorigin="anonymous"
        onload="initPaperMermaid()"></script>
```

### 方案 B：本地（离线优先）

```text
论文项目/
└── assets/
    └── mermaid/
        └── mermaid.min.js
```

```html
<script defer src="assets/mermaid/mermaid.min.js"
        onload="initPaperMermaid()"></script>
```

下载地址：`https://github.com/mermaid-js/mermaid/releases`

## 初始化脚本

在 HTML `<body>` 末尾加入。它初始化 Mermaid 并扫描所有 `<pre class="mermaid">` 渲染。失败时保留源码可读（类似 KaTeX 的 `equation-plain` 思路）。

```html
<script>
function initPaperMermaid() {
  if (window.__paperMermaidRendered) return;
  window.__paperMermaidRendered = true;

  if (typeof mermaid === 'undefined') {
    console.warn('Mermaid not loaded, source code remains readable');
    return;
  }
  mermaid.initialize({
    startOnLoad: false,           // 手动控制，避免重复渲染
    theme: 'base',                // 基础主题，配合 themeVariables 定制
    securityLevel: 'strict',      // 禁止 HTML 注入（论文页安全）
    fontFamily: '-apple-system, "Segoe UI", "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif',
    themeVariables: {
      // 类图/时序图统一风格：浅底深线
      primaryColor: '#ffffff',        // 节点底色纯白
      primaryTextColor: '#000000',    // 文字纯黑
      primaryBorderColor: '#000000',  // 边框纯黑
      lineColor: '#000000',           // 连线纯黑
      secondaryColor: '#ffffff',
      tertiaryColor: '#ffffff',
      // 时序图专用
      actorBkg: '#ffffff',
      actorBorder: '#000000',
      actorTextColor: '#000000',
      signalColor: '#000000',
      signalTextColor: '#000000',
      labelBoxBkgColor: '#ffffff',
      labelTextColor: '#000000',
      loopTextColor: '#000000',
      noteBkgColor: '#fff8e1',        // 注释淡黄（论文页允许的语义色）
      noteBorderColor: '#000000',
      noteTextColor: '#000000',
      activationBkgColor: '#ffffff',
      activationBorderColor: '#000000'
    }
  });
  // 渲染所有带 mermaid 类的 pre 块
  document.querySelectorAll('pre.mermaid').forEach(function(el, i) {
    el.id = el.id || ('mermaid-diagram-' + i);
    mermaid.run({ nodes: [el] }).catch(function(err) {
      console.warn('Mermaid render failed for', el.id, err);
      // 失败时不删源码，读者可读到文本语法
    });
  });
}

// defer 时序兜底
window.addEventListener('DOMContentLoaded', function() {
  if (typeof initPaperMermaid === 'function') {
    initPaperMermaid();
  }
});
</script>
```

## 回退机制

```text
1. Mermaid 加载成功
   → 渲染 <pre class="mermaid"> 为 SVG 图
   → 源码被替换

2. Mermaid 加载失败（离线且无本地库）
   → <pre class="mermaid"> 保留原始文本语法
   → 读者看到可读的类图/时序图源码（如 "class Model { +forward(x) }"）
   → 至少保证语义可理解
```

**关键**：Mermaid 源码本身是可读文本（`User --> Encoder: 输入 x`），即使不渲染，读者也能理解调用关系。这是比图片更优的回退——图片坏了完全不可读，Mermaid 源码坏了仍可读。

## UML 模板

### 模板 1：类图（classDiagram）

表达类的继承、实现、聚合关系。用于论文里"模块结构""类层级""组件关系"。

```html
<div class="mermaid-figure uml-class" aria-label="模块类层级">
<pre class="mermaid">
classDiagram
    direction TB

    class nn_Module {
        &lt;&lt;abstract&gt;&gt;
        +forward(x) Tensor*
        +parameters() List~Parameter~
        #_init_weight()
    }

    class Encoder {
        &lt;&lt;interface&gt;&gt;
        +encode(input) Tensor
    }

    class TransformerEncoder {
        +layers: List~Layer~
        +forward(x) Tensor
        +encode(input) Tensor
    }

    class MultiHeadAttention {
        +n_heads: int
        +forward(q, k, v) Tensor
    }

    nn_Module &lt;|-- TransformerEncoder : 继承
    Encoder &lt;|.. TransformerEncoder : 实现
    TransformerEncoder *-- MultiHeadAttention : 组合
</pre>
<p class="read-guide">读法：TransformerEncoder 继承自抽象基类 nn_Module（实心箭头），实现 Encoder 接口（虚线箭头），内部组合了 MultiHeadAttention（实心菱形表示强拥有）。抽象类和接口用斜体标签标记。</p>
</div>
```

**UML 符号速查**（Mermaid 语法；在 `<pre>` 标签里使用时，所有 `<` 必须写成 `&lt;`）：

| 符号 | Mermaid 语法 | `<pre>` 内写法 | 含义 |
|---|---|---|---|
| `+` | `+method()` | `+method()` | public |
| `-` | `-field` | `-field` | private |
| `#` | `#method()` | `#method()` | protected |
| `~类型~` | `List~Tensor~` | `List~Tensor~` | 泛型参数 |
| 构造型 | `<<abstract>>` | `&lt;&lt;abstract&gt;&gt;` | 抽象类（斜体） |
| 构造型 | `<<interface>>` | `&lt;&lt;interface&gt;&gt;` | 接口 |
| 继承 | `Base <\|-- Derived` | `Base &lt;\|-- Derived` | 实线+空心三角 |
| 实现 | `Iface <\|.. Impl` | `Iface &lt;\|.. Impl` | 虚线+空心三角 |
| 组合 | `A *-- B` | `A *-- B` | 实心菱形，强拥有 |
| 聚合 | `A o-- B` | `A o-- B` | 空心菱形，弱引用 |

适用场景：论文的模块结构图、类继承层级、组件依赖关系、框架的接口设计。

### 模板 2：时序图（sequenceDiagram）

表达对象之间的调用顺序、同步/异步消息、生命线激活。用于论文里"前向传播流程""训练循环""推理流程"。

```html
<div class="mermaid-figure uml-sequence" aria-label="前向传播时序">
<pre class="mermaid">
sequenceDiagram
    participant Input as 输入 x
    participant Enc as Encoder
    participant Attn as MultiHeadAttention
    participant FFN as FeedForward
    participant Out as 输出 logits

    Input->>Enc: tokenize & embed
    activate Enc
    Enc->>Attn: Q, K, V
    activate Attn
    Attn-->>Enc: attention weights
    deactivate Attn
    Enc->>FFN: attn_output
    activate FFN
    FFN-->>Enc: transformed
    deactivate FFN
    Enc-->>Out: hidden states
    deactivate Enc

    Note over Enc,Attn: 自注意力：Q·K^T 经 softmax 得权重
    Note over Out: 最终分类层前停止
</pre>
<p class="read-guide">读法：实线箭头是同步调用（调用方等待返回），虚线箭头是返回值。激活块（生命线上的竖条）表示该对象正在执行。注释框解释关键步骤的数学含义。</p>
</div>
```

**时序图语法速查**：

| 语法 | 含义 |
|---|---|
| `A->>B: msg` | 同步消息（实线实心箭头） |
| `A-->>B: msg` | 返回值（虚线实心箭头） |
| `A--)B: msg` | 异步消息（实线开放箭头） |
| `activate A` / `deactivate A` | 生命线激活块 |
| `Note over A,B: text` | 跨对象注释 |
| `participant X as 别名` | 简短 id + 可读别名 |
| `loop ... end` | 循环块 |
| `alt ... else ... end` | 条件分支 |

适用场景：论文的前向/反向传播流程、训练循环、推理 pipeline、多模块交互。

## 设计规则

1. **`<pre>` 内的 `<` 必须转义为 `&lt;`**：这是最重要的规则。Mermaid 类图的构造型注解（`<<abstract>>`、`<<interface>>`）和关系箭头（`<|--`、`<|..`）都含 `<` 字符。如果直接写 `<`，浏览器 DOM 解析器会把 `<<interface>>` 当成未知 HTML 标签 `<interface>` 吃掉，导致 Mermaid 收到残缺文本并报 "Syntax error"。正确写法是 `&lt;&lt;interface&gt;&gt;` 和 `Base &lt;|-- Derived`。时序图和概念图（`->>`、`-->`）里的 `>` 不需要转义，只有 `<` 需要。
2. **优先用别名**：`participant Enc as TransformerEncoder` 让源码可读，渲染后显示全名。
3. **注释框标数学含义**：UML 图里的 `Note over` 用于点出某步骤对应的公式，公式本身放相邻 `formula-card`，不放 Mermaid 源码里。
4. **类图方向**：`direction TB`（自上而下）适合继承层级，`direction LR`（从左到右）适合并列模块。
5. **时序图控制参与者数量**：超过 6 个 participant 时拆成多张图，否则生命线交错难读。
6. **必须配 `read-guide`**：图后写"读法"，解释 UML 符号含义和关键路径。
7. **与 mono-diagram 的关系**：mono-diagram 生成纯黑白可打印的 Mermaid 图（Word/PDF 用，走 mermaid-cli 预渲染）；本 skill 的 Mermaid 是 HTML 在线实时渲染，允许 `themeVariables` 定制语义色（如注释淡黄）。
8. **不放图片标题进源码**：图题写在 HTML 的 `<p>` 或正文里，不写进 `<pre class="mermaid">` 块。

## 验证清单

生成 HTML 后检查：

- [ ] 每个 `mermaid-figure` 内有 `<pre class="mermaid">` 且含合法 Mermaid 语法
- [ ] `<pre>` 内所有 `<` 已转义为 `&lt;`（构造型 `<<...>>`、关系箭头 `<|--`/`<|..`）；`>` 不需要转义
- [ ] Mermaid JS 已引入（CDN 或本地）
- [ ] `initPaperMermaid()` 脚本在 body 末尾
- [ ] 断网测试：Mermaid CDN 不可达时，`<pre>` 内源码可读
- [ ] 类图的继承/实现/组合箭头方向正确（`Base <\|-- Derived` 而非反过来）
- [ ] 时序图参与者不超过 6 个，超过则拆图
- [ ] 每个 `mermaid-figure` 后跟 `read-guide` 解释
- [ ] 复杂时序（嵌套 loop/alt）渲染后生命线不交错错乱
