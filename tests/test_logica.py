import random

import pytest

from logica import (
    Formula,
    FormulaError,
    parse_formula,
    resolve_clash,
    roll_skill_test,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("4 coin[2]+3", Formula(base=4, coins=2, modifier=3)),
        ("4coin[2]+3", Formula(base=4, coins=2, modifier=3)),
        ("4 coin [ 2 ] + 3", Formula(base=4, coins=2, modifier=3)),
        ("10 coin[2]-5", Formula(base=10, coins=2, modifier=-5)),
        ("4+2x3", Formula(base=4, coins=2, modifier=3)),
        ("4 + 2×3", Formula(base=4, coins=2, modifier=3)),
        ("10-2x5", Formula(base=10, coins=2, modifier=-5)),
    ],
)
def test_parse_formula_accepts_old_and_new_notation(text, expected):
    assert parse_formula(text) == expected


def test_formula_result_never_falls_below_zero():
    formula = parse_formula("10-2x5")
    assert [formula.result(heads) for heads in range(3)] == [10, 5, 0]
    assert formula.result(3) == 0


def test_formula_rejects_more_than_five_coins():
    with pytest.raises(FormulaError, match="No máximo 5 moedas"):
        parse_formula("4+6x3")


def test_negative_modifier_sets_minimum_when_all_coins_are_heads():
    formula = parse_formula("10 coin[2]-5")
    assert formula.minimum_damage == 0
    assert formula.possible_results == (10, 5, 0)


def test_skill_test_succeeds_when_result_equals_difficulty():
    test = roll_skill_test(2, 8, random.Random(0))
    assert test.roll.total == 8
    assert test.success
    assert not test.can_spend_to_succeed


def test_skill_test_warns_when_failure_is_two_points_or_less():
    test = roll_skill_test(2, 10, random.Random(0))
    assert test.roll.total == 8
    assert not test.success
    assert test.deficit == 2
    assert test.can_spend_to_succeed


def test_clash_rerolls_ties_and_adds_one_damage_per_tie():
    result = resolve_clash(
        Formula(base=0, coins=1, modifier=1),
        Formula(base=0, coins=1, modifier=1),
        random.Random(0),
    )
    assert len(result.rounds) == 2
    assert result.ties == 1
    assert result.winner == "enemy"
    assert result.margin == 1
    assert result.damage == 2
    assert result.player_sp_change == -5
    assert result.enemy_sp_change == 5
