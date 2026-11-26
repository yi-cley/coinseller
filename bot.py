import os
import random
import re

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from embeds import (
    chances_embed,
    clash_embeds,
    coin_embed,
    roll_embed,
    skill_test_embed,
)
from logica import (
    FormulaError,
    parse_formula,
    resolve_clash,
    roll_formula,
    roll_skill_test,
)

RNG = random.SystemRandom()
intents = discord.Intents.default()
intents.message_content = True


class VictoriaBot(commands.Bot):
    async def setup_hook(self) -> None:
        await self.tree.sync()


bot = VictoriaBot(command_prefix="!", intents=intents)


def _user_name(user: discord.abc.User) -> str:
    return user.display_name if isinstance(user, discord.Member) else user.name


def _error_embed(message: str) -> discord.Embed:
    return discord.Embed(
        title="Não consegui fazer a rolagem",
        description=message,
        colour=discord.Colour.red(),
    )


async def _send_error(
    destination: discord.Interaction | commands.Context,
    error: str,
) -> None:
    embed = _error_embed(error)
    if isinstance(destination, discord.Interaction):
        if destination.response.is_done():
            await destination.followup.send(embed=embed, ephemeral=True)
        else:
            await destination.response.send_message(embed=embed, ephemeral=True)
    else:
        await destination.reply(embed=embed)


async def _send_embeds(
    destination: discord.Interaction | commands.Context,
    embeds: list[discord.Embed],
) -> None:
    if isinstance(destination, discord.Interaction):
        await destination.response.send_message(embed=embeds[0])
        for embed in embeds[1:]:
            await destination.followup.send(embed=embed)
    else:
        for embed in embeds:
            await destination.send(embed=embed)


def _parse_text_roll_arguments(arguments: str) -> tuple[str, int]:
    arguments = arguments.strip()
    try:
        parse_formula(arguments)
        return arguments, 0
    except FormulaError:
        pass

    match = re.fullmatch(r"(.+?)\s+([+-]?\d+)", arguments)
    if not match:
        raise FormulaError("Use o formato 4+2x3 ou 4+2x3 +2.")
    formula_text, bonus_text = match.groups()
    parse_formula(formula_text)
    bonus = int(bonus_text)
    if bonus < 0:
        raise FormulaError("O bônus não pode ser negativo.")
    return formula_text, bonus


@bot.tree.command(name="r", description="Rola uma habilidade")
@app_commands.describe(
    formula="Fórmula, por exemplo 4+2x3 ou 4 coin[2]+3",
    bonus="Bônus de apoio, por exemplo 2",
    nome="Nome da habilidade (opcional)",
)
async def roll_command(
    interaction: discord.Interaction,
    formula: str,
    bonus: int = 0,
    nome: str | None = None,
) -> None:
    try:
        result = roll_formula(parse_formula(formula), RNG, bonus)
    except (FormulaError, ValueError) as error:
        await _send_error(interaction, str(error))
        return
    await interaction.response.send_message(
        embed=roll_embed(_user_name(interaction.user), result, nome)
    )


@bot.tree.command(name="teste", description="Faz um teste de perícia")
@app_commands.describe(
    grau="Grau da perícia",
    nd="Nível de dificuldade",
    bonus="Bônus de apoio, por exemplo 2",
)
async def test_command(
    interaction: discord.Interaction,
    grau: int,
    nd: int,
    bonus: int = 0,
) -> None:
    try:
        result = roll_skill_test(grau, nd, RNG, bonus)
    except ValueError as error:
        await _send_error(interaction, str(error))
        return
    await interaction.response.send_message(
        embed=skill_test_embed(_user_name(interaction.user), result)
    )


@bot.tree.command(name="choque", description="Resolve um choque entre duas habilidades")
@app_commands.describe(
    voce="Fórmula da sua habilidade",
    inimigo="Fórmula da habilidade inimiga",
    bonus="Bônus de apoio para a sua rolagem",
)
async def clash_command(
    interaction: discord.Interaction,
    voce: str,
    inimigo: str,
    bonus: int = 0,
) -> None:
    try:
        player_formula = parse_formula(voce)
        enemy_formula = parse_formula(inimigo)
        result = resolve_clash(player_formula, enemy_formula, RNG, bonus)
    except (FormulaError, ValueError) as error:
        await _send_error(interaction, str(error))
        return
    await _send_embeds(
        interaction,
        clash_embeds(
            _user_name(interaction.user),
            "Inimigo",
            player_formula,
            enemy_formula,
            result,
        )
    )


@bot.tree.command(name="chances", description="Mostra as chances sem rolar")
@app_commands.describe(formula="Fórmula, por exemplo 4+2x3")
async def chances_command(
    interaction: discord.Interaction,
    formula: str,
) -> None:
    try:
        parsed = parse_formula(formula)
    except FormulaError as error:
        await _send_error(interaction, str(error))
        return
    await interaction.response.send_message(embed=chances_embed(parsed))


@bot.tree.command(name="moeda", description="Joga uma moeda")
async def coin_command(interaction: discord.Interaction) -> None:
    heads = bool(RNG.randint(0, 1))
    await interaction.response.send_message(
        embed=coin_embed(_user_name(interaction.user), heads)
    )


@bot.command(name="r", help="Uso: !r 4+2x3 [ +2 ]")
async def text_roll_command(ctx: commands.Context, *, arguments: str) -> None:
    try:
        formula_text, bonus = _parse_text_roll_arguments(arguments)
        result = roll_formula(parse_formula(formula_text), RNG, bonus)
    except (FormulaError, ValueError) as error:
        await _send_error(ctx, str(error))
        return
    await ctx.reply(embed=roll_embed(_user_name(ctx.author), result))


@bot.command(name="t", help="Uso: !t GRAU ND [BÔNUS]")
async def text_test_command(ctx: commands.Context, *, arguments: str) -> None:
    parts = arguments.split()
    if len(parts) not in (2, 3):
        await _send_error(ctx, "Use o formato !t 2 8 [2].")
        return
    try:
        grade = int(parts[0])
        difficulty = int(parts[1])
        bonus = int(parts[2]) if len(parts) == 3 else 0
    except ValueError:
        await _send_error(ctx, "Grau, ND e bônus devem ser números.")
        return
    try:
        result = roll_skill_test(grade, difficulty, RNG, bonus)
    except ValueError as error:
        await _send_error(ctx, str(error))
        return
    await ctx.reply(embed=skill_test_embed(_user_name(ctx.author), result))
    
@bot.command(name="c", help="Uso: !c SUA_FORMULA FORMULA_INIMIGA [BÔNUS]")
async def text_clash_command(ctx: commands.Context, *, arguments: str) -> None:
    parts = arguments.split()
    if len(parts) not in (2, 3):
        await _send_error(ctx, "Use o formato !c 4+2x3 4+1x4 [2] (fórmulas sem espaços).")
        return
    try:
        bonus = int(parts[2]) if len(parts) == 3 else 0
        player_formula = parse_formula(parts[0])
        enemy_formula = parse_formula(parts[1])
        result = resolve_clash(player_formula, enemy_formula, RNG, bonus)
    except (FormulaError, ValueError) as error:
        await _send_error(ctx, str(error))
        return
    await _send_embeds(
        ctx,
        clash_embeds(_user_name(ctx.author), "Inimigo", player_formula, enemy_formula, result),
    )

@bot.event
async def on_command_error(
    ctx: commands.Context,
    error: commands.CommandError,
) -> None:
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        if ctx.command and ctx.command.name == "r":
            await _send_error(ctx, "Uso: !r 4+2x3 [ +2 ].")
            return
        if ctx.command and ctx.command.name == "t":
            await _send_error(ctx, "Uso: !t 2 8 [2].")
            return
        if ctx.command and ctx.command.name == "c":
            await _send_error(ctx, "Uso: !c 4+2x3 4+1x4 [2].")
            return
    raise error


@bot.event
async def on_ready() -> None:
    print(f"Conectado como {bot.user}")


def main() -> None:
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError(
            "Token ausente: defina DISCORD_TOKEN no arquivo .env."
        )
    bot.run(token)


if __name__ == "__main__":
    main()
