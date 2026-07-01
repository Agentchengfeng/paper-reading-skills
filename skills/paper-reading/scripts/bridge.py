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


class PaperBridgeHandler(BaseHTTPRequestHandler):
    server_version = "PaperReadingBridge/2.0"

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
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

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format % args}")


class PaperBridgeServer(ThreadingHTTPServer):
    def __init__(self, server_address, handler_class, *, endpoint, page_path, log_path):
        super().__init__(server_address, handler_class)
        self.endpoint = endpoint
        self.page_path = Path(page_path).expanduser() if page_path else None
        self.log_path = Path(log_path).expanduser()


def main():
    parser = argparse.ArgumentParser(description="Paper reading local bridge.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--endpoint", default="/__paper_annotation")
    parser.add_argument("--page", required=True, help="HTML file to update.")
    parser.add_argument("--log", default="paper_annotation_requests.jsonl")
    args = parser.parse_args()

    server = PaperBridgeServer(
        (args.host, args.port),
        PaperBridgeHandler,
        endpoint=args.endpoint,
        page_path=args.page,
        log_path=args.log,
    )
    print(f"Paper reading bridge: http://{args.host}:{args.port}{args.endpoint}")
    print(f"Health: http://{args.host}:{args.port}/healthz")
    print(f"Request log: {Path(args.log).expanduser()}")
    print(f"HTML page: {Path(args.page).expanduser()}")
    server.serve_forever()


if __name__ == "__main__":
    main()
