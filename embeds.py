import discord

from logica import ClashResult, Formula, RollResult, SkillTest

NEUTRAL = discord.Colour.blurple()
SUCCESS = discord.Colour.green()
FAILURE = discord.Colour.red()


def _format_results(results: tuple[int, ...]) -> str:
    return " / ".join(str(result) for result in results)


def _format_faces(roll: RollResult) -> str:
    if not roll.faces:
        return "Nenhuma moeda"
    return "  ".join(
        f"[{position}] {'🟡' if heads else '⚫'}"
        for position, heads in enumerate(roll.faces, start=1)
    )


def _format_equation(roll: RollResult) -> str:
    heads_word = "cara" if roll.heads == 1 else "caras"
    modifier_sign = "+" if roll.formula.modifier >= 0 else "−"
    equation = (
        f"{roll.formula.base} {modifier_sign} {roll.heads} {heads_word} "
        f"× {abs(roll.formula.modifier)}"
    )
    if roll.bonus:
        equation += f" + {roll.bonus} (bônus de apoio)"
    return f"{equation} = {roll.total}"


def _add_roll_details(embed: discord.Embed, roll: RollResult) -> None:
    embed.add_field(name="Moedas", value=_format_faces(roll), inline=False)
    embed.add_field(name="Conta", value=_format_equation(roll), inline=False)
    positions = ", ".join(map(str, roll.heads_positions)) or "nenhuma"
    embed.add_field(
        name="Efeitos",
        value=f"Caras nas posições: {positions}",
        inline=False,
    )
    outcomes = _format_results(roll.formula.possible_results)
    if roll.bonus:
        adjusted = _format_results(
            tuple(
                dict.fromkeys(
                    roll.formula.result(heads, roll.bonus)
                    for heads in range(roll.formula.coins + 1)
                )
            )
        )
        outcomes += f" · Com bônus: {adjusted}"
    embed.set_footer(
        text=(
            f"Dano mínimo: {roll.formula.minimum_damage} · "
            f"Fórmula: {roll.formula.notation} ({outcomes})"
        )
    )


def roll_embed(
    roller_name: str,
    roll: RollResult,
    ability_name: str | None = None,
    colour: discord.Colour = NEUTRAL,
) -> discord.Embed:
    title = f"Rolagem de {roller_name}"
    if ability_name:
        title += f" — {ability_name}"
    embed = discord.Embed(title=title, colour=colour)
    _add_roll_details(embed, roll)
    embed.add_field(name="RESULTADO", value=f"**{roll.total}**", inline=False)
    return embed


def skill_test_embed(roller_name: str, test: SkillTest) -> discord.Embed:
    colour = SUCCESS if test.success else FAILURE
    status = "SUCESSO" if test.success else "FALHA"
    embed = discord.Embed(
        title=f"Teste de perícia — {roller_name}",
        colour=colour,
    )
    _add_roll_details(embed, test.roll)
    embed.add_field(
        name="RESULTADO",
        value=f"**{test.roll.total}** · ND {test.difficulty} — **{status}**",
        inline=False,
    )
    if test.can_spend_to_succeed:
        embed.add_field(
            name="Conversão com SP",
            value=(
                f"Faltaram {test.deficit} pontos: você pode pagar 5 SP "
                "para transformar em sucesso."
            ),
            inline=False,
        )
    return embed


def _round_text(
    number: int,
    player_name: str,
    enemy_name: str,
    player_roll: RollResult,
    enemy_roll: RollResult,
    is_tie: bool,
) -> str:
    player_positions = ", ".join(map(str, player_roll.heads_positions)) or "nenhuma"
    enemy_positions = ", ".join(map(str, enemy_roll.heads_positions)) or "nenhuma"
    player_outcome = (
        f"{player_name}: {_format_faces(player_roll)} → **{player_roll.total}**\n"
        f"Conta: {_format_equation(player_roll)}\n"
        f"Caras nas posições: {player_positions}"
    )
    enemy_outcome = (
        f"{enemy_name}: {_format_faces(enemy_roll)} → **{enemy_roll.total}**\n"
        f"Conta: {_format_equation(enemy_roll)}\n"
        f"Caras nas posições: {enemy_positions}"
    )
    label = "1ª rolagem" if number == 1 else f"Desempate {number - 1}"
    suffix = " — empate" if is_tie else ""
    return f"**{label}**\n{player_outcome}\n{enemy_outcome}{suffix}"


def clash_embeds(
    player_name: str,
    enemy_name: str,
    player_formula: Formula,
    enemy_formula: Formula,
    result: ClashResult,
) -> list[discord.Embed]:
    player_won = result.winner == "player"
    winner_name = player_name if player_won else enemy_name
    loser_name = enemy_name if player_won else player_name
    title = f"Choque — {winner_name} vence"
    colour = SUCCESS if player_won else FAILURE
    formula_footer = (
        f"Fórmulas: você {player_formula.notation} "
        f"({_format_results(player_formula.possible_results)}) · "
        f"inimigo {enemy_formula.notation} "
        f"({_format_results(enemy_formula.possible_results)})"
    )
    page_size = 10
    pages = [
        discord.Embed(
            title=title if start == 0 else f"{title} (continuação)",
            colour=colour,
        )
        for start in range(0, len(result.rounds), page_size)
    ]

    for page_index, embed in enumerate(pages):
        start = page_index * page_size
        end = min(start + page_size, len(result.rounds))
        for index in range(start, end):
            round_result = result.rounds[index]
            is_tie = round_result.player.total == round_result.enemy.total
            embed.add_field(
                name=f"Rodada {index + 1}",
                value=_round_text(
                    index + 1,
                    player_name,
                    enemy_name,
                    round_result.player,
                    round_result.enemy,
                    is_tie,
                ),
                inline=False,
            )
        if page_index == len(pages) - 1:
            embed.add_field(
                name="Resultado",
                value=(
                    f"{winner_name} anula o golpe e causa **{result.damage}** de dano "
                    f"a {loser_name} (diferença {result.margin}"
                    f"{f' + {result.ties} de empate' if result.ties else ''})."
                ),
                inline=False,
            )
            embed.add_field(
                name="SP",
                value=(
                    f"{player_name}: {result.player_sp_change:+d} · "
                    f"{enemy_name}: {result.enemy_sp_change:+d}"
                ),
                inline=False,
            )
        embed.set_footer(text=formula_footer)
    return pages


def chances_embed(formula: Formula) -> discord.Embed:
    embed = discord.Embed(
        title=f"Chances — {formula.notation}",
        colour=NEUTRAL,
    )
    distribution = formula.distribution()
    lines = [
        f"**{outcome}:** {probability * 100:.2f}%"
        for outcome, probability in sorted(distribution.items())
    ]
    embed.description = "\n".join(lines)
    embed.add_field(name="Média", value=f"{formula.average:.2f}", inline=True)
    embed.add_field(name="Moedas", value=str(formula.coins), inline=True)
    embed.set_footer(
        text=(
            f"Dano mínimo: {formula.minimum_damage} · "
            f"Resultados: {_format_results(formula.possible_results)}"
        )
    )
    return embed


def coin_embed(roller_name: str, heads: bool) -> discord.Embed:
    result = "Cara" if heads else "Coroa"
    emoji = "🟡" if heads else "⚫"
    return discord.Embed(
        title=f"Moeda de {roller_name}",
        description=f"{emoji} **{result}**",
        colour=NEUTRAL,
    )
