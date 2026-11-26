# Bot de Moedas — Tabuleiro de Victoria

Bot de Discord em Python 3.11+ para rolar moedas, fazer testes de perícia e resolver choques. A lógica de regras fica em `logica.py`, independente do Discord; a integração e os embeds ficam em `bot.py` e `embeds.py`.

## Regras implementadas

- Fórmulas antigas (`4 coin[2]+3`) e novas (`4+2x3`, `4 + 2×3`).
- Resultado com piso zero, máximo de cinco moedas e moedas jogadas em ordem.
- Modificador negativo, dano mínimo sem bônus e resultados/chances possíveis.
- Testes de perícia com sucesso ao empatar com a ND e aviso de conversão por 5 SP quando faltar até 2.
- Choque com re-rolagens de empate: cada empate acrescenta 1 ao dano do vencedor. O dano é a diferença final mais os extras; margem de 5 ou mais altera o SP em mais 5. O bônus informado aplica-se ao lado de quem executou o comando.
- Em produção usa `random.SystemRandom`; os testes passam um gerador com semente fixa.

## Comandos

- `/r formula [bonus] [nome]`
- `/teste grau nd [bonus]`
- `/choque voce inimigo [bonus]`
- `/chances formula`
- `/moeda`
- Atalhos: `!r 4+2x3`, `!r 4+2x3 +2` e `!t 2 8`

O bônus é um inteiro não negativo; `2` representa o bônus de apoio de Lastro/Inspirar. Resultados possíveis da fórmula e dano mínimo são exibidos sem o bônus; quando há bônus, os resultados ajustados também aparecem.

## Criar e convidar o bot

1. Acesse o [Discord Developer Portal](https://discord.com/developers/applications) e crie uma aplicação.
2. Na aplicação, abra **Bot**, crie o bot e copie o token. Mantenha-o privado.
3. Em **Installation** (ou **OAuth2 > URL Generator**), selecione os escopos `bot` e `applications.commands`. Conceda permissões para ver canais, enviar mensagens e incorporar links; para os atalhos `!r`/`!t`, ative **Message Content Intent** em **Bot > Privileged Gateway Intents**.
4. Use o link de instalação gerado para adicionar o bot ao servidor desejado.

## Executar localmente

No PowerShell, dentro desta pasta:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
Copy-Item .env.example .env
```

Edite `.env` e substitua o valor de `DISCORD_TOKEN` pelo token do bot. Depois:

```powershell
python bot.py
```

Rode os testes com:

```powershell
pytest
```

## Hospedagem 24h

Vercel é voltada a funções/serverless e não mantém uma conexão de Gateway do Discord continuamente aberta. Para 24h, escolha um serviço que mantenha um processo worker ligado:

- **Mais simples e confiável:** VPS pequena (por exemplo, Hetzner, DigitalOcean ou Linode), normalmente alguns dólares por mês; execute o bot como serviço `systemd` ou contêiner com política de reinício.
- **Opção gerenciada:** Railway ou Render com um worker persistente; confira os preços e limites atuais, pois planos gratuitos podem dormir, acabar ou deixar de estar disponíveis.
- **Grátis:** disponibilidade de instâncias gratuitas persistentes varia bastante. Verifique a política vigente do provedor antes de contar com operação contínua; uma instância que suspende por inatividade não atende ao requisito 24h.

Configure `DISCORD_TOKEN` como variável secreta no provedor, não envie o `.env` ao Git e habilite reinício automático do processo.
