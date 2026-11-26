#!/usr/bin/env python3
"""Static performance audit for NEWTJ main.lua.

Does not run the game. Flags old command paths that write physics every
frame or scan the whole workspace from a short loop.

Usage:
  python3 tools/perf_check.py main.lua
  python3 tools/perf_check.py main.lua --json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field


HOT_SIGNALS = ("Heartbeat", "PreRender", "RenderStepped", "Stepped")
WEIGHT = {"critical": 25, "high": 10, "medium": 4, "info": 1}


@dataclass
class Finding:
    severity: str
    code: str
    line: int
    message: str
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "code": self.code,
            "line": self.line,
            "message": self.message,
            "detail": self.detail,
        }


@dataclass
class Fn:
    name: str
    start: int
    end: int
    body: list[str] = field(default_factory=list)


def tokenize(src: str) -> list[tuple[int, str]]:
    """Lua tokens, comments dropped, strings collapsed to STR. Line is 1-based."""
    tokens: list[tuple[int, str]] = []
    i = 0
    n = len(src)
    line = 1

    def bump(ch: str) -> None:
        nonlocal line
        if ch == "\n":
            line += 1

    while i < n:
        ch = src[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        if ch.isspace():
            i += 1
            continue
        if ch == "-" and i + 1 < n and src[i + 1] == "-":
            if i + 3 < n and src[i + 2] == "[" and src[i + 3] == "[":
                i += 4
                while i + 1 < n and not (src[i] == "]" and src[i + 1] == "]"):
                    bump(src[i])
                    i += 1
                i = min(n, i + 2)
            else:
                while i < n and src[i] != "\n":
                    i += 1
            continue
        if ch in ('"', "'"):
            quote = ch
            start = line
            i += 1
            while i < n and src[i] != quote:
                if src[i] == "\\":
                    bump(src[i])
                    i += 2
                    continue
                bump(src[i])
                i += 1
            i += 1
            tokens.append((start, "STR"))
            continue
        if ch == "[" and i + 1 < n and src[i + 1] == "[":
            start = line
            i += 2
            while i + 1 < n and not (src[i] == "]" and src[i + 1] == "]"):
                bump(src[i])
                i += 1
            i = min(n, i + 2)
            tokens.append((start, "STR"))
            continue
        if ch.isalpha() or ch == "_":
            start = line
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] == "_"):
                j += 1
            tokens.append((start, src[i:j]))
            i = j
            continue
        if ch.isdigit():
            start = line
            j = i + 1
            while j < n and (src[j].isdigit() or src[j] == "."):
                j += 1
            tokens.append((start, src[i:j]))
            i = j
            continue
        if ch in ".:":
            nxt = src[i + 1] if i + 1 < n else ""
            if ch == "." and nxt == ".":
                tokens.append((line, ".."))
                i += 2
                continue
            if ch == "." and nxt.isdigit():
                j = i + 1
                while j < n and (src[j].isdigit() or src[j] == "."):
                    j += 1
                tokens.append((line, src[i:j]))
                i = j
                continue
            tokens.append((line, ch))
            i += 1
            continue
        tokens.append((line, ch))
        i += 1
    return tokens


def functions(tokens: list[tuple[int, str]], lines: list[str]) -> list[Fn]:
    found: list[Fn] = []
    # for/while use a single `end` shared with their `do`.
    stack: list[tuple[str, int, str | None]] = []
    i = 0
    while i < len(tokens):
        line, tok = tokens[i]
        if tok in ("function", "if", "while", "for", "repeat"):
            name = None
            if tok == "function":
                name = "<anon>"
                if i >= 2 and tokens[i - 1][1] == "=" and re.match(r"^[A-Za-z_]", tokens[i - 2][1]):
                    name = tokens[i - 2][1]
                elif i + 1 < len(tokens) and re.match(r"^[A-Za-z_]", tokens[i + 1][1]):
                    parts = [tokens[i + 1][1]]
                    j = i + 2
                    while j + 1 < len(tokens) and tokens[j][1] in (".", ":") and re.match(r"^[A-Za-z_]", tokens[j + 1][1]):
                        parts.append(tokens[j + 1][1])
                        j += 2
                    name = ".".join(parts)
            stack.append((tok, line, name))
        elif tok == "do":
            if not (stack and stack[-1][0] in ("for", "while")):
                stack.append(("do", line, None))
        elif tok == "until" and stack and stack[-1][0] == "repeat":
            stack.pop()
        elif tok == "end" and stack:
            kind, start, name = stack.pop()
            if kind == "function" and name:
                found.append(Fn(name, start, line, lines[start - 1 : line]))
        i += 1
    return found


def enclosing(fns: list[Fn], line: int) -> Fn | None:
    best = None
    for fn in fns:
        if fn.start <= line <= fn.end and (best is None or (fn.end - fn.start) < (best.end - best.start)):
            best = fn
    return best


def audit(src: str) -> tuple[list[Finding], dict]:
    lines = src.splitlines()
    tokens = tokenize(src)
    fns = functions(tokens, lines)
    by_name: dict[str, list[Fn]] = {}
    for fn in fns:
        by_name.setdefault(fn.name, []).append(fn)
    findings: list[Finding] = []

    binds: dict[str, list[tuple[str, int]]] = {}
    signal_at: list[tuple[int, str, str]] = []
    i = 0
    while i + 4 < len(tokens):
        line, tok = tokens[i]
        if (
            tok == "RunService"
            and tokens[i + 1][1] == "."
            and tokens[i + 2][1] in HOT_SIGNALS
            and tokens[i + 3][1] == ":"
            and tokens[i + 4][1] == "Connect"
        ):
            signal = tokens[i + 2][1]
            callee = "<anon>"
            nxt = tokens[i + 6][1] if i + 6 < len(tokens) else ""
            if tokens[i + 5][1] == "(" and re.match(r"^[A-Za-z_]", nxt) and nxt not in {"function", "if", "while", "for"}:
                callee = nxt
            binds.setdefault(callee, []).append((signal, line))
            signal_at.append((line, signal, callee))
        elif (
            tok == ":"
            and i + 3 < len(tokens)
            and tokens[i + 1][1] == "Connect"
            and tokens[i + 2][1] == "("
            and re.match(r"^[A-Za-z_]", tokens[i + 3][1])
        ):
            receiver = tokens[i - 1][1] if i else ""
            if receiver not in HOT_SIGNALS and re.search(r"preRender|Render|Heartbeat|Stepped", receiver, re.I):
                arg = tokens[i + 3][1]
                binds.setdefault(arg, []).append((receiver, line))
                signal_at.append((line, receiver, arg))
        i += 1

    for callee, spots in binds.items():
        signals = sorted({sig for sig, _ in spots})
        if len(signals) >= 2 and callee not in {"<anon>", "function"}:
            where = ", ".join(f"{sig}@{ln}" for sig, ln in spots)
            findings.append(Finding(
                "critical",
                "DOUBLE_BIND",
                spots[0][1],
                f"{callee} ถูกผูก {', '.join(signals)} พร้อมกัน — คำสั่งเดิน/เขียนตำแหน่งรันเกิน 1 ครั้งต่อเฟรม",
                where,
            ))

    def own_text(fn: Fn) -> str:
        skip: set[int] = set()
        for other in fns:
            if other is not fn and fn.start < other.start and other.end < fn.end:
                skip.update(range(other.start, other.end + 1))
        return "\n".join(lines[n - 1] for n in range(fn.start, fn.end + 1) if n not in skip)

    def smallest_caller(fn: Fn) -> Fn | None:
        if fn.name in {"<anon>", "function"}:
            return None
        best = None
        pattern = re.compile(rf"\b{re.escape(fn.name)}\s*\(")
        for other in fns:
            if other is fn:
                continue
            if not pattern.search(own_text(other)):
                continue
            span = other.end - other.start
            if best is None or span < (best.end - best.start):
                best = other
        return best

    def short_wait_near_call(caller: Fn, fn: Fn) -> str:
        pattern = re.compile(rf"\b{re.escape(fn.name)}\s*\(")
        for n in range(caller.start, caller.end + 1):
            if not pattern.search(lines[n - 1]):
                continue
            window = lines[max(caller.start, n - 30) - 1 : min(caller.end, n + 8)]
            for chunk in window:
                m = re.search(r"task\.wait\(\s*([0-9]*\.?[0-9]+)\s*\)", chunk)
                if m and float(m.group(1)) <= 0.2:
                    return f"เรียกจาก {caller.name}:{caller.start} ทุก task.wait({m.group(1)})"
        return ""

    hot_fns = set()
    for callee, spots in binds.items():
        if callee in {"<anon>", "function"}:
            continue
        for fn in by_name.get(callee, []):
            hot_fns.add(fn.start)
    for line_no, _signal, callee in signal_at:
        if callee == "<anon>":
            fn = enclosing(fns, line_no)
            if fn:
                hot_fns.add(fn.start)

    def is_hot_fn(fn: Fn) -> bool:
        if fn.start in hot_fns:
            return True
        caller = smallest_caller(fn)
        return caller is not None and caller.start in hot_fns

    for fn in fns:
        text = own_text(fn)
        if "workspace:GetDescendants" in text or "workspace:GetChildren" in text:
            caller = smallest_caller(fn)
            wait_note = short_wait_near_call(caller, fn) if caller else ""
            if wait_note or is_hot_fn(fn):
                findings.append(Finding(
                    "critical",
                    "WORKSPACE_SCAN",
                    fn.start,
                    f"{fn.name} สแกนทั้ง workspace ระหว่างที่คำสั่งเก่ายังทำงานถี่",
                    wait_note or "อยู่บนเส้น RunService",
                ))
            else:
                findings.append(Finding(
                    "medium",
                    "WORKSPACE_SCAN",
                    fn.start,
                    f"{fn.name} ใช้ workspace:GetDescendants — ต้องมีช่วงพักและห้ามเรียกทุกเฟรม",
                ))
        if "PlayerGui" in text and "GetDescendants" in text:
            findings.append(Finding(
                "medium",
                "GUI_SCAN",
                fn.start,
                f"{fn.name} เดิน PlayerGui ทั้งก้อน ควรจำป้ายที่เจอแล้วหรือสแกนไม่ถี่กว่า 1 วินาที",
            ))
        has_cframe = re.search(r"\.CFrame\s*=", text) is not None
        has_walk = ":Walk(" in text
        has_vel = "AssemblyLinearVelocity" in text
        if has_cframe and has_walk and (fn.name != "<anon>" or is_hot_fn(fn)):
            findings.append(Finding(
                "high",
                "WALK_PLUS_CFRAME",
                fn.start,
                f"{fn.name} สั่ง Walk และเขียน CFrame ในฟังก์ชันเดียวกัน — คำสั่งเก่าทับจอยสติ๊ก",
            ))
        elif has_cframe and is_hot_fn(fn) and not has_walk:
            findings.append(Finding(
                "high",
                "CFRAME_HOT",
                fn.start,
                f"{fn.name} เขียน CFrame บนเส้นที่รันทุกเฟรม",
            ))
        if has_vel and (is_hot_fn(fn) or (has_walk and fn.name != "<anon>")):
            findings.append(Finding(
                "medium",
                "VELOCITY_CLEAR",
                fn.start,
                f"{fn.name} ล้าง AssemblyLinearVelocity ซ้ำบนลูปร้อน",
            ))

    for line_no, signal, callee in signal_at:
        if callee != "<anon>":
            continue
        fn = enclosing(fns, line_no)
        if not fn:
            continue
        text = own_text(fn)
        if re.search(r"\.CFrame\s*=", text) and ":Walk(" in text:
            findings.append(Finding(
                "high",
                "WALK_PLUS_CFRAME",
                line_no,
                f"callback {signal} เขียน CFrame และเรียก Walk ในเฟรมเดียวกัน",
            ))
        elif re.search(r"\.CFrame\s*=", text):
            findings.append(Finding(
                "high",
                "CFRAME_HOT",
                line_no,
                f"callback {signal} เขียน CFrame ทุกเฟรม",
            ))

    for m in re.finditer(r"workspace\s*\.\s*DescendantAdded\s*:\s*Connect", src):
        line = src.count("\n", 0, m.start()) + 1
        findings.append(Finding(
            "medium",
            "DESCENDANT_ADDED",
            line,
            "workspace.DescendantAdded ทำให้สแกนทั้งแมพทุกครั้งที่มีโมเดลใหม่",
        ))

    # Short skill/loot poll: while + task.wait(small) + GetDescendants or FireServer in the next 40 lines.
    for idx, line in enumerate(lines):
        m = re.search(r"task\.wait\(\s*([0-9]*\.?[0-9]+)\s*\)", line)
        if not m:
            continue
        delay = float(m.group(1))
        if delay > 0.2:
            continue
        window = "\n".join(lines[max(0, idx - 25) : idx + 1])
        if "while" not in window:
            continue
        if any(float(hit) >= 0.5 for hit in re.findall(r"task\.wait\(\s*([0-9]*\.?[0-9]+)\s*\)", window)):
            continue
        if not any(token in window for token in ("GetDescendants", "FireServer", "skillFire", "farmWarp")):
            continue
        findings.append(Finding(
            "high" if "GetDescendants" in window else "medium",
            "SHORT_POLL",
            idx + 1,
            f"task.wait({delay}) ในลูปที่ยังยิงคำสั่งเก่าหรือสแกนวัตถุ",
        ))

    eps = [i for i, line in enumerate(lines, 1) if "MONSTER_VJOY_MOVE_EPS" in line]
    if len(eps) == 1:
        findings.append(Finding(
            "info",
            "UNUSED_MOVE_EPS",
            eps[0],
            "MONSTER_VJOY_MOVE_EPS ถูกประกาศแต่ไม่ถูกอ่าน อย่าเอากลับมาใช้เพื่อข้าม Humanoid:Move",
        ))

    # Connection census
    counts = {sig: 0 for sig in HOT_SIGNALS}
    counts["Alias"] = 0
    for _, sig, _ in signal_at:
        key = sig if sig in counts else "Alias"
        counts[key] = counts.get(key, 0) + 1
    counts["Connect"] = sum(1 for line in lines if ":Connect" in line)
    counts["GetDescendants"] = sum(1 for line in lines if "GetDescendants" in line)
    counts["CFrameAssign"] = sum(1 for line in lines if re.search(r"\.CFrame\s*=", line))
    counts["Walk"] = sum(1 for line in lines if ":Walk(" in line)

    # Dedupe same code+line
    uniq: list[Finding] = []
    seen = set()
    for item in findings:
        key = (item.code, item.line)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
    order = {"critical": 0, "high": 1, "medium": 2, "info": 3}
    uniq.sort(key=lambda f: (order[f.severity], f.line))
    score = sum(WEIGHT[f.severity] for f in uniq)
    summary = {
        "lines": len(lines),
        "bytes": len(src.encode("utf-8")),
        "functions": len(fns),
        "score": score,
        "counts": counts,
        "by_severity": {k: sum(1 for f in uniq if f.severity == k) for k in order},
    }
    return uniq, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="NEWTJ static performance audit")
    parser.add_argument("file", nargs="?", default="main.lua")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        src = open(args.file, encoding="utf-8", errors="replace").read()
    except OSError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 2
    findings, summary = audit(src)
    if args.json:
        json.dump({"summary": summary, "findings": [f.as_dict() for f in findings]}, sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0
    print(f"NEWTJ perf check  {args.file}")
    print(f"lines {summary['lines']}  functions {summary['functions']}  score {summary['score']}  (ต่ำกว่า = เบากว่า)")
    c = summary["counts"]
    print(
        "signals  Heartbeat {Heartbeat}  PreRender {PreRender}  RenderStepped {RenderStepped}  Stepped {Stepped}  alias {Alias}".format(
            **c
        )
    )
    print(f"Connect {c['Connect']}   GetDescendants {c['GetDescendants']}   CFrame= {c['CFrameAssign']}   Walk( {c['Walk']}")
    sev = summary["by_severity"]
    print(f"critical {sev['critical']}  high {sev['high']}  medium {sev['medium']}  info {sev['info']}")
    print()
    if not findings:
        print("PASS: no performance findings")
        return 0
    for item in findings:
        extra = f"  ({item.detail})" if item.detail else ""
        print(f"{item.severity.upper():8} {item.line:5}  {item.code:18}  {item.message}{extra}")
    print()
    print("Static perf check does not measure FPS. Confirm on device after each change.")
    return 1 if sev["critical"] or sev["high"] else 0


if __name__ == "__main__":
    sys.exit(main())
