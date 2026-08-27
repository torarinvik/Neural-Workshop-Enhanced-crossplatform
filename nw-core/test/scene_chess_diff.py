#!/usr/bin/env python3
"""Differential harness for src/scene_chess.elisa against the REAL screen.

The position is named, not played. A `chess.Board` is emptied and the sweep's
piece table set on it directly, which reaches boards no legal game would --
and keeps python-chess's move generator, the dependency this project keeps
rather than reimplements, out of a test about drawing. The target squares are
supplied the same way, by patching `legal_moves` for the one square in hand.

SPDX-License-Identifier: GPL-2.0-or-later
"""
import sys

import scenediff

scenediff.reexec()

import chess as chesslib                                          # noqa: E402
from neural_workshop import state                                  # noqa: E402
from neural_workshop.ui.chess import Chess                         # noqa: E402

PHASES = {0: "ready", 1: "solving", 2: "solved", 3: "missed", 4: "done"}


class Posed(chesslib.Board):
    """A board whose legal moves are given rather than generated.

    `legal_moves` is a read-only property on chess.Board, so it is overridden
    here rather than assigned. Everything else -- `piece_at`, the square
    numbering, the colours -- is python-chess's own.
    """

    supplied = ()

    @property
    def legal_moves(self):
        return self.supplied


def build(spec):
    state.cfg.BLACK_BACKGROUND = bool(spec["black"])
    screen = Chess()
    board = Posed(None)                                # empty, no pieces
    targets = []
    for square in range(64):
        kind = (chesslib.PAWN + (square + spec["spec"]) % 6
                if (square * 5 + spec["spec"]) % 3 == 0 else 0)
        if kind:
            board.set_piece_at(square, chesslib.Piece(
                kind, (square + spec["spec"]) % 2 == 0))
        if (square * 3 + spec["spec"]) % 7 == 0:
            targets.append(square)
    screen.position = board
    screen.view_color = bool(spec["view_white"])
    screen.selected = None if spec["selected"] < 0 else spec["selected"]
    screen.trial = spec["trial"]
    screen.total_trials = spec["total_trials"]
    screen.phase = PHASES[spec["phase"]]
    screen.message = 'Level 3 — White to move and mate in one'
    screen.drawn = []

    # `_draw_board` reads `position.legal_moves` and keeps the moves FROM the
    # selected square. A named position is not necessarily one the generator
    # would produce moves for, so the moves are supplied instead -- the same
    # boundary tasks/chess.elisa already draws around the engine.
    if screen.selected is not None:
        board.supplied = [chesslib.Move(screen.selected, square)
                          for square in targets]
    return screen, screen._build_chrome


if __name__ == "__main__":
    sys.exit(scenediff.main(build))
