import math
import random
import re
from dataclasses import dataclass
from typing import Protocol


class RandomSource(Protocol):
    def randint(self, a: int, b: int) -> int: ...


class FormulaError(ValueError):
    pass


_NEW_FORMULA = re.compile(
    r"^\s*(-?\d+)\s*([+-])\s*(\d+)\s*[x×]\s*(\d+)\s*$",
    re.IGNORECASE,
)
_OLD_FORMULA = re.compile(
    r"^\s*(-?\d+)\s*coin\s*\[\s*(\d+)\s*\]\s*([+-])\s*(\d+)\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Formula:
    base: int
    coins: int
    modifier: int

    def __post_init__(self) -> None:
        if not 0 <= self.coins <= 5:
            raise FormulaError("No máximo 5 moedas.")

    @property
    def notation(self) -> str:
        if self.modifier < 0:
            return f"{self.base} - {self.coins}×{abs(self.modifier)}"
        return f"{self.base} + {self.coins}×{self.modifier}"

    def result(self, heads: int, bonus: int = 0) -> int:
        return max(0, self.base + heads * self.modifier + bonus)

    @property
    def minimum_damage(self) -> int:
        return min(self.result(heads) for heads in range(self.coins + 1))

    @property
    def possible_results(self) -> tuple[int, ...]:
        return tuple(
            dict.fromkeys(self.result(heads) for heads in range(self.coins + 1))
        )

    def distribution(self) -> dict[int, float]:
        total_combinations = 2**self.coins
        probabilities: dict[int, float] = {}
        for heads in range(self.coins + 1):
            outcome = self.result(heads)
            probability = math.comb(self.coins, heads) / total_combinations
            probabilities[outcome] = probabilities.get(outcome, 0.0) + probability
        return probabilities

    @property
    def average(self) -> float:
        return sum(
            outcome * probability
            for outcome, probability in self.distribution().items()
        )


def parse_formula(text: str) -> Formula:
    match = _NEW_FORMULA.fullmatch(text)
    if match:
        base, sign, coins, modifier = match.groups()
        signed_modifier = int(modifier) * (1 if sign == "+" else -1)
        return Formula(int(base), int(coins), signed_modifier)

    match = _OLD_FORMULA.fullmatch(text)
    if match:
        base, coins, sign, modifier = match.groups()
        signed_modifier = int(modifier) * (1 if sign == "+" else -1)
        return Formula(int(base), int(coins), signed_modifier)

    raise FormulaError("Use o formato 4+2x3 ou 4 coin[2]+3.")


@dataclass(frozen=True)
class RollResult:
    formula: Formula
    faces: tuple[bool, ...]
    bonus: int = 0

    @property
    def heads_positions(self) -> tuple[int, ...]:
        return tuple(index for index, heads in enumerate(self.faces, start=1) if heads)

    @property
    def heads(self) -> int:
        return len(self.heads_positions)

    @property
    def total(self) -> int:
        return self.formula.result(self.heads, self.bonus)


def roll_formula(
    formula: Formula, rng: RandomSource, bonus: int = 0
) -> RollResult:
    if bonus < 0:
        raise ValueError("O bônus não pode ser negativo.")
    faces = tuple(bool(rng.randint(0, 1)) for _ in range(formula.coins))
    return RollResult(formula=formula, faces=faces, bonus=bonus)


@dataclass(frozen=True)
class SkillTest:
    roll: RollResult
    difficulty: int
    success: bool
    deficit: int

    @property
    def can_spend_to_succeed(self) -> bool:
        return not self.success and self.deficit <= 2


def roll_skill_test(
    grade: int,
    difficulty: int,
    rng: RandomSource,
    bonus: int = 0,
) -> SkillTest:
    if grade < 0:
        raise ValueError("O grau não pode ser negativo.")
    if difficulty < 0:
        raise ValueError("A dificuldade não pode ser negativa.")
    formula = Formula(base=2 * grade, coins=3, modifier=2)
    roll = roll_formula(formula, rng, bonus)
    return SkillTest(
        roll=roll,
        difficulty=difficulty,
        success=roll.total >= difficulty,
        deficit=max(0, difficulty - roll.total),
    )


@dataclass(frozen=True)
class ClashRound:
    player: RollResult
    enemy: RollResult


@dataclass(frozen=True)
class ClashResult:
    rounds: tuple[ClashRound, ...]
    winner: str
    ties: int
    margin: int
    damage: int
    player_sp_change: int
    enemy_sp_change: int


def resolve_clash(
    player_formula: Formula,
    enemy_formula: Formula,
    rng: RandomSource,
    bonus: int = 0,
) -> ClashResult:
    if bonus < 0:
        raise ValueError("O bônus não pode ser negativo.")

    rounds: list[ClashRound] = []
    ties = 0
    while True:
        player_roll = roll_formula(player_formula, rng, bonus)
        enemy_roll = roll_formula(enemy_formula, rng)
        rounds.append(ClashRound(player=player_roll, enemy=enemy_roll))
        if player_roll.total != enemy_roll.total:
            break
        ties += 1

    winner = "player" if player_roll.total > enemy_roll.total else "enemy"
    margin = abs(player_roll.total - enemy_roll.total)
    damage = margin + ties
    sp_change = 5 + (5 if margin >= 5 else 0)
    if winner == "player":
        player_sp_change, enemy_sp_change = sp_change, -sp_change
    else:
        player_sp_change, enemy_sp_change = -sp_change, sp_change

    return ClashResult(
        rounds=tuple(rounds),
        winner=winner,
        ties=ties,
        margin=margin,
        damage=damage,
        player_sp_change=player_sp_change,
        enemy_sp_change=enemy_sp_change,
    )
