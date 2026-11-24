"""Compare Browser's deals, pages, par, reference ports and play with Python."""
from pathlib import Path
from random import Random
from types import SimpleNamespace
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import browser  # noqa: E402
from neural_workshop.ui import browser as ui  # noqa: E402

KINDS = {"back": 1, "home": 2, "cart": 3, "list": 4, "item": 5, "add": 6, "remove": 7, "checkout": 8}
SORTS = ("featured", "price", "rating")
STYLES = ("title", "text", "link", "button", "muted", "banner", "good", "bad")
CRITERIA = ("named", "cheapest", "cheapest_in_stock", "lowest_total", "rated", "best_rated")
NOTICES = ("", "Added to the cart.", "Sorry, this is out of stock.")


def code(action):
    if action is None:
        return [0, 0, 0, 0, 0]
    kind = action[0]
    if kind == "list":
        return [4, action[1], action[2], SORTS.index(action[3]), 0]
    if kind in ("item", "add", "remove"):
        return [KINDS[kind], 0, 0, 0, action[1]]
    return [KINDS[kind], 0, 0, 0, 0]


def compare(rows, tag, expected, where):
    kind, *fields = next(rows).split()
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        actual = float(field) if isinstance(value, float) else int(field)
        assert actual == value, (where, tag, i, actual, value)


def compare_text(rows, expected, where):
    actual = bytes.fromhex(next(rows)).decode()
    assert actual == expected, (where, actual, expected)


def compare_deal(rows, dealt, where):
    g = dealt.level
    compare(rows, "grade", [g.rung, g.departments, g.products, g.buys, int(g.sorting), int(g.stock),
                            int(g.shipping), int(g.paged), int(g.stale), len(g.criteria), g.slack], where)
    compare(rows, "deal", [dealt.seed, browser.SHOPS.index(dealt.shop), len(dealt.products), dealt.featured], where)
    for name in dealt.departments:
        compare(rows, "kind", [browser.KINDS.index(name)], where)
    for p in dealt.products:
        compare(rows, "product", [p.department, p.price, p.listed, int(p.stock), p.rating, p.shipping, p.pid], where)
        compare_text(rows, p.name, (where, p.pid))
    for (criterion, department), target in zip(dealt.goals, dealt.targets):
        compare(rows, "goal", [CRITERIA.index(criterion), department, target], where)
    compare_text(rows, browser.goal_words(dealt), where)


def compare_layout(rows, dealt, page, cart, notice, where):
    elements = browser.layout(dealt, page, cart, notice)
    compare(rows, "page", [len(elements), float(browser.page_height(elements)), *code(page)], (where, page))
    for e in elements:
        compare(rows, "element", [float(e.x), float(e.y), float(e.w), float(e.h), STYLES.index(e.style),
                                  *code(e.action)], (where, page, e))
        compare_text(rows, e.words, (where, page, e))
    compare_text(rows, browser.address(dealt, page), (where, page))
    compare_text(rows, ui._page_title(dealt, page), (where, page))
    return len(elements)


def compare_pages(rows, dealt, where):
    count = compare_layout(rows, dealt, ("home",), [], "", where)
    orders = SORTS if dealt.level.sorting else SORTS[:1]
    for department in range(len(dealt.departments)):
        for sort in orders:
            for number in range(browser.pages_of(dealt, department)):
                count += compare_layout(rows, dealt, ("list", department, number, sort), [], "", where)
    for product in dealt.products:
        if product.pid % 5 == 0 or product.pid == dealt.targets[0]:
            count += compare_layout(rows, dealt, ("item", product.pid), [], NOTICES[product.pid % 3], where)
    count += compare_layout(rows, dealt, ("cart",), [], "", where)
    count += compare_layout(rows, dealt, ("cart",), list(dealt.targets) + [dealt.featured], "", where)
    return count


def steer(session, port):
    if port < ui.CLICK:
        dx, dy = browser.DIRECTIONS[port // 3]
        step = browser.STEPS[port % 3]
        session.move(dx * step, dy * step)
    elif port == ui.CLICK:
        session.click()
    elif port == ui.SCROLL_UP:
        session.wheel(-1)
    elif port == ui.SCROLL_DOWN:
        session.wheel(1)


def compare_state(rows, session, port, kind, where):
    compare(rows, "step", [port, kind, float(session.scroll), float(session.pointer[0]), float(session.pointer[1]),
                           session.clicks, NOTICES.index(session.notice), int(session.checked_out),
                           len(session.history), int(session.right()), float(session.max_scroll()),
                           *code(session.page), *session.cart], where)


def play(rows, dealt, seed, offset, where):
    session = browser.Session(dealt, offset)
    state = seed % 2147483648
    steps = 0
    for _ in range(160):
        state = (state * 1103515245 + 12345) % 2147483648
        draw = state // 128
        pick = draw % 100
        kind = 0
        if pick < 35:
            port = (draw // 100) % 15
            steer(session, port)
        elif pick < 90:
            kind = 1
            links = [index for index, e in enumerate(session.elements()) if e.action and session.visible(e)]
            choice = (draw // 100) % (len(links) + 4)
            if choice < len(links):
                x, y, w, h = session.on_screen(session.elements()[links[choice]])
                port = links[choice]
                session.click(x + w / 2, y + h / 2)
            elif choice < len(links) + 3:
                (x, y, _w, _h), _action = session.chrome()[choice - len(links)]
                port = 100 + choice - len(links)
                session.click(x + 5, y + 5)
            else:
                port = 200
                session.click(500, 20)
        else:
            kind, port = 2, -1
            session.clicks += 1
            session.do(("back",))
        compare_state(rows, session, port, kind, (where, steps))
        steps += 1
        if session.checked_out:
            break
    assert next(rows) == "played", where
    return steps, session.checked_out


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = elements = steps = checkouts = reference_clicks = 0
    for header in rows:
        tag, rung, seed, from_run = header.split()
        assert tag == "case", header
        rung, seed, from_run = int(rung), int(seed), int(from_run)
        where = (rung, seed, from_run)
        if from_run:
            run = Random(seed)
            dealt = browser.deal(rung, rng=run)
            compare(rows, "after", [run.random()], where)
        else:
            dealt = browser.deal(rung, seed=seed)
        compare_deal(rows, dealt, where)
        best, path = browser.fewest(dealt)
        compare(rows, "par", [best, browser.thorough(dealt), browser.par(dealt)], where)
        for action in path:
            compare(rows, "path", code(action), where)
        elements += compare_pages(rows, dealt, where)
        ports = ui.reference_ports(SimpleNamespace(session=browser.Session(dealt)))
        compare(rows, "reference", [len(ports), *ports], where)
        replay = browser.Session(dealt)
        for port in ports:
            steer(replay, port)
        assert replay.checked_out and replay.right() and replay.clicks == best, (where, replay.clicks, best)
        compare(rows, "replayed", [1, 1, best], where)
        reference_clicks += best
        count, done = play(rows, dealt, seed * 31 + rung, 0.0, where)
        steps += count
        checkouts += done
        if rung % 4 == 0:
            count, done = play(rows, dealt, seed * 37 + rung + 1, 40.0, where)
            steps += count
            checkouts += done
        assert next(rows) == "end", where
        cases += 1
    assert cases == 146 and checkouts, (cases, checkouts)
    print(f"PASS: {cases} Browser shops match Python ({elements:,} page elements, {reference_clicks} reference "
          f"clicks, {steps:,} play steps, {checkouts} checkouts)")


if __name__ == "__main__":
    main(sys.argv[1])
