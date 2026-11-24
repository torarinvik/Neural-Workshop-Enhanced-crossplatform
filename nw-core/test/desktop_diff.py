"""Compare Desktop's grades and deals with desktop.py."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import desktop  # noqa: E402

FILE_KINDS = ("folder", "doc", "sheet", "image", "music")
COLOUR_NAMES = [name for name, _rgb in desktop.COLOURS]


def compare(rows, tag, expected, where):
    kind, *fields = next(rows).split(" ")
    fields = [field for field in fields if field != ""]
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        actual = field if isinstance(value, str) else (float(field) if isinstance(value, float) else int(field))
        assert actual == value, (where, tag, i, actual, value)


def grade_fields(g):
    return [g.rung, g.windows, g.tabs, g.per_tab, g.rows, len(g.kinds), g.dialogs, int(g.submenus), g.depends,
            g.applies, g.popups, g.minimised, g.closed, g.notes, g.offscreen, int(g.explorer), g.moves, g.deletes,
            g.restores, g.depth, g.desktop_files, g.ex_tabs, g.pinned, int(g.explorer_closed), g.copies,
            int(g.list_view), int(g.hide_card), g.goals, float(g.factor), float(g.slack)]


def spec_fields(spec):
    words = COLOUR_NAMES if spec.kind == "colour" else desktop.WORDS
    return [desktop.LABELS.index(spec.label), desktop.KINDS.index(spec.kind), spec.count, spec.value,
            *[words.index(word) for word in spec.words]]


def dialogs(dealt):
    found = []
    for window, window_menus in enumerate(dealt.menus):
        for menu, (_name, entries) in enumerate(window_menus):
            for item, entry in enumerate(entries):
                made = [(-1, entry[1:])] if entry[0] == "dialog" else list(enumerate(entry[2]))
                for sub, (title, members) in made:
                    found.append([desktop.DIALOGS.index(title), window, menu, item, sub, *members])
    return found


KEYS = {"explorer": 1, "trash": 2, "app": 2000000, "node": 3000000, "ex": 4000000}
NAMED = {"Open": 0, "Cut": 1, "Copy": 2, "Delete": 3, "Restore": 4, "Paste": 5, "View": 6}


def key_code(key):
    if key is None:
        return -1
    return KEYS[key[0]] + (key[1] if len(key) > 1 else 0)


def all_windows(desk):
    return desk.windows + ([desk.explorer] if desk.explorer else []) + desk.notes


def all_dialogs(desk):
    found = []
    for win in desk.windows:
        for _name, items in win.menus:
            for item in items:
                found += item.dialogs if isinstance(item, desktop.Submenu) else [item]
    return found


def at(items, item):
    return -1 if item is None else next(i for i, other in enumerate(items) if other is item)


def desk_rows(desk, dealt):
    windows = all_windows(desk)
    menu = desk.menu or (None, 0, None)
    context = desk.context
    head = [desk.clicks, int(desk.done), float(desk.pointer[0]), float(desk.pointer[1]), int(desk.held is not None),
            at(all_dialogs(desk), desk.dialog), at(windows, menu[0]), menu[1], -1 if menu[2] is None else menu[2],
            -1 if desk.dropdown is None else desk.dropdown.ident, int(desk.start_open), int(desk.start_all),
            -1 if desk.popup is None else desk.next_popup - 1, desk.next_popup]
    if context is None:
        head += [0, 0, 0, 0, 0, 0]
    else:
        what, node, win, x, y = context
        head += [1, 0 if what == "node" else 1, node.ident, at(windows, win), float(x), float(y)]
    head += [key_code(desk.picked), key_code(desk.last), key_code(getattr(desk, "_previous", None)),
             -1 if desk.clipboard is None else desk.clipboard.ident, int(desk.copying), int(desk.peeking),
             int(desk.solved)]
    rows = [("desk", head), ("order", [at(windows, win) for win in desk.order])]
    shown = []
    for win in windows:
        scroll = (list(win.scroll) + [0, 0, 0])[:3]
        shown += [float(win.x), float(win.y), win.rows, win.active, *scroll, int(win.minimised), int(win.closed)]
    rows.append(("windows", shown))
    ex = desk.explorer
    if ex is not None:
        places = [ex.place, int(ex.list_view), len(ex.places)]
        for place in ex.places:
            places += [place.path.ident, place.scroll, -1 if place.selected is None else place.selected.ident,
                       len(place.history), *[node.ident for node in place.history]]
        rows.append(("explorer", places))
    rows.append(("controls", [value for c in desk.controls for value in (c.value, c.shown)]))
    nodes = [len(desk.nodes)]
    for node in desk.nodes:
        nodes += [-1 if node.parent is None else node.parent.ident, -1 if node.origin is None else node.origin.ident]
        if node.ident >= len(dealt.files):
            nodes.append(node.name.encode().hex())
    rows.append(("nodes", nodes))
    return rows


def compare_desk(rows, desk, dealt, where):
    for tag, expected in desk_rows(desk, dealt):
        compare(rows, tag, expected, where)


def action_fields(action):
    if action is None:
        return [0, 0, 0, 0, 0]
    if action[0] == "click":
        return [1, *action[1], 0, 0]
    return [2, *action[1], *action[2]]


def reference_or_none(desk):
    """The reference's next action; None when it would press Done or, in
    a state seeded play reached, finds nothing it can do (STUCK)."""
    try:
        action = desktop.reference_action(desk)
    except AssertionError:
        return None
    return None if action is not None and action[1] is None else action


def play(rows, dealt, seed, where):
    desk = desktop.Desktop(dealt)
    rolling = seed % 2147483648
    steps = 0
    for _ in range(160):
        if desk.done:
            break
        rolling = (rolling * 1103515245 + 12345) % 2147483648
        draw = rolling // 128
        kind = draw % 10
        x, y = (draw // 16) % 200 * 5, (draw // 3200) % 128 * 5
        action = reference_or_none(desk) if kind < 5 else None
        if action is not None:
            compare(rows, "act", action_fields(action), where)
            desk.act(action)
        elif kind < 7:
            compare(rows, "click", [x, y], where)
            desk.click(x, y)
        elif kind < 9:
            win = desk.order[(draw // 7) % len(desk.order)]
            from_x, from_y = (win.x + 20.0, win.y + 10.0) if kind == 7 else (float(x), float(y))
            to_x = from_x + ((draw // 11) % 41 - 20) * 10.0
            to_y = from_y + ((draw // 13) % 41 - 20) * 10.0
            compare(rows, "drag", [from_x, from_y, to_x, to_y], where)
            desk.press(from_x, from_y)
            desk.release(to_x, to_y)
        else:
            compare(rows, "right", [x, y], where)
            desk.right_click(x, y)
        compare_desk(rows, desk, dealt, (where, steps))
        steps += 1
    return steps, desk.solved


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = files = moves = clicks = played = solves = 0
    for header in rows:
        tag, rung, seed = header.split()
        assert tag == "case", header
        rung, seed = int(rung), int(seed)
        where = (rung, seed)
        run = Random(seed)
        dealt = desktop.deal(rung, rng=run)
        compare(rows, "after", [run.random()], where)
        compare(rows, "grade", grade_fields(dealt.level), where)
        compare(rows, "titles", [desktop.TITLES.index(title) for title in dealt.titles], where)
        compare(rows, "specs", [len(dealt.specs), *[field for spec in dealt.specs for field in spec_fields(spec)]], where)
        compare(rows, "tabs", [ident for pages in dealt.tabs for page in pages for ident in page], where)
        found = dialogs(dealt)
        compare(rows, "dialogs", [len(found), *[field for made in found for field in made]], where)
        compare(rows, "applies", [int(value) for value in dealt.applies], where)
        compare(rows, "places", [value for place in dealt.places for value in place], where)
        compare(rows, "order", list(dealt.order), where)
        compare(rows, "minimised", list(dealt.minimised), where)
        compare(rows, "closed", list(dealt.closed), where)
        compare(rows, "notes", [field for text, x, y in dealt.notes for field in (desktop.NOTES.index(text), x, y)],
                where)
        compare(rows, "popups", [field for popup in dealt.popups
                                 for field in (popup.at, popup.window, int(popup.safe_left))], where)
        compare(rows, "explorer", list(dealt.explorer_at), where)
        compare(rows, "pinned", list(dealt.pinned), where)
        compare(rows, "shortcuts", list(dealt.shortcuts), where)
        compare(rows, "requires", [field for ident, (other, value) in dealt.requires for field in (ident, other, value)],
                where)
        compare(rows, "goals", [field for pair in dealt.goals for field in pair], where)
        compare(rows, "files", [len(dealt.files), *[field for name, folder, kind, parent in dealt.files
                                                    for field in (name.encode().hex(), int(folder),
                                                                  FILE_KINDS.index(kind), parent)]], where)
        compare(rows, "moves", [field for pair in dealt.moves for field in pair], where)
        compare(rows, "copies", [field for pair in dealt.copies for field in pair], where)
        compare(rows, "view", [int(dealt.list_view), int(dealt.hide_card)], where)
        desk = desktop.Desktop(dealt)
        actions = []
        for _ in range(3000):
            action = desktop.reference_action(desk)
            actions += action_fields(action)
            if action is None:
                break
            desk.act(action)
        compare(rows, "reference", actions, where)
        compare_desk(rows, desk, dealt, where)
        assert desk.solved, where
        compare(rows, "par", [float(desktop.par(dealt))], where)
        steps, solved = play(rows, dealt, seed * 31 + rung, where)
        assert next(rows) == "end", where
        clicks += desk.clicks
        played += steps
        solves += solved
        cases += 1
        files += len(dealt.files)
        moves += len(dealt.moves) + len(dealt.copies)
    assert cases == 41 * 8, cases
    print(f"PASS: {cases} Desktop deals match Python ({files:,} files and folders, {moves:,} file goals, "
          f"{clicks:,} reference clicks, {played:,} seeded actions, {solves} solved in play)")


if __name__ == "__main__":
    main(sys.argv[1])
