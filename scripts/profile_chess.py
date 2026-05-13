#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "chess" / "state.json"
SVG_PATH = ROOT / "assets" / "chess-board.svg"
README_PATH = ROOT / "README.md"
REPO = "eriksone225/eriksone225"

PIECES = {
    "wK": "♔", "wQ": "♕", "wR": "♖", "wB": "♗", "wN": "♘", "wP": "♙",
    "bK": "♚", "bQ": "♛", "bR": "♜", "bB": "♝", "bN": "♞", "bP": "♟",
}
FILES = "abcdefgh"

START_BOARD = [
    ["bR","bN","bB","bQ","bK","bB","bN","bR"],
    ["bP","bP","bP","bP","bP","bP","bP","bP"],
    [None,None,None,None,None,None,None,None],
    [None,None,None,None,None,None,None,None],
    [None,None,None,None,None,None,None,None],
    [None,None,None,None,None,None,None,None],
    ["wP","wP","wP","wP","wP","wP","wP","wP"],
    ["wR","wN","wB","wQ","wK","wB","wN","wR"],
]

def fresh_state():
    return {
        "board": START_BOARD,
        "turn": "w",
        "move_number": 1,
        "last_move": "",
        "history": [],
        "message": "White to move.",
    }

def load_state():
    if not STATE_PATH.exists():
        return fresh_state()
    return json.loads(STATE_PATH.read_text())

def save_state(state):
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")

def color(piece):
    return piece[0] if piece else None

def kind(piece):
    return piece[1] if piece else None

def in_bounds(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def to_coord(r, c):
    return f"{FILES[c]}{8-r}"

def from_coord(s):
    if not re.fullmatch(r"[a-h][1-8]", s):
        raise ValueError("Bad coordinate")
    c = FILES.index(s[0])
    r = 8 - int(s[1])
    return r, c

def add_slides(board, moves, r, c, piece_color, dirs):
    for dr, dc in dirs:
        nr, nc = r + dr, c + dc
        while in_bounds(nr, nc):
            target = board[nr][nc]
            if target is None:
                moves.append((nr, nc))
            else:
                if color(target) != piece_color:
                    moves.append((nr, nc))
                break
            nr += dr
            nc += dc

def piece_moves(board, r, c):
    piece = board[r][c]
    if not piece:
        return []
    pc, pk = color(piece), kind(piece)
    moves = []

    if pk == "P":
        direction = -1 if pc == "w" else 1
        start_row = 6 if pc == "w" else 1
        one = r + direction
        if in_bounds(one, c) and board[one][c] is None:
            moves.append((one, c))
            two = r + direction * 2
            if r == start_row and in_bounds(two, c) and board[two][c] is None:
                moves.append((two, c))
        for dc in (-1, 1):
            nr, nc = r + direction, c + dc
            if in_bounds(nr, nc) and board[nr][nc] and color(board[nr][nc]) != pc:
                moves.append((nr, nc))

    if pk == "N":
        for dr, dc in [(-2,-1),(-2,1),(-1,-2),(-1,2),(1,-2),(1,2),(2,-1),(2,1)]:
            nr, nc = r + dr, c + dc
            if in_bounds(nr, nc) and color(board[nr][nc]) != pc:
                moves.append((nr, nc))

    if pk == "B":
        add_slides(board, moves, r, c, pc, [(-1,-1),(-1,1),(1,-1),(1,1)])
    if pk == "R":
        add_slides(board, moves, r, c, pc, [(-1,0),(1,0),(0,-1),(0,1)])
    if pk == "Q":
        add_slides(board, moves, r, c, pc, [(-1,-1),(-1,1),(1,-1),(1,1),(-1,0),(1,0),(0,-1),(0,1)])
    if pk == "K":
        for dr, dc in [(-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)]:
            nr, nc = r + dr, c + dc
            if in_bounds(nr, nc) and color(board[nr][nc]) != pc:
                moves.append((nr, nc))
    return moves

def all_moves(state):
    board = state["board"]
    turn = state["turn"]
    result = []
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if piece and color(piece) == turn:
                for nr, nc in piece_moves(board, r, c):
                    result.append((to_coord(r, c), to_coord(nr, nc)))
    return result

def parse_move(raw):
    raw = raw.strip()
    match = re.search(r"\b([a-h][1-8])[-\s]?([a-h][1-8])\b", raw, re.I)
    if not match:
        raise ValueError("Move must look like e2e4 or e2-e4.")
    return match.group(1).lower(), match.group(2).lower()

def apply_move(state, raw_move):
    try:
        src, dst = parse_move(raw_move)
    except ValueError as exc:
        state["message"] = str(exc)
        return False

    legal = all_moves(state)
    if (src, dst) not in legal:
        state["message"] = f"Illegal move ignored: {src}-{dst}."
        return False

    sr, sc = from_coord(src)
    dr, dc = from_coord(dst)
    board = state["board"]
    moving = board[sr][sc]
    captured = board[dr][dc]

    board[dr][dc] = moving
    board[sr][sc] = None

    if moving == "wP" and dr == 0:
        board[dr][dc] = "wQ"
    if moving == "bP" and dr == 7:
        board[dr][dc] = "bQ"

    notation = f"{src}-{dst}"
    if captured:
        notation += f" x{PIECES[captured]}"
    state["last_move"] = notation
    state["history"].append(notation)
    state["turn"] = "b" if state["turn"] == "w" else "w"
    if state["turn"] == "w":
        state["move_number"] += 1
    state["message"] = f"Move applied: {notation}."
    return True

def reset_if_requested(state, raw):
    if raw and re.search(r"\breset\b", raw, re.I):
        return fresh_state(), True
    return state, False

def generate_svg(state):
    board = state["board"]
    last = state.get("last_move", "")
    last_squares = set()
    if re.match(r"^[a-h][1-8]-[a-h][1-8]", last):
        a, b = last[:2], last[3:5]
        last_squares = {a, b}

    light = "#f0d9b5"
    dark = "#b88a63"
    frame = "#222b3a"
    size = 79
    parts = [
        '<svg width="640" height="640" viewBox="0 0 640 640" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="title desc">',
        '<title id="title">Playable chess board</title>',
        '<desc id="desc">Current GitHub profile chess board position.</desc>',
        f'<rect width="640" height="640" fill="{frame}"/>',
        '<g transform="translate(4 4)">',
    ]
    for r in range(8):
        for c in range(8):
            x, y = c * size, r * size
            fill = light if (r + c) % 2 == 0 else dark
            coord = to_coord(r, c)
            parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="{fill}"/>')
            if coord in last_squares:
                parts.append(f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="#60a5fa" opacity="0.28"/>')
    parts.append('<g font-family="Georgia, Times New Roman, serif" font-size="58" font-weight="700" text-anchor="middle" dominant-baseline="middle">')
    for r in range(8):
        for c in range(8):
            piece = board[r][c]
            if not piece:
                continue
            x, y = c * size + size / 2, r * size + size / 2
            glyph = PIECES[piece]
            if color(piece) == "w":
                parts.append(f'<text x="{x}" y="{y}" fill="#ffffff" stroke="#000000" stroke-width="1">{glyph}</text>')
            else:
                parts.append(f'<text x="{x}" y="{y}" fill="#000000">{glyph}</text>')
    parts.append('</g>')
    parts.append('<g font-family="Arial, sans-serif" font-size="16" font-weight="700">')
    for r in range(8):
        fill = dark if r % 2 == 0 else light
        parts.append(f'<text x="8" y="{r*size+20}" fill="{fill}">{8-r}</text>')
    for c, f in enumerate(FILES):
        fill = light if c % 2 == 0 else dark
        parts.append(f'<text x="{c*size+60}" y="626" fill="{fill}">{f}</text>')
    parts.append('</g></g></svg>')
    SVG_PATH.parent.mkdir(parents=True, exist_ok=True)
    SVG_PATH.write_text("\n".join(parts) + "\n")

def move_link(src, dst):
    title = quote(f"chess: {src}{dst}")
    body = quote("Submit this issue to play the move. A GitHub Action will update the board in the profile README and close the issue.")
    return f"https://github.com/{REPO}/issues/new?title={title}&body={body}"

def reset_link():
    title = quote("chess: reset")
    body = quote("Submit this issue to reset the profile chess board.")
    return f"https://github.com/{REPO}/issues/new?title={title}&body={body}"

def generate_section(state):
    turn_name = "White" if state["turn"] == "w" else "Black"
    legal = all_moves(state)
    grouped = {}
    for src, dst in legal:
        grouped.setdefault(src, []).append(dst)

    buttons = []
    for src in sorted(grouped):
        for dst in sorted(grouped[src]):
            buttons.append(f'<a href="{move_link(src, dst)}"><img src="https://img.shields.io/badge/{src}-{dst}-2ea44f?style=for-the-badge" alt="{src}-{dst}" /></a>')

    buttons_html = "\n    ".join(buttons[:40])
    if len(buttons) > 40:
        buttons_html += f"\n    <br />\n    <sub>Showing first 40 legal moves out of {len(buttons)}.</sub>"

    history = ", ".join(state.get("history", [])[-10:]) or "No moves yet."
    return f'''### ♟️ Let's Play Chess!

<div align="center">
  <img src="./assets/chess-board.svg" width="500" alt="Playable chess board" />
  <br />
  <strong>{turn_name} to move</strong>
  <br />
  <sub>{state.get("message", "")}</sub>
  <br />
  <sub>Last move: {state.get("last_move") or "none"} - Move {state.get("move_number", 1)}</sub>
  <br /><br />

  {buttons_html}

  <br /><br />
  <a href="{reset_link()}"><img src="https://img.shields.io/badge/reset-board-red?style=for-the-badge" alt="Reset board" /></a>
  <br />
  <sub>How to play: click a move badge, submit the pre-filled GitHub issue, and the profile board updates automatically. GitHub READMEs cannot run live JavaScript, so this uses GitHub Actions instead.</sub>
  <br />
  <sub>Recent moves: {history}</sub>
</div>'''

def update_readme(section):
    text = README_PATH.read_text()
    pattern = re.compile(r"### ♟️ Let's Play Chess!\n\n.*?\n\n---", re.S)
    replacement = section + "\n\n---"
    if not pattern.search(text):
        raise RuntimeError("Could not find chess section in README.md")
    README_PATH.write_text(pattern.sub(replacement, text))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--move", default="")
    args = parser.parse_args()

    state = load_state()
    state, did_reset = reset_if_requested(state, args.move)
    if args.move and not did_reset:
        apply_move(state, args.move)

    save_state(state)
    generate_svg(state)
    update_readme(generate_section(state))

if __name__ == "__main__":
    main()
