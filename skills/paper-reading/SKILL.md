---
name: paper-reading
description: "读研究论文、技术报告、arXiv PDF、论文 repo 或资料包时使用。用于目的优先的论文解读、文档式 HTML 长文、SVG 图解、划线协作标记、本地 bridge 写回、标记解释、正文重组、以及 Codex 内置浏览器刷新验证。"
---

# 论文协作阅读

## 原则

- 只定义方法、结构、组件契约和执行边界，不定义某篇论文、模型、系统、指标或实验内容。
- 具体内容必须来自当次论文材料、repo、用户补充或当前 HTML。
- `~/.codex/skills/paper-reading` 是 `~/.claude/skills/paper-reading` 的软链；改这里即同步两边。

## 组件

```text
paper-reading/
├── docs/01-paper-prompt.md     论文解读方法
├── docs/02-html-contract.md    HTML 协作契约
├── docs/03-layout-standard.md  页面版式标准
└── scripts/bridge.py           本地标记写回脚本
```

## 来源与协议

- 官方来源：`https://github.com/Agentchengfeng/paper-reading-skills`
- 作者：`成峰 / AI产品自由`
- 协议：Apache-2.0；复制、改造或二次发布时保留 `LICENSE` 和 `NOTICE.md`。

## 资源路由

- 从论文或 repo 生成/重写正文：读 `docs/01-paper-prompt.md`。
- 创建、修复或优化论文 HTML：读 `docs/03-layout-standard.md`，再读 `docs/02-html-contract.md`。
- 处理划线标记、补充解释、作图或正文重组：读 `docs/02-html-contract.md`。
- 启动本地标记写回：运行 `scripts/bridge.py`，不要重写 bridge 逻辑。

## 硬规则

- 解读开头先写研究目的，再写核心结论。
- 页面左侧使用内容阅读地图，不做机械章节目录。
- 稍微复杂的内容默认用 SVG 图解：机制链、流程、对照、公式关系、调度逻辑、瓶颈链和概念间依赖，不能只靠长段文字解释。
- 划线协作只保留三类动作：`名词讲解`、`逻辑梳理`、`作图理解`。
- 用户说 `重组`、`整合`、`合并到正文`、`改成新段落` 时，把批注内容融入正文，删除对应疑问卡片和解释块；有用 SVG 保留为普通正文图。
- 本地 HTML 的刷新、DOM 检查和交互验证默认使用 Codex 内置浏览器；验证 URL 使用 localhost，不用 `file://` 代替。

## 边界

- HTML 不放 API key，不直接调用模型。
- Bridge 只接收标记、写 JSONL、改 HTML；不生成解释。
- 不新增 README、examples、templates、runtime 解释层或未验证示例。
