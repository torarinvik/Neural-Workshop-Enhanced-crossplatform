"""Compare Errands' deals, mail, plans, par, reference ports and play with Python."""
from pathlib import Path
from random import Random
from types import SimpleNamespace
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import browser, errands  # noqa: E402
from neural_workshop.ui import errands as ui  # noqa: E402

APPS = ("mail", "shop", "expenses")
SORTS = ("featured", "price", "rating")
SHOP_KINDS = {"back": 1, "home": 2, "cart": 3, "list": 4, "item": 5, "add": 6, "remove": 7, "checkout": 8, "placed": 9}
NOTICES = ("", "Claim filed.", "Fill in every part of the claim first.")


def shop_code(action):
    if action is None:
        return [0, 0, 0, 0, 0]
    kind = action[0]
    if kind == "list":
        return [4, action[1], action[2], SORTS.index(action[3]), 0]
    if kind in ("item", "add", "remove", "placed"):
        return [SHOP_KINDS[kind], 0, 0, 0, action[1]]
    return [SHOP_KINDS[kind], 0, 0, 0, 0]


def step_code(step):
    kind = step[0]
    if kind == "app":
        return [1, APPS.index(step[1]), *shop_code(None)]
    if kind == "done":
        return [2, 0, *shop_code(None)]
    if kind == "open":
        return [3, step[1], *shop_code(None)]
    if kind == "inbox":
        return [4, 0, *shop_code(None)]
    if kind == "shop":
        return [5, 0, *shop_code(step[1])]
    if kind == "field":
        return [6, 0 if step[1] == "order" else 1, *shop_code(None)]
    if kind == "key":
        return [7, 10 if step[1] == "del" else int(step[1]), *shop_code(None)]
    if kind == "category":
        return [8, errands.CATEGORIES.index(step[1]), *shop_code(None)]
    return [9, 0, *shop_code(None)]


def compare(rows, tag, expected, where):
    kind, *fields = next(rows).split()
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        actual = float(field) if isinstance(value, float) else int(field)
        assert actual == value, (where, tag, i, actual, value)


def read_text(rows):
    return bytes.fromhex(next(rows)).decode()


def compare_text(rows, expected, where):
    actual = read_text(rows)
    assert actual == expected, (where, actual, expected)
    return actual


def compare_deal(rows, dealt, where):
    g = dealt.level
    compare(rows, "grade", [g.rung, g.errands, int(g.shopping), g.shop_rung, g.noise, int(g.policy), int(g.amend), g.slack],
            where)
    compare(rows, "deal", [dealt.seed, len(dealt.mails), *dealt.numbers], where)
    if dealt.shop:
        shop = dealt.shop
        pairs = [value for target, category in zip(shop.targets, dealt.categories)
                 for value in (target, errands.CATEGORIES.index(category))]
        compare(rows, "shop", [shop.seed, len(shop.departments), len(shop.products), len(shop.goals), *pairs], where)
    else:
        (receipt,) = dealt.receipts
        compare(rows, "receipt", [int(receipt.order), int(receipt.amount), errands.CATEGORIES.index(receipt.category)], where)
    for index, mail in enumerate(dealt.mails):
        compare(rows, "mail", [int(mail.needed)], (where, index))
        compare_text(rows, mail.sender, (where, index))
        compare_text(rows, mail.subject, (where, index))
        compare_text(rows, mail.time, (where, index))
        body = compare_text(rows, mail.body, (where, index))
        tag, count, *bounds = next(rows).split()
        assert tag == "wrap" and int(count) == len(bounds), (where, tag)
        lines = [body.encode()[int(a):int(b)].decode() for a, b in zip(bounds[::2], bounds[1::2])]
        assert lines == errands.wrap(mail.body), (where, index, lines, errands.wrap(mail.body))


def steer(office, port):
    if port < ui.CLICK:
        dx, dy = browser.DIRECTIONS[port // 3]
        office.move(dx * browser.STEPS[port % 3], dy * browser.STEPS[port % 3])
    elif port == ui.CLICK:
        office.click()
    elif port == ui.SCROLL_UP:
        office.wheel(-1)
    elif port == ui.SCROLL_DOWN:
        office.wheel(1)


def compare_state(rows, office, port, kind, where):
    shop = office.shop
    orders = [value for order in (shop.orders if shop else []) for value in (order.number, order.total, len(order.items))]
    compare(rows, "step", [port, kind, APPS.index(office.app), -1 if office.reading is None else office.reading,
                           sum(1 << index for index in office.read), 0 if office.focus == "order" else 1,
                           -1 if office.category is None else errands.CATEGORIES.index(office.category),
                           len(office.claims), office.clicks, float(office.pointer[0]), float(office.pointer[1]),
                           int(office.done), NOTICES.index(office.notice), float(shop.scroll if shop else 0.0),
                           len(shop.cart) if shop else 0, len(shop.orders) if shop else 0,
                           *(shop_code(shop.page) if shop else [0, 0, 0, 0, 0]), *orders], where)
    compare_text(rows, office.fields["order"] + "|" + office.fields["amount"], where)


def play(rows, dealt, seed, where):
    office = errands.Office(dealt)
    rolling = seed % 2147483648
    steps = 0
    for _ in range(200):
        rolling = (rolling * 1103515245 + 12345) % 2147483648
        draw = rolling // 128
        pick = draw % 100
        port = (draw // 100) % 15
        kind = 0
        if pick < 30:
            steer(office, port)
        elif pick < 85:
            kind = 1
            targets = office.targets()
            links = []
            if office.app == "shop":
                links = [index for index, e in enumerate(office.shop.elements()) if e.action and office.shop.visible(e)]
            choice = (draw // 100) % (len(targets) + len(links) + 3)
            port = choice
            if choice < len(targets):
                action, (x, y, w, h) = targets[choice]
                if action == ("done",) and (draw // 7) % 9 != 0:
                    port = -2
                else:
                    office.click(x + w / 2, y + h / 2)
            elif choice < len(targets) + len(links):
                element = office.shop.elements()[links[choice - len(targets)]]
                x, y, w, h = office.shop.on_screen(element)
                office.click(x + w / 2, y + h / 2)
            else:
                office.click(float((draw // 7) % 1000), float((draw // 11) % 640))
        else:
            kind = 2
            port = (draw // 100) % 11
            if office.app == "expenses" and not office.done:
                office.clicks += 1
                office.do(("key", "del" if port == 10 else str(port)))
        compare_state(rows, office, port, kind, (where, steps))
        steps += 1
        if office.done:
            break
    wrong = office.mistakes()
    compare(rows, "played", [int(not wrong)], where)
    compare_text(rows, "; ".join(wrong), where)
    return steps, office.done


def scripted(rows, dealt, skip, where):
    office = errands.Office(dealt)
    steps = errands.plan(dealt)
    last_submit = max(index for index, step in enumerate(steps) if step == ("submit",))
    for index, step in enumerate(steps):
        if skip and index == last_submit:
            continue
        if step == ("done",):
            for extra in (("app", "expenses"), ("field", "order"), ("key", "4"), ("field", "amount"), ("key", "9"),
                          ("category", errands.CATEGORIES[3]), ("submit",)):
                office.clicks += 1
                office.do(extra)
        office.clicks += 1
        office.do(step)
    wrong = office.mistakes()
    compare(rows, "scripted", [int(skip), int(not wrong), len(office.claims)], where)
    return compare_text(rows, "; ".join(wrong), where)


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = steps = finished = reference_clicks = mails = 0
    kinds, said = set(), set()
    for header in rows:
        tag, rung, seed, from_run = header.split()
        assert tag == "case", header
        rung, seed, from_run = int(rung), int(seed), int(from_run)
        where = (rung, seed, from_run)
        if from_run:
            run = Random(seed)
            dealt = errands.deal(rung, rng=run)
            compare(rows, "after", [run.random()], where)
        else:
            dealt = errands.deal(rung, seed=seed)
        compare_deal(rows, dealt, where)
        mails += len(dealt.mails)
        kinds.update(mail.subject.split(" ")[0] for mail in dealt.mails)
        compare(rows, "par", [errands.fewest(dealt), errands.thorough(dealt), errands.par(dealt)], where)
        for step in errands.plan(dealt):
            compare(rows, "plan", step_code(step), where)
        start = errands.Office(dealt)
        start.pointer = [float(seed % 1000), float(rung * 20 % 640)]
        ports = ui.reference_ports(SimpleNamespace(office=start))
        compare(rows, "reference", [len(ports), *ports], where)
        replay = errands.Office(dealt)
        replay.pointer = list(start.pointer)
        for port in ports:
            steer(replay, port)
        assert replay.done and not replay.mistakes() and replay.clicks == errands.fewest(dealt), (where, replay.mistakes())
        compare(rows, "replayed", [1, 1, replay.clicks], where)
        reference_clicks += replay.clicks
        said.add(scripted(rows, dealt, False, where).split(" ", 1)[1])
        said.add(scripted(rows, dealt, True, where).split(";")[0].split(" ")[0])
        count, done = play(rows, dealt, seed * 31 + rung, where)
        steps, finished = steps + count, finished + done
        if rung % 3 == 0:
            count, done = play(rows, dealt, seed * 37 + rung + 1, where)
            steps, finished = steps + count, finished + done
        assert next(rows) == "end", where
        cases += 1
    assert cases == 140 and finished and {"claim(s) that should not be there", "no"} <= said, (cases, finished, said)
    print(f"PASS: {cases} Errands rounds match Python ({mails} mails of {len(kinds)} kinds, {reference_clicks:,} reference "
          f"clicks, {steps:,} play steps, {finished} rounds finished)")


if __name__ == "__main__":
    main(sys.argv[1])
