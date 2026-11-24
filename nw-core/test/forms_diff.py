"""Compare Forms' grades, deals, cards, reference typist, par and typing with forms.py."""
from pathlib import Path
from random import Random
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "original-neural-workshop-enhanced"))
from neural_workshop import forms  # noqa: E402
from neural_workshop.ui import forms as ui  # noqa: E402

KEYS = ("first", "last", "city", "email", "born", "phone", "country", "plan", "news", "work", "company")
NAMED = {forms.BACKSPACE: -1, forms.TAB: -2, forms.ENTER: -3, forms.UP: -4, forms.DOWN: -5}


def code(key):
    return NAMED[key] if key in NAMED else ord(key)


def key_of(number):
    return next((name for name, value in NAMED.items() if value == number), None) or chr(number)


def hexed(text):
    return text.encode().hex() or "-"


def compare(rows, tag, expected, where):
    kind, *fields = next(rows).split(" ")
    assert kind == tag and len(fields) == len(expected), (where, tag, kind, fields, expected)
    for i, (field, value) in enumerate(zip(fields, expected)):
        actual = field if isinstance(value, str) else (float(field) if isinstance(value, float) else int(field))
        assert actual == value, (where, tag, i, actual, value)


def text_answer(field):
    return field.answer if field.kind in ("text", "date", "digits") else ""


def index_answer(field):
    return 0 if field.kind in ("text", "date", "digits") else field.answer


def form_fields(form):
    field = form.field
    values = [form.keys, form.bounced, form.page, form.focus, KEYS.index(field.key) if field else -1, int(form.sent),
              form.lit.get("country", 0), form.cost, hexed(form.query.get("country", ""))]
    for f in form.deal.fields:
        value = form.values[f.key]
        text = isinstance(value, str)
        values += [-1 if value is None else (0 if text else value), int(f.key in form.marked), int(form._showing(f)),
                   int(forms._valid(f, value)), int(form.right(f)), hexed(value if text else "")]
    return values


def play(rows, dealt, seed, where):
    form = forms.Form(dealt)
    rolling = seed % 2147483648
    steps = 0
    for _ in range(160):
        if form.sent:
            break
        rolling = (rolling * 1103515245 + 12345) % 2147483648
        draw = rolling // 128
        kind = draw % 8
        if kind < 4:
            key = forms.reference_keys(form)
        elif kind < 6:
            key = ui.KEYS[(draw // 8) % ui.PORTS]
        elif kind == 6:
            key = chr(65 + (draw // 8) % 26)
        if kind < 7:
            compare(rows, "key", [code(key)], where)
            form.press(key)
        else:
            index = (draw // 8) % 5
            compare(rows, "click", [index], where)
            # ui.Forms.focus_on, without the screen.
            form._leave()
            form.keys += 1
            form.focus = index
        compare(rows, "form", form_fields(form), (where, steps))
        steps += 1
    compare(rows, "wrong", [len(form.wrong), *sorted(KEYS.index(f.key) for f in form.wrong)], where)
    return steps, form.sent


def main(binary):
    rows = iter(subprocess.check_output([binary], text=True).splitlines())
    cases = keys = typed = sent = 0
    letters = decoys = pages = 0
    for header in rows:
        tag, rung, seed = header.split()
        assert tag == "case", header
        rung, seed = int(rung), int(seed)
        where = (rung, seed)
        run = Random(seed)
        dealt = forms.deal(rung, rng=run)
        compare(rows, "after", [run.random()], where)
        g = dealt.level
        compare(rows, "grade", [g.rung, int("date" in g.kinds), int("digits" in g.kinds), int("choice" in g.kinds),
                                int("radio" in g.kinds), g.fields, g.pages, int(g.letter), int(g.decoys),
                                int(g.conditional), g.penalty, float(g.factor), float(g.slack)], where)
        expected = [len(dealt.fields)]
        for f in dealt.fields:
            expected += [KEYS.index(f.key), f.page, int(index_answer(f)), hexed(str(text_answer(f)))]
        compare(rows, "fields", expected, where)
        compare(rows, "card", [len(dealt.card), *map(hexed, dealt.card)], where)
        typist = forms.Form(dealt)
        pressed = []
        for _ in range(2000):
            key = forms.reference_keys(typist)
            if key is None:
                break
            pressed.append(code(key))
            typist.press(key)
        compare(rows, "reference", pressed, where)
        compare(rows, "form", form_fields(typist), where)
        assert typist.sent and not typist.wrong, where
        compare(rows, "par", [float(forms.par(dealt))], where)
        steps, done = play(rows, dealt, seed * 31 + rung, where)
        assert next(rows) == "end", where
        cases += 1
        keys += len(pressed)
        typed += steps
        sent += done
        letters += g.letter
        decoys += g.decoys
        pages += g.pages > 1
    assert cases == 31 * 8 and sent and letters and decoys and pages, (cases, sent)
    print(f"PASS: {cases} Forms deals match Python ({keys:,} reference keys, {typed:,} keys and clicks in play, "
          f"{sent} forms sent in play, {letters} letters, {pages} multi-page forms)")


if __name__ == "__main__":
    main(sys.argv[1])
