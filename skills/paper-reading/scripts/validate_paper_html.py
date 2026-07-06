#!/usr/bin/env python3
"""validate_paper_html.py
校验 paper-reading skill 生成的 HTML 文件质量。

四类校验：
  1. formula-card：双层渲染完整性（data-katex + equation-plain）
  2. SVG：XML 合法性 + 元素在 viewBox 内 + 必备属性
  3. Mermaid：<pre> 内未转义的 <（会被 HTML 解析器吃掉）
  4. --contract：paper-reading HTML 协作契约（页面结构、askbar、mark panel、稳定 section id）

设计目标：
  - 零第三方依赖（只用标准库）
  - 退出码：error=1，warn-only/ok=0（CI 友好）
  - 输出可读，Agent 能根据报错直接定位修复

用法：
  python3 scripts/validate_paper_html.py path/to/paper.html
  python3 scripts/validate_paper_html.py docs/ --recursive
  python3 scripts/validate_paper_html.py path/to/paper.html --contract --strict --json
"""
from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence

VERSION = "1.2.0"

# 公式关系图的允许色板（蓝=输入/橙=中间/绿=结果/灰=组成 + 黑墨/白底）
ALLOWED_FIGURE_COLORS = {
    "#ffffff", "#fff",           # 白底
    "#000000", "#000",           # 黑墨
    "#333", "#333333", "#666", "#666666", "#888", "#888888", "#999", "#999999",
    "#ddd", "#dddddd", "#555", "#555555",  # 灰阶文字/边框
    "#f8f9fa", "#fafafa",        # 浅灰底
    "#e3f2fd", "#1565c0",        # 蓝：输入
    "#fff3e0", "#e65100",        # 橙：中间
    "#e8f5e9", "#2e7d32",        # 绿：结果
    "#fff8e1",                   # 注释淡黄（Mermaid note）
    "#c62828",                   # 红：关键差异强调
}


@dataclass
class Issue:
    level: str  # "error" | "warn" | "info"
    line: int   # 0 表示无法定位
    message: str


@dataclass
class Report:
    file: Path
    issues: List[Issue] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        return any(i.level == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "error")

    @property
    def warn_count(self) -> int:
        return sum(1 for i in self.issues if i.level == "warn")


def _line_of(text: str, offset: int) -> int:
    """根据字符偏移算行号（1-based）"""
    if offset < 0:
        return 0
    return text.count("\n", 0, offset) + 1


def _has_class(text: str, class_name: str) -> bool:
    """判断 HTML 中是否存在精确 class token。"""
    return re.search(r'class="[^"]*\b' + re.escape(class_name) + r'\b[^"]*"', text) is not None


def _first_class_tag(text: str, class_name: str) -> Optional[re.Match]:
    """返回第一个包含指定 class token 的起始标签。"""
    return re.search(
        r'<(?P<tag>[a-zA-Z][\w:-]*)\b[^>]*class="[^"]*\b' +
        re.escape(class_name) + r'\b[^"]*"[^>]*>',
        text,
        re.S,
    )


def _section_open_tags(text: str) -> List[re.Match]:
    return list(re.finditer(r'<section\b[^>]*>', text, re.I | re.S))


def _tag_attr(tag: str, attr: str) -> Optional[str]:
    m = re.search(r'\b' + re.escape(attr) + r'="([^"]*)"', tag, re.I)
    return m.group(1) if m else None


# ============================================================
# 1. formula-card 双层渲染校验
# ============================================================

def _find_block_end(text: str, start: int, open_tag: str = "div") -> int:
    """从 start 位置的 <div ...> 开始，找到匹配的 </div> 位置（处理嵌套）"""
    open_re = re.compile(rf'<{open_tag}\b[^>]*>', re.I)
    close_re = re.compile(rf'</{open_tag}>', re.I)
    depth = 1
    pos = text.index('>', start) + 1
    while depth > 0 and pos < len(text):
        next_open = open_re.search(text, pos)
        next_close = close_re.search(text, pos)
        if next_close is None:
            return len(text)
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            pos = next_close.end()
            if depth == 0:
                return pos
    return pos


def validate_formula_cards(text: str, report: Report) -> None:
    """每个 formula-card 必须有 data-katex 和 equation-plain"""
    # 只匹配 class 精确含 "formula-card"（非 formula-card__xxx 子元素）
    for m in re.finditer(
        r'<div[^>]*class="[^"]*\bformula-card(?![\w-])[^"]*"[^>]*>',
        text
    ):
        start = m.start()
        # 找精确的闭合 </div>（处理嵌套）
        block_end = _find_block_end(text, start, "div")
        window = text[start:block_end]
        line = _line_of(text, start)

        if "data-katex" not in window:
            report.issues.append(Issue(
                "error", line,
                "formula-card 缺少 data-katex 属性（LaTeX 源码）。"
                "双层渲染要求 equation-rendered 层必须有 data-katex。"
            ))
        else:
            # 精确取 formula-card 内第一个 data-katex 的值
            katex_m = re.search(r'data-katex="([^"]*)"', window)
            if katex_m:
                val = katex_m.group(1)
                if not val.strip():
                    report.issues.append(Issue(
                        "error", line,
                        "formula-card 的 data-katex 属性为空，必须填 LaTeX 源码。"
                    ))
                elif "<" in val:
                    # data-katex 值里出现 <，说明误填了 HTML/MathML
                    report.issues.append(Issue(
                        "error", line,
                        f"data-katex 值含 '<'，疑似误填渲染后 HTML/MathML。"
                        f"应填 LaTeX 源码如 \\frac{{a}}{{b}}，"
                        f"不是 <mfrac> 或 <frac>。"
                    ))

        if "equation-plain" not in window:
            report.issues.append(Issue(
                "warn", line,
                "formula-card 缺少 equation-plain 纯文字回退层。"
                "KaTeX 不可用时无回退，无障碍访问受损。"
            ))
        else:
            # 检查 equation-plain 非空
            plain_m = re.search(
                r'class="[^"]*equation-plain[^"]*"[^>]*>([^<]*)<',
                window
            )
            if plain_m and not plain_m.group(1).strip():
                report.issues.append(Issue(
                    "warn", line,
                    "equation-plain 内容为空，必须手写 Unicode 纯文字版。"
                ))


# ============================================================
# 2. SVG 校验（XML 合法 + 几何 + 必备属性）
# ============================================================

def _f(val: Optional[str]) -> Optional[float]:
    """安全解析数字"""
    if val is None:
        return None
    m = re.match(r"^[-\d.]+", str(val))
    return float(m.group()) if m else None


def _attrs_block(s: str) -> dict:
    """简易 XML 属性解析"""
    return {m.group(1): m.group(2)
            for m in re.finditer(r'([\w-]+)="([^"]*)"', s)}


def validate_svg_block(svg: str, offset: int, text: str, report: Report) -> None:
    """校验单个 SVG 块"""
    line = _line_of(text, offset)
    opening = re.match(r'<svg[^>]*>', svg)
    if not opening:
        return

    attrs = _attrs_block(opening.group(0))

    # 2a. 必备属性
    if "viewBox" not in attrs:
        report.issues.append(Issue("error", line, "SVG 缺少 viewBox 属性"))
        return
    vb_parts = attrs["viewBox"].split()
    try:
        vb_w, vb_h = float(vb_parts[-2]), float(vb_parts[-1])
    except (IndexError, ValueError):
        report.issues.append(Issue("error", line, f"viewBox 值非法: {attrs['viewBox']}"))
        return

    if "width" not in attrs:
        report.issues.append(Issue("warn", line, "SVG 缺少 width/height（建议与 viewBox 同步）"))
    if "font-family" not in attrs:
        report.issues.append(Issue("warn", line, "SVG 缺少 font-family（建议含中文兜底）"))

    # 2b. XML 合法性
    try:
        # 标准 SVG 通常已经带 xmlns。旧逻辑无条件注入 xmlns 会把
        # <svg xmlns="..."> 变成重复属性并误报 duplicate attribute。
        svg_for_parse = svg
        if "xmlns=" not in opening.group(0):
            svg_for_parse = svg.replace("<svg", '<svg xmlns="http://www.w3.org/2000/svg"', 1)
        ET.fromstring(svg_for_parse)
    except ET.ParseError as e:
        report.issues.append(Issue("error", line, f"SVG XML 解析失败: {e}"))
        return  # XML 不合法就不做几何检查

    # 2c. 几何：所有元素在 viewBox 内
    is_figure = "formula-relation" in attrs.get("class", "")
    for tag in ["rect", "circle", "line", "text", "ellipse"]:
        for m in re.finditer(rf'<{tag}([^>]*?)(?:/)?>', svg, re.S):
            elem_attrs = _attrs_block(m.group(1))
            elem_line = _line_of(text, offset + m.start())
            _check_element_bounds(tag, elem_attrs, vb_w, vb_h, elem_line, report)

    # 2d. 颜色校验（仅 formula-relation）
    if is_figure:
        for prop in ["fill", "stroke"]:
            for m in re.finditer(rf'{prop}="([^"]*)"', svg):
                color = m.group(1).lower().strip()
                if color and color not in ALLOWED_FIGURE_COLORS and not color.startswith("url("):
                    cline = _line_of(text, offset + m.start())
                    report.issues.append(Issue(
                        "warn", cline,
                        f"SVG 使用非语义色 {prop}=\"{color}\"。"
                        f"公式关系图允许：蓝(#e3f2fd/#1565c0) 橙(#fff3e0/#e65100) "
                        f"绿(#e8f5e9/#2e7d32) 灰(#fafafa/#666) 黑墨/白底。"
                    ))


def _check_element_bounds(tag: str, attrs: dict,
                          vw: float, vh: float,
                          line: int, report: Report) -> None:
    """检查单个元素是否超出 viewBox"""
    tol = 0.5  # 0.5px 容差
    overshoots = []

    if tag == "rect":
        x, y = _f(attrs.get("x")), _f(attrs.get("y"))
        w, h = _f(attrs.get("width")), _f(attrs.get("height"))
        if None in [x, y, w, h]:
            return
        if x + w > vw + tol: overshoots.append(f"右边 {x+w} > {vw}")
        if y + h > vh + tol: overshoots.append(f"下边 {y+h} > {vh}")
        if x < -tol: overshoots.append(f"左边 {x} < 0")
        if y < -tol: overshoots.append(f"上边 {y} < 0")

    elif tag == "circle":
        cx, cy, r = _f(attrs.get("cx")), _f(attrs.get("cy")), _f(attrs.get("r"))
        if None in [cx, cy, r]:
            return
        if cx + r > vw + tol: overshoots.append(f"右 {cx+r} > {vw}")
        if cx - r < -tol: overshoots.append(f"左 {cx-r} < 0")
        if cy + r > vh + tol: overshoots.append(f"下 {cy+r} > {vh}")
        if cy - r < -tol: overshoots.append(f"上 {cy-r} < 0")

    elif tag == "ellipse":
        cx, cy = _f(attrs.get("cx")), _f(attrs.get("cy"))
        rx, ry = _f(attrs.get("rx")), _f(attrs.get("ry"))
        if None in [cx, cy, rx, ry]:
            return
        if cx + rx > vw + tol: overshoots.append(f"右 {cx+rx} > {vw}")
        if cy + ry > vh + tol: overshoots.append(f"下 {cy+ry} > {vh}")

    elif tag == "line":
        pts = [_f(attrs.get(k)) for k in ["x1", "y1", "x2", "y2"]]
        if any(p is None for p in pts):
            return
        x1, y1, x2, y2 = pts
        if max(x1, x2) > vw + tol: overshoots.append(f"x={max(x1,x2)} > {vw}")
        if max(y1, y2) > vh + tol: overshoots.append(f"y={max(y1,y2)} > {vh}")
        if min(x1, x2) < -tol: overshoots.append(f"x={min(x1,x2)} < 0")
        if min(y1, y2) < -tol: overshoots.append(f"y={min(y1,y2)} < 0")

    elif tag == "text":
        x, y = _f(attrs.get("x")), _f(attrs.get("y"))
        if x is not None and x > vw + tol: overshoots.append(f"text x={x} > {vw}")
        if y is not None and y > vh + tol: overshoots.append(f"text y={y} > {vh}")
        if y is not None and y < -tol: overshoots.append(f"text y={y} < 0")

    for ovs in overshoots:
        report.issues.append(Issue(
            "error", line,
            f"SVG <{tag}> 超出 viewBox ({vw}x{vh}): {ovs}。元素会被裁切。"
        ))


def validate_svgs(text: str, report: Report) -> None:
    """校验所有 SVG 块（包括 svg-figure 和独立的 svg）"""
    # 匹配 <svg ...>...</svg>，容忍内部嵌套标签
    for m in re.finditer(r'<svg\b[^>]*>.*?</svg>', text, re.S):
        validate_svg_block(m.group(0), m.start(), text, report)


# ============================================================
# 3. Mermaid 转义校验
# ============================================================

def validate_mermaid_blocks(text: str, report: Report) -> None:
    """<pre class="mermaid"> 内的 < 必须转义为 &lt;"""
    for m in re.finditer(
        r'<pre[^>]*class="[^"]*mermaid[^"]*"[^>]*>(.*?)</pre>',
        text, re.S
    ):
        body = m.group(1)
        line = _line_of(text, m.start())
        # 找未转义的 <（不是 &lt;）
        # 排除合法的 HTML 实体和注释
        for lt_m in re.finditer(r'<(?!/?[a-zA-Z!])', body):
            lt_line = _line_of(text, m.start() + lt_m.start())
            # 取上下文
            ctx_start = max(0, lt_m.start() - 10)
            ctx_end = min(len(body), lt_m.end() + 15)
            context = body[ctx_start:ctx_end].replace("\n", "\\n")
            report.issues.append(Issue(
                "error", lt_line,
                f'<pre class="mermaid"> 内发现未转义的 "<"。'
                f'浏览器会把它当成 HTML 标签开始，吃掉后续内容导致 '
                f'Mermaid Syntax error。上下文: ...{context}... '
                f'修复：把 < 改成 &lt;（构造型 &lt;&lt;interface&gt;&gt;、'
                f'关系箭头 Base &lt;|-- Derived）。'
            ))


# ============================================================
# 4. HTML 协作契约校验（--contract）
# ============================================================

def validate_contract(text: str, report: Report) -> None:
    """校验 paper-reading HTML 的页面结构与协作契约。

    该模式不替代组件校验，而是检查页面是否具备可持续协作的结构：
    稳定根节点、正文区域、section id、mark panel、askbar 以及 bridge 写回需要的锚点。
    """
    doc_tag = _first_class_tag(text, "paper-doc")
    if not doc_tag:
        report.issues.append(Issue(
            "error", 0,
            "--contract: 缺少 .paper-doc 根容器。页面必须有稳定根节点，供阅读地图、正文和协作组件挂载。"
        ))
    else:
        line = _line_of(text, doc_tag.start())
        if not _tag_attr(doc_tag.group(0), "data-paper-id"):
            report.issues.append(Issue(
                "warn", line,
                "--contract: .paper-doc 建议添加 data-paper-id，便于 bridge 写回、版本追踪和多论文区分。"
            ))

    main_tag = _first_class_tag(text, "paper-main")
    if not main_tag:
        report.issues.append(Issue(
            "error", 0,
            "--contract: 缺少 .paper-main 正文容器。Agent 后续重组正文和定位 section 需要该区域。"
        ))

    if not _has_class(text, "paper-sidebar"):
        report.issues.append(Issue(
            "warn", 0,
            "--contract: 缺少 .paper-sidebar 阅读地图。长文页面建议提供内容阅读地图，而不是只放机械目录。"
        ))

    section_tags = _section_open_tags(text)
    if not section_tags:
        report.issues.append(Issue(
            "error", 0,
            "--contract: 缺少 <section id=\"...\">。稳定 section id 是划线、刷新定位和二次追问的基础。"
        ))
    else:
        ids = []
        for m in section_tags:
            section_id = _tag_attr(m.group(0), "id")
            line = _line_of(text, m.start())
            if not section_id:
                report.issues.append(Issue(
                    "warn", line,
                    "--contract: <section> 缺少 id。建议所有正文 section 都有稳定 id。"
                ))
            else:
                ids.append(section_id)

        if len(ids) < 3:
            report.issues.append(Issue(
                "warn", 0,
                "--contract: 稳定 section id 少于 3 个。论文长文通常至少需要研究目的、机制/概念、证据/边界等可定位区域。"
            ))

        for required_id in ["thesis", "sources", "paper-mark-panel"]:
            if required_id not in ids:
                report.issues.append(Issue(
                    "warn", 0,
                    f"--contract: 建议包含 section#{required_id}，用于目的优先阅读、来源区或协作写回。"
                ))

    if not _has_class(text, "paper-mark-panel"):
        report.issues.append(Issue(
            "warn", 0,
            "--contract: 缺少 .paper-mark-panel。划线问题和后续解释建议写入独立协作区。"
        ))

    if not _has_class(text, "paper-annotation"):
        report.issues.append(Issue(
            "warn", 0,
            "--contract: 缺少 .paper-annotation。bridge 写回后通常需要 annotation 容器承载问题和解释。"
        ))

    askbar = _first_class_tag(text, "paper-askbar")
    if not askbar:
        report.issues.append(Issue(
            "warn", 0,
            "--contract: 缺少 .paper-askbar。最小阅读页可省略，但可交互协作页建议提供追问输入区。"
        ))
    else:
        askbar_line = _line_of(text, askbar.start())
        for child in ["paper-askbar__form", "paper-askbar__input", "paper-askbar__button"]:
            if not _has_class(text, child):
                report.issues.append(Issue(
                    "warn", askbar_line,
                    f"--contract: .paper-askbar 存在，但缺少 .{child}。askbar 组件不完整。"
                ))

    if _has_class(text, "formula-card") and not _has_class(text, "formula-card__equation-plain"):
        report.issues.append(Issue(
            "warn", 0,
            "--contract: 页面存在 formula-card，但没有 equation-plain 回退层。"
        ))


# ============================================================
# 主流程
# ============================================================

def validate_file(path: Path, *, contract: bool = False) -> Report:
    """校验单个 HTML 文件"""
    report = Report(file=path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        report.issues.append(Issue("error", 0, f"无法读取文件: {e}"))
        return report

    if not text.strip():
        report.issues.append(Issue("error", 0, "文件为空"))
        return report

    validate_formula_cards(text, report)
    validate_svgs(text, report)
    validate_mermaid_blocks(text, report)
    if contract:
        validate_contract(text, report)

    return report


def discover(paths: Sequence[str], recursive: bool = False) -> List[Path]:
    """发现所有 .html 文件"""
    found: List[Path] = []
    for item in paths:
        p = Path(item)
        if p.is_file() and p.suffix.lower() in {".html", ".htm"}:
            found.append(p)
        elif p.is_dir():
            pattern = "**/*.html" if recursive else "*.html"
            found.extend(p.glob(pattern))
    return sorted(set(found))


def format_report(report: Report) -> str:
    """格式化单个文件的报告"""
    lines = [f"\n{'=' * 60}", f"📄 {report.file}", "=" * 60]
    if not report.issues:
        lines.append("  ✅ 全部通过，无问题")
        return "\n".join(lines)

    # 按行号排序
    sorted_issues = sorted(report.issues, key=lambda i: (i.line, i.level))
    for issue in sorted_issues:
        level_icon = {"error": "❌", "warn": "⚠️ ", "info": "ℹ️ "}[issue.level]
        loc = f"L{issue.line}" if issue.line else "L?"
        lines.append(f"  {level_icon} [{issue.level}] {loc} {issue.message}")

    lines.append(f"\n  汇总: {report.error_count} error, {report.warn_count} warn")
    return "\n".join(lines)


def report_to_dict(report: Report) -> dict:
    """转换为机器可读结果，供 Agent / CI wrapper 解析。"""
    return {
        "file": str(report.file),
        "error_count": report.error_count,
        "warn_count": report.warn_count,
        "issues": [
            {"level": i.level, "line": i.line, "message": i.message}
            for i in sorted(report.issues, key=lambda x: (x.line, x.level, x.message))
        ],
    }


def build_summary(reports: List[Report], *, strict: bool = False, contract: bool = False) -> dict:
    error_count = sum(r.error_count for r in reports)
    warn_count = sum(r.warn_count for r in reports)
    return {
        "version": VERSION,
        "file_count": len(reports),
        "error_count": error_count,
        "warn_count": warn_count,
        "ok": error_count == 0 and (warn_count == 0 if strict else True),
        "strict": strict,
        "contract": contract,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="校验 paper-reading skill 生成的 HTML 文件质量"
    )
    parser.add_argument("paths", nargs="+", help="HTML 文件或目录路径")
    parser.add_argument("--recursive", "-r", action="store_true",
                        help="递归扫描目录")
    parser.add_argument("--json", action="store_true",
                        help="输出机器可读 JSON，方便 Agent / CI wrapper 解析")
    parser.add_argument("--contract", action="store_true",
                        help="检查 paper-reading HTML 协作契约：结构、section id、askbar、mark panel 等")
    parser.add_argument("--strict", action="store_true",
                        help="严格验收模式：存在 warn 也返回失败退出码")
    parser.add_argument("--version", "-v", action="version",
                        version=f"validate_paper_html {VERSION}")
    args = parser.parse_args(argv)

    files = discover(args.paths, args.recursive)
    if not files:
        print("未找到 .html 文件", file=sys.stderr)
        return 2

    reports = [validate_file(path, contract=args.contract) for path in files]
    summary = build_summary(reports, strict=args.strict, contract=args.contract)

    if args.json:
        print(json.dumps({
            "summary": summary,
            "reports": [report_to_dict(report) for report in reports],
        }, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print(format_report(report))
        print(f"\n{'=' * 60}")
        print(f"总计: {summary['file_count']} 文件, {summary['error_count']} error, {summary['warn_count']} warn")
        if args.strict and summary["warn_count"] > 0:
            print("strict 模式：warning 也会导致失败退出码")
        print("=" * 60)

    # 默认：有 error 返回 1；strict：warning 也返回 1
    return 1 if (summary["error_count"] > 0 or (args.strict and summary["warn_count"] > 0)) else 0


if __name__ == "__main__":
    sys.exit(main())
