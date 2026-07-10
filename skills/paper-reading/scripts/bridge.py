#!/usr/bin/env python3
import argparse
import html
import json
import re
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


KIND_LABELS = {
    "term": "名词讲解",
    "logic": "逻辑梳理",
    "diagram": "作图理解",
}

BLOCK_RE = re.compile(r"\n(?P<indent>\s*)(?P<block><(?P<tag>p|li|h[1-6]|div)\b[^>]*>.*?</(?P=tag)>)", re.S)
TAG_RE = re.compile(r"<[^>]+>")
SVG_TEXT_RE = re.compile(r"(?P<open><text\b(?P<attrs>[^>]*)>)(?P<body>.*?)(?P<close></text>)", re.S)


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def attr_escape(value):
    return html.escape(str(value or ""), quote=True)


def text_escape(value):
    return html.escape(str(value or ""), quote=False)


def normalize_kind(kind):
    return kind if kind in KIND_LABELS else "logic"


def safe_anchor_id(mark_id):
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", str(mark_id or "")).strip("-")
    return f"paper-anchor-{safe or 'mark'}"


def normalize_text(value):
    return re.sub(r"\s+", " ", html.unescape(str(value or ""))).strip()


def visible_text(fragment):
    return normalize_text(TAG_RE.sub("", fragment))


def is_inside_question_marker(source, start):
    last_open = source.rfind('<aside class="paper-question-marker"', 0, start)
    last_close = source.rfind("</aside>", 0, start)
    return last_open != -1 and last_open > last_close


def selected_candidates(selected):
    selected = normalize_text(selected)
    if not selected:
        return []

    candidates = [selected]
    parts = [part.strip() for part in re.split(r"(?<=[。；;.!?？])\s*", selected) if len(part.strip()) >= 12]
    candidates.extend(parts)
    if len(selected) > 80:
        candidates.append(selected[:120].strip())
        candidates.append(selected[-120:].strip())

    escaped = []
    for value in candidates:
        escaped.append(value)
        escaped.append(html.escape(value, quote=False))

    seen = set()
    result = []
    for value in sorted(escaped, key=len, reverse=True):
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def highlight_block(block, item):
    mark_id = str(item.get("id") or "")
    kind = normalize_kind(item.get("kind"))
    anchor_id = item.get("anchorId") or safe_anchor_id(mark_id)
    if mark_id and f'data-mark-id="{attr_escape(mark_id)}"' in block:
        return block, False

    for candidate in selected_candidates(item.get("text")):
        index = block.find(candidate)
        if index == -1:
            continue
        span = (
            f'<span id="{attr_escape(anchor_id)}" class="annotation-highlight" '
            f'data-mark-id="{attr_escape(mark_id)}" data-mark-kind="{attr_escape(kind)}">'
            f"{candidate}</span>"
        )
        return block[:index] + span + block[index + len(candidate):], True

    highlighted_svg, svg_changed = highlight_svg_text(block, item)
    if svg_changed:
        return highlighted_svg, True

    return block, False


def add_svg_text_marker(open_tag, item, *, with_anchor):
    mark_id = attr_escape(item.get("id"))
    kind = attr_escape(normalize_kind(item.get("kind")))
    anchor_id = attr_escape(item.get("anchorId") or safe_anchor_id(item.get("id")))

    if "svg-text-annotation-highlight" not in open_tag:
        if 'class="' in open_tag:
            open_tag = re.sub(r'class="([^"]*)"', r'class="\1 svg-text-annotation-highlight"', open_tag, count=1)
        else:
            open_tag = open_tag[:-1] + ' class="svg-text-annotation-highlight">'

    extras = []
    if with_anchor and ' id="' not in open_tag:
        extras.append(f'id="{anchor_id}"')
    if 'data-mark-id="' not in open_tag:
        extras.append(f'data-mark-id="{mark_id}"')
    if 'data-mark-kind="' not in open_tag:
        extras.append(f'data-mark-kind="{kind}"')
    if extras:
        open_tag = open_tag[:-1] + " " + " ".join(extras) + ">"
    return open_tag


def highlight_svg_text(block, item):
    if "<svg" not in block or "<text" not in block:
        return block, False

    mark_id = str(item.get("id") or "")
    anchor_id = item.get("anchorId") or safe_anchor_id(mark_id)
    if anchor_id and f'id="{attr_escape(anchor_id)}"' in block:
        return block, False

    selected = normalize_text(item.get("text"))
    if not selected:
        return block, False

    matches = list(SVG_TEXT_RE.finditer(block))
    target_indexes = set()
    for index, match in enumerate(matches):
        text = visible_text(match.group("body"))
        if not text:
            continue
        if text in selected or selected in text:
            target_indexes.add(index)

    if not target_indexes:
        selected_tokens = [token for token in re.split(r"\s+", selected) if len(token) >= 2]
        for index, match in enumerate(matches):
            text = visible_text(match.group("body"))
            if text and any(token in text for token in selected_tokens):
                target_indexes.add(index)

    if not target_indexes:
        return block, False

    first_target = min(target_indexes)

    def replace(match):
        current_index = len(replace.seen)
        replace.seen.append(current_index)
        if current_index not in target_indexes:
            return match.group(0)
        open_tag = add_svg_text_marker(match.group("open"), item, with_anchor=current_index == first_target)
        return f'{open_tag}{match.group("body")}{match.group("close")}'

    replace.seen = []
    return SVG_TEXT_RE.sub(replace, block), True


def find_section_bounds(source, section_id):
    section_start = source.find(f'<section id="{section_id}"')
    if section_start == -1:
        return None
    section_open_end = source.find(">", section_start)
    section_close = source.find("\n      </section>", section_open_end)
    if section_close == -1:
        close_match = re.search(r"\n\s*</section>", source[section_open_end:])
        section_close = section_open_end + close_match.start() if close_match else -1
    if section_close == -1:
        return None
    return section_start, section_close


def find_best_block(source, item, section_bounds):
    selected = normalize_text(item.get("text"))
    anchor_text = normalize_text(item.get("anchorText"))
    needles = [text for text in (selected, anchor_text) if text]
    if not needles:
        return None

    ranges = []
    if section_bounds:
        ranges.append(section_bounds)
    main_start = source.find('<main class="paper-main">')
    main_close = source.rfind("</main>")
    if main_start != -1 and main_close != -1:
        ranges.append((main_start, main_close))
    ranges.append((0, len(source)))

    used_ranges = set()
    for start, end in ranges:
        key = (start, end)
        if key in used_ranges:
            continue
        used_ranges.add(key)
        best = None
        for match in BLOCK_RE.finditer(source, start, end):
            block_start = match.start("block")
            block_end = match.end("block")
            if is_inside_question_marker(source, block_start):
                continue
            block = match.group("block")
            block_text = visible_text(block)
            if not block_text:
                continue

            score = 0
            for needle in needles:
                if needle and needle in block_text:
                    score = max(score, 100000 + len(needle))
                elif block_text and block_text in needle:
                    score = max(score, 50000 + len(block_text))
                elif needle[:48] and needle[:48] in block_text:
                    score = max(score, 10000 + len(needle[:48]))

            if score and (best is None or score > best["score"]):
                best = {"start": block_start, "end": block_end, "block": block, "score": score}
        if best:
            return best

    return None


def build_question_block(item):
    kind = normalize_kind(item.get("kind"))
    mark_id = attr_escape(item.get("id"))
    anchor_id = attr_escape(item.get("anchorId") or safe_anchor_id(item.get("id")))
    label = KIND_LABELS[kind]
    question = text_escape(item.get("question") or "")

    return f"""

        <aside class="paper-question-marker" data-question-id="{mark_id}" data-question-kind="{attr_escape(kind)}" data-anchor-id="{anchor_id}">
          <span class="paper-question-marker__action">{text_escape(label)}</span>
          <span class="paper-question-marker__supplement">补充：{question}</span>
        </aside>
"""


def insert_question_block(page_path, item):
    if not page_path:
        return {"inserted": False, "reason": "page path not configured"}

    path = Path(page_path).expanduser()
    source = path.read_text(encoding="utf-8")
    mark_id = attr_escape(item.get("id"))
    if mark_id and f'data-question-id="{mark_id}"' in source:
        return {"inserted": False, "duplicate": True}

    section_id = str(item.get("sectionId") or "").strip() or "thesis"
    item["anchorId"] = item.get("anchorId") or safe_anchor_id(item.get("id"))
    block = build_question_block(item)
    section_bounds = find_section_bounds(source, section_id)
    target = find_best_block(source, item, section_bounds)

    if target:
        highlighted, highlighted_text = highlight_block(target["block"], item)
        updated = source[:target["start"]] + highlighted + block + source[target["end"]:]
        path.write_text(updated, encoding="utf-8")
        return {
            "inserted": True,
            "sectionId": section_id,
            "placement": "after matched block",
            "highlighted": highlighted_text,
        }

    if section_bounds:
        _, section_close = section_bounds
        updated = source[:section_close] + block + source[section_close:]
        path.write_text(updated, encoding="utf-8")
        return {"inserted": True, "sectionId": section_id, "placement": "section fallback"}

    fallback = re.search(r'\n\s*<section\s+id="paper-mark-panel"', source)
    if fallback:
        updated = source[:fallback.start()] + block + source[fallback.start():]
        path.write_text(updated, encoding="utf-8")
        return {"inserted": True, "sectionId": None, "fallback": "before paper-mark-panel"}

    return {"inserted": False, "reason": f"section not found: {section_id}"}


# --- 撤销支持 ---
# 删除指定 mark_id 对应的疑问卡片(aside)并还原高亮 span 为纯文本。
# 撤销语义:让 HTML 回到这条标记被插入之前的样子。

ASIDE_BY_ID_RE = re.compile(
    r"\n\s*<aside\b[^>]*data-question-id=\"(?P<qid>[^\"]+)\"[^>]*>.*?</aside>",
    re.S,
)

HIGHLIGHT_BY_ID_RE = re.compile(
    r'<span\b[^>]*data-mark-id="(?P<qid>[^"]+)"[^>]*>',
    re.S,
)

# 匹配一个完整的 <span ...>...</span>(处理嵌套:用栈计数配对闭合标签)
SPAN_OPEN_RE = re.compile(r'<span\b[^>]*>', re.S)
SPAN_CLOSE_RE = re.compile(r'</span>', re.S)


def _find_span_end(source, start):
    """从 start 处的 <span ...> 开始,找到与之配对的 </span> 位置(处理嵌套 span)。

    返回 (end_index_after_close, inner_text) 或 None。
    """
    open_match = SPAN_OPEN_RE.match(source, start)
    if not open_match:
        return None
    pos = open_match.end()
    depth = 1
    inner_start = pos
    while depth > 0 and pos < len(source):
        next_open = SPAN_OPEN_RE.search(source, pos)
        next_close = SPAN_CLOSE_RE.search(source, pos)
        if not next_close:
            return None  # 标签不闭合,放弃
        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                inner = source[inner_start:next_close.start()]
                return next_close.end(), inner
            pos = next_close.end()
    return None


def _unwrap_highlight_spans(source, mark_id):
    """还原所有 data-mark-id == mark_id 的高亮 span 为纯文本,处理嵌套。

    策略:反复扫描,每次找到目标 span 的开标签,用栈匹配找到配对的 </span>,
    把整个 span 替换成 inner。处理嵌套:如果 inner 里还套着同 id 的 span,
    下一轮扫描会继续处理。
    """
    changes = 0
    while True:
        m = HIGHLIGHT_BY_ID_RE.search(source)
        if not m:
            break
        # 检查这个 span 是否是目标 mark_id
        if m.group("qid") != mark_id:
            # 找下一个:在当前匹配后继续找
            # 但 HIGHLIGHT_BY_ID_RE 只匹配带 data-mark-id 的,需要跳过非目标的
            # 用 search 从 m.end() 之后找下一个候选
            next_m = HIGHLIGHT_BY_ID_RE.search(source, m.end())
            if not next_m:
                break
            if next_m.group("qid") != mark_id:
                # 没有目标了
                break
            m = next_m

        result = _find_span_end(source, m.start())
        if not result:
            break
        end, inner = result
        # 替换:整个 span(含开闭标签)→ inner
        source = source[:m.start()] + inner + source[end:]
        changes += 1
    return source, changes


def remove_question_block(page_path, mark_id):
    """从 HTML 删除指定 mark_id 的 aside 卡片 + 还原对应高亮 span。"""
    if not page_path:
        return {"removed": False, "reason": "page path not configured"}
    if not mark_id:
        return {"removed": False, "reason": "mark_id is empty"}

    path = Path(page_path).expanduser()
    if not path.exists():
        return {"removed": False, "reason": "html file not found"}

    source = path.read_text(encoding="utf-8")
    changes = {"aside_removed": 0, "highlight_unwrapped": 0}

    # 1. 删除匹配的 aside 块(data-question-id == mark_id)
    def _drop_aside(m):
        if m.group("qid") == mark_id:
            changes["aside_removed"] += 1
            return ""
        return m.group(0)
    source = ASIDE_BY_ID_RE.sub(_drop_aside, source)

    # 2. 还原高亮 span(data-mark-id == mark_id)为纯文本(处理嵌套)
    source, span_changes = _unwrap_highlight_spans(source, mark_id)
    changes["highlight_unwrapped"] += span_changes

    # 3. 还原 SVG 文本上的高亮(data-mark-id == mark_id)
    #    策略:从 class 中移除 svg-text-annotation-highlight;若 class 变空则删 class 属性。
    svg_mark_re = re.compile(
        r'(?P<open><text\b[^>]*?)data-mark-id="(?P<qid>[^"]+)"([^>]*?)>'
    )

    def _strip_svg(m):
        if m.group("qid") != mark_id:
            return m.group(0)
        open_tag = m.group("open") + m.group(3)
        # 移除 svg-text-annotation-highlight class
        open_tag = re.sub(r'\s*svg-text-annotation-highlight', '', open_tag)
        # 移除空的 data-mark-kind
        open_tag = re.sub(r'\s+data-mark-kind="[^"]*"', '', open_tag)
        # 若 class="" 则删除
        open_tag = re.sub(r'\s+class=""', '', open_tag)
        changes["highlight_unwrapped"] += 1
        return open_tag + ">"
    source = svg_mark_re.sub(_strip_svg, source)

    if changes["aside_removed"] or changes["highlight_unwrapped"]:
        path.write_text(source, encoding="utf-8")
        return {"removed": True, **changes}
    return {"removed": False, "reason": "mark_id not found in html", **changes}


def undo_last_mark(page_path, log_path, mark_id=None):
    """撤销最近一条标记(或指定 mark_id 的那条)。

    流程:
      1. 从 JSONL 末尾找到目标记录(优先 mark_id,否则最后一条)
      2. 从 JSONL 删除该行
      3. 调 remove_question_block 回滚 HTML
    """
    log_path = Path(log_path).expanduser()
    if not log_path.exists():
        return {"ok": False, "reason": "log file not found"}

    lines = log_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return {"ok": False, "reason": "log is empty"}

    target_index = None
    if mark_id:
        # 从末尾向前找匹配的 mark_id(跳过损坏行)
        for i in range(len(lines) - 1, -1, -1):
            try:
                row = json.loads(lines[i])
            except json.JSONDecodeError:
                continue
            if row.get("id") == mark_id:
                target_index = i
                break
        if target_index is None:
            return {"ok": False, "reason": f"mark_id not found: {mark_id}"}
    else:
        # 取最后一条有效 JSON 行(跳过空行、损坏行)
        for i in range(len(lines) - 1, -1, -1):
            if not lines[i].strip():
                continue
            try:
                json.loads(lines[i])
                target_index = i
                break
            except json.JSONDecodeError:
                continue
        if target_index is None:
            return {"ok": False, "reason": "log is empty"}

    target_line = lines[target_index]
    try:
        target_item = json.loads(target_line)
    except json.JSONDecodeError:
        return {"ok": False, "reason": "target jsonl line is invalid"}

    # 从 JSONL 删除该行
    del lines[target_index]
    log_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")

    # 回滚 HTML
    target_mark_id = target_item.get("id") or ""
    html_result = remove_question_block(page_path, target_mark_id)

    return {
        "ok": True,
        "undoneId": target_mark_id,
        "undoneKind": target_item.get("kind"),
        "undoneText": target_item.get("text", "")[:80],
        "htmlResult": html_result,
    }


class PaperBridgeHandler(BaseHTTPRequestHandler):
    server_version = "PaperReadingBridge/2.1"

    def token_ok(self):
        """可选本地 token。未配置 token 时保持向后兼容；配置后所有接口都要带 token。"""
        expected = getattr(self.server, "token", None)
        if not expected:
            return True
        provided = self.headers.get("X-Paper-Bridge-Token") or self.headers.get("Authorization", "")
        if provided.startswith("Bearer "):
            provided = provided[7:].strip()
        return provided == expected

    def require_token(self):
        if self.token_ok():
            return True
        self.write_json({"ok": False, "error": "unauthorized: missing or invalid bridge token"}, status=401)
        return False

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Paper-Bridge-Token, Authorization")
        super().end_headers()

    def write_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.write_json({"ok": True})

    def do_GET(self):
        if not self.require_token():
            return
        path = urlparse(self.path).path
        if path == "/healthz":
            self.write_json({"ok": True, "page": str(self.server.page_path), "log": str(self.server.log_path)})
            return
        if path == "/requests":
            rows = []
            if self.server.log_path.exists():
                for line in self.server.log_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        rows.append({"raw": line})
            self.write_json({"ok": True, "requests": rows})
            return
        self.write_json({"ok": False, "error": "not found"}, status=404)

    def do_POST(self):
        if not self.require_token():
            return
        path = urlparse(self.path).path
        if path != self.server.endpoint:
            self.write_json({"ok": False, "error": "not found"}, status=404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8")
            item = json.loads(raw)
        except Exception as exc:
            self.write_json({"ok": False, "error": f"bad json: {exc}"}, status=400)
            return

        item["kind"] = normalize_kind(item.get("kind"))
        item["receivedAt"] = now_iso()
        item["status"] = "written"

        insert_result = insert_question_block(self.server.page_path, item)
        item["insertResult"] = insert_result
        item["handledAt"] = now_iso() if insert_result.get("inserted") else None

        self.server.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.server.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

        self.write_json({"ok": True, "item": item, "reload": bool(insert_result.get("inserted"))})

    def do_DELETE(self):
        """撤销接口:DELETE /__paper_undo 删最近一条;带 ?id=mark-xxx 删指定一条。"""
        if not self.require_token():
            return
        parsed = urlparse(self.path)
        if parsed.path != "/__paper_undo":
            self.write_json({"ok": False, "error": "not found"}, status=404)
            return

        # 从 query 取可选 mark_id
        from urllib.parse import parse_qs
        qs = parse_qs(parsed.query)
        mark_id = (qs.get("id", [None]) or [None])[0]

        result = undo_last_mark(
            self.server.page_path,
            self.server.log_path,
            mark_id=mark_id,
        )
        self.write_json(result)

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")


class PaperBridgeServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, *, endpoint, page_path, log_path, token=None):
        super().__init__(server_address, handler_class)
        self.endpoint = endpoint
        self.page_path = Path(page_path).expanduser() if page_path else None
        self.log_path = Path(log_path).expanduser()
        self.token = token


def main():
    parser = argparse.ArgumentParser(description="Paper reading local bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--endpoint", default="/__paper_annotation")
    parser.add_argument("--page", required=True, help="HTML file to update.")
    parser.add_argument("--log", default="paper_annotation_requests.jsonl")
    parser.add_argument("--token", default=None, help="Optional local bridge token. If set, requests must include X-Paper-Bridge-Token or Authorization: Bearer <token>.")
    args = parser.parse_args()

    server = PaperBridgeServer(
        (args.host, args.port),
        PaperBridgeHandler,
        endpoint=args.endpoint,
        page_path=args.page,
        log_path=args.log,
        token=args.token,
    )
    print(f"Paper reading bridge: http://{args.host}:{args.port}{args.endpoint}")
    print(f"Health: http://{args.host}:{args.port}/healthz")
    if args.token:
        print("Token auth: enabled; send X-Paper-Bridge-Token or Authorization: Bearer <token>")
    else:
        print("Token auth: disabled; use --token for safer local write-back")
    print(f"Request log: {Path(args.log).expanduser()}")
    print(f"HTML page: {Path(args.page).expanduser()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
