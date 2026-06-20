# Echoes of Desvaneio

**Echoes of Desvaneio** e um RPG de texto em Python, jogado inteiramente pelo terminal, inspirado na sensacao de uma aventura de mesa em um mundo de fantasia medieval. O foco do projeto e transformar escolhas simples de texto em uma experiencia com progressao, combate tatico, exploracao, NPCs, quests, loja, taverna, bestiario e equipamentos com identidade mecanica.

O jogo ainda esta em desenvolvimento, mas ja possui uma base jogavel e bem completa para testar com amigos.

## Como Jogar

Requisitos:

- Python 3 instalado.
- Nenhuma biblioteca externa obrigatoria.

Para iniciar:

```bash
python main.py
```

No Windows, se o comando acima nao funcionar:

```bash
py -3 main.py
```

O jogo salva o progresso em:

```text
data/core/player.json
```

Para comecar uma aventura nova, apague esse arquivo antes de abrir o jogo. Ele sera recriado automaticamente.

## Estado Atual

O projeto ja conta com:

- Criacao de personagem com classe, raca, atributos e passivas raciais.
- Sistema de nivel, XP e pontos de atributo ao subir de nivel.
- Combate por turnos com ataque, defesa, fuga, itens, habilidades fisicas e magicas.
- Mana e Estamina como recursos de habilidade.
- Condicoes de combate com resistencia em d20.
- Equipamentos com propriedades reais.
- Durabilidade de armas e armaduras.
- Loja com desconto por Carisma.
- Inventario com equipamentos separados por slot.
- Pocoes e consumiveis em combate.
- Taverna com descanso, boatos e eventos.
- Quests publicas e pedidos pessoais de NPCs.
- Eventos de exploracao e eventos urbanos.
- NPCs estruturados com memoria, rumores e pedidos.
- Bestiario progressivo.
- UI de terminal com cores ANSI, caixas e mensagens diegeticas.

## Estrutura do Projeto

```text
main.py
data/
  core/
    bestiary.json
    class.json
    exploration.json
    exploration_events.json
    npcs.json
    player.json
    quests.json
    races.json
    shops.json
    skills.json
    tavern.json
    town_events.json
  enemies/
    enemies.json
  items/
    accessories/
    armor/
    potions/
    weapons/
src/
  UI/
    bestiary.py
    character_creation.py
    combat.py
    exploration.py
    inventory.py
    npcs.py
    quests.py
    shop.py
    tavern.py
    utils/colors.py
  services/
    attribute_service.py
    bestiary_service.py
    character_service.py
    combat_service.py
    condition_service.py
    database.py
    event_service.py
    exploration_service.py
    item_service.py
    level_service.py
    npc_service.py
    quest_service.py
    shop_service.py
```

### `data/`

Guarda o conteudo do jogo em JSON: inimigos, itens, racas, classes, missoes, NPCs, eventos, taverna, bestiario e save do jogador.

### `src/UI/`

Contem os menus e telas que o jogador ve no terminal.

### `src/services/`

Contem as regras internas do jogo: combate, itens, nivel, lojas, quests, NPCs, bestiario e eventos.

## Sistemas Principais

### Criacao de Personagem

O jogador escolhe uma classe e uma raca. Classes definem atributos base e racas adicionam bonus e passivas. Depois, o jogador distribui pontos extras antes de iniciar a aventura.

### Combate

O combate usa turnos. No turno do jogador, e possivel:

- atacar com habilidades fisicas ou magicas;
- analisar o inimigo;
- usar consumiveis;
- tentar fugir.

No turno inimigo, o jogador escolhe uma postura defensiva:

- esquivar;
- bloquear;
- contra-atacar.

Atributos, passivas, condicoes, equipamentos e precisao inimiga influenciam as formulas.

### Condicoes

O jogo possui condicoes como:

- Sangrando;
- Envenenado;
- Queimando;
- Atordoado;
- Fortificado;
- Exausto;
- Silenciado;
- Corroido.

Algumas condicoes causam dano por turno, outras afetam reacoes, custos de recurso, magia ou durabilidade.

Varios efeitos podem ser resistidos com rolagem d20:

```text
d20 + modificador do atributo + bonus de equipamento >= CD
```

### Equipamentos com Propriedades

Equipamentos nao sao apenas bonus de atributo. Eles podem ter propriedades como:

- bonus de dano fisico ou magico;
- chance critica;
- dano critico;
- reducao de custo de Mana ou Estamina;
- resistencia contra condicoes;
- chance de aplicar condicao ao acertar;
- reducao de dano recebido;
- reducao de desgaste;
- bonus de ouro ou XP.

Isso faz com que duas armas do mesmo nivel possam mudar o estilo de jogo de formas diferentes.

### Quests e NPCs

O jogo separa:

- **Quadro de Missoes:** contratos publicos da vila.
- **NPCs:** pedidos pessoais, rumores e dialogos contextuais.

NPCs possuem memoria simples, afinidade, topicos de conversa e podem oferecer missoes ocultas que nao aparecem no quadro.

### Taverna

A taverna funciona como hub social:

- ouvir boatos;
- conversar com o taverneiro;
- descansar pagando ouro;
- observar eventos aleatorios.

Descansar restaura HP, Mana e Estamina.

### Bestiario

O bestiario e progressivo:

- criatura nunca vista aparece como `???`;
- criatura encontrada aparece como avistada;
- criatura derrotada revela ficha completa.

Entradas completas mostram lore, habitat, estatisticas, condicoes, taticas, preparacao e loot conhecido.

## Conteudo Atual

A vila inicial e **Phandalin**, com:

- centro comercial;
- taverna;
- quadro de missoes;
- NPCs estruturados;
- areas de exploracao;
- inimigos normais, raros e chefes.

O projeto tambem ja possui base para expansao de outras vilas, como Neverwinter.

## Como Criar Conteudo Novo

### Novo Inimigo

Edite:

```text
data/enemies/enemies.json
```

Um inimigo pode ter atributos, loot, condicao ao acertar e falas de combate.

### Novo Item

Edite um dos arquivos em:

```text
data/items/
```

Itens podem ter `modifiers` e `properties`.

### Nova Quest

Edite:

```text
data/core/quests.json
```

Quests publicas aparecem no quadro se nao tiverem `"hidden": true`. Quests pessoais de NPC devem ser ocultas e ligadas em `data/core/npcs.json`.

### Novo NPC

Edite:

```text
data/core/npcs.json
```

NPCs podem ter descricao, local, disposicao, topicos, rumores e quests pessoais.

## Validacao do Projeto

Para verificar se o codigo compila:

```bash
py -3 -m compileall src
py -3 -m py_compile main.py
```

Para validar JSONs manualmente:

```bash
py -3 -m json.tool data/core/quests.json
py -3 -m json.tool data/enemies/enemies.json
```

## Observacoes Para Quem For Jogar

Este e um projeto de RPG textual em evolucao. Algumas partes ainda podem mudar bastante, principalmente economia, balanceamento fino, novas cidades e conteudo narrativo.

Se encontrar algum comportamento estranho, vale anotar:

- o que estava fazendo;
- qual menu estava aberto;
- qual inimigo ou item estava envolvido;
- se o erro apareceu antes ou depois de salvar.

## Ideia Central

**Desvaneio** nao tenta ser um RPG grafico. Ele tenta ser uma mesa pequena dentro do terminal: texto, escolhas, risco, improviso, personagem pensando, inimigos provocando, NPCs dando pistas e o jogador montando sua propria historia a partir de sistemas simples.

