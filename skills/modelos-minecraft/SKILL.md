---
name: modelos-minecraft
description: Cria modelos 3D de entidades/mobs/criaturas para Minecraft (GeckoLib, Bedrock, Blockbench .geo.json) com texturas em pixel art pintadas texel a texel, animações (.animation.json) e prévias renderizadas para conferir; busca sozinha referências visuais oficiais (Wikimon para Digimon) e modelos do Cobblemon (mod de Pokémon) para estudar estilo e proporção; também texturas 2D de itens e blocos. Use SEMPRE que o usuário pedir modelo, mob, criatura, personagem, boss, pet, montaria, Digimon/Pokémon ou qualquer bicho para Minecraft, textura de entidade, skin de mob, refazer/melhorar um modelo ou textura existente, deixar um modelo "mais bonito/fiel/parecido/detalhado", reclamar que um modelo está feio ou não parece o personagem, animar um modelo GeckoLib, ou criar ícone de item/bloco em pixel art — mesmo que ele não diga "skill", "GeckoLib", "Cobblemon" ou "Blockbench".
---

# Modelos de Minecraft com pixel art de verdade

Você vai descrever o modelo em Python com a biblioteca `mcmodel` (nesta skill), gerar os arquivos,
**olhar as prévias renderizadas ao lado das referências**, criticar e repetir. A biblioteca cuida do
que é mecânico e fácil de errar (UV, orientação das faces, empacotamento da textura, oclusão nas
junções, sombreamento por rampas). Seu trabalho é o design: forma, paleta, rosto, fidelidade.

A lição mais cara até agora: **modelo feito de memória sai feio e pouco parecido**. Todo personagem
que existe fora do Minecraft começa por referências oficiais e pelo estudo de um mod que já é
bonito (Cobblemon). Leia `references/referencias-e-estilo.md` antes de projetar.

## Ambiente

A pasta base é `D:\FerramentasMinecraft` no PC principal e `C:\FerramentasMinecraft` no notebook (que
só tem C:). Os scripts acham a base sozinhos; onde aparecer `D:\FerramentasMinecraft` abaixo, use a da
máquina atual.

- Python com numpy e Pillow: `<base>\venv\Scripts\python.exe`
  (se não existir, rode `instalar.bat` na pasta da skill; tudo fica dentro da pasta base).
- Pasta da skill: `D:\FerramentasMinecraft\skills\modelos-minecraft` — chamada de `<skill>` abaixo.
- Referências baixadas: `D:\FerramentasMinecraft\referencias\` (digimon/, cobblemon/, outras/).
- Blockbench portátil (para o usuário abrir e girar o modelo): `D:\FerramentasMinecraft\Blockbench\`.
- Escreva os scripts de modelo dentro do projeto do usuário (ex. `tools/modelos/<nome>.py`), não na
  pasta da skill.

## Fluxo

1. **Buscar referências (obrigatório para personagem que já existe).**
   ```
   python <skill>/scripts/referencias.py digimon <Nome>          # arte oficial + renders 3D
   python <skill>/scripts/referencias.py cobblemon <pokemon> ...  # 1–3 de corpo parecido (tabela no guia)
   ```
   Abra `_contato.png` e o `_vistas.png` do Cobblemon. Rode `paleta.py` no melhor render 3D oficial
   (ele imprime `rampa_manual(...)` prontas). Liste por escrito 5–10 traços que identificam o
   personagem e as proporções (quantas cabeças de altura, largura do focinho, tamanho dos olhos).
   Se o usuário mandou imagens, use-as também (`paleta.py`, `comparar.py` aceitam qualquer imagem).
   Se o modelo vai para um mod, descubra a versão do GeckoLib, as pastas de assets e os nomes de
   ossos/animações que o código espera (`references/formatos.md`).
2. **Projetar antes de codar: medir e montar o esqueleto.** Para qualquer criatura média ou
   grande (champion, ultimate, mega, quadrúpede, humanoide) leia `references/anatomia.md` e siga
   o método: ache uma vista de lado e uma de frente (folhas "reference art"/"model sheet",
   lineart), meça em H (cabeça, segmentos dos membros, ângulos do tronco e do pescoço), escreva
   essas medidas na docstring do script e defina os pontos das articulações. Ficha: altura em
   unidades, densidade (padrão 2), ossos com pivôs (incluindo `jaw`, olhos ou pálpebras), cubos
   principais, materiais com as rampas da referência. Se for o estágio seguinte de uma linha,
   compare com o anterior (`anatomia.md` §4). Leia também `references/arte.md` §1–6 e
   `references/referencias-e-estilo.md` se ainda não leu nesta conversa.
3. **Escrever o script.** Parta de `<skill>/exemplos/raposa.py` e da API em `references/api.md`.
   **Cores: VIVAS e LISAS (preferência do usuário).** Rampas tiradas da referência oficial
   (`paleta.py` → `rampa_manual(...)`) com `estilo="limpo"` na pele e `estilo="liso"` em garras,
   dentes, metal e olhos. O usuário testou o granulado vanilla (`rampa_vanilla` + `estilo="vanilla"`)
   e achou "apagado" e "com spray manchado": não use, a menos que ele peça um visual vanilla.
   Técnicas de forma do Cobblemon: `cubo_arredondado` em `cubo_arredondado` em
   cabeça/barriga/coxas, `plano` para dentes e unhas, `afinar` para garras e chifres, `decalque`
   para olhos que dobram a quina. Membros dobrados, pescoço e cauda com `segmento`/`cadeia`
   (de articulação a articulação). Receitas em `references/receitas.md`.
4. **Gerar, validar e comparar.**
   ```
   python meu_modelo.py
   python <skill>/scripts/validar.py X.geo.json X.png X.animation.json
   python <skill>/scripts/previa.py X.geo.json X.png --anim X.animation.json --atlas --zoom head --quadros walk,attack
   python <skill>/scripts/comparar.py X.geo.json X.png ref3d.png refarte.png --estilo <pasta do Cobblemon>
   python <skill>/scripts/silhueta.py X.geo.json X.png ref_lado.png --vista esquerda   # e --vista frente
   python <skill>/scripts/vaos.py X.geo.json X.png --anim X.animation.json              # frestas
   ```
   ERRO no validador = conserte já. Nota de ruído alto (> 12% de pixels isolados) = baixe `ruido`.
   `vaos.py` acusa frestas (fundo aparecendo entre peças, parado e andando): feche com peça de
   junta na articulação (ombro, cotovelo, quadril, joelho, tornozelo, base do pescoço), `sobra`
   maior nos segmentos ou blocos do tronco que se sobreponham mais. O usuário nota "corpo soltando".
5. **Olhar de verdade.** Abra com a ferramenta de leitura de imagem a comparação
   (`_comparacao.png`), a folha (`_folha.png`), o close do rosto (`_zoom.png`) e os quadros da
   animação. Passe o checklist de `references/arte.md` §8 e as 5 perguntas de
   `references/referencias-e-estilo.md` §6. Escreva o que está errado, conserte, gere de novo.
   Faça **no mínimo três passes** de comparação antes de mostrar. Cada passe deve atacar o maior
   problema primeiro: postura/esqueleto → proporção (silhueta) → formato da cabeça → rosto → cor →
   detalhes. Olhe as prévias grandes (`--altura 480`) além da comparação pequena.
6. **Entregar.** Ao refazer um modelo existente, gere a versão nova numa pasta separada e mostre ao
   usuário uma imagem "antes | depois | referência" (é o que ele entende melhor); só substitua os
   arquivos do mod com o ok dele. Ao salvar no mod (`m.salvar(modelos=..., animacoes=...,
   texturas=...)`), rode o validador de novo nos arquivos finais. Diga como abrir no Blockbench.

## Regras que evitam os erros mais comuns

- A criatura olha para **-Z**; **+X é o lado esquerdo dela**; pés em y = 0; centrada em x = z = 0.
- **Orientação das faces = a do GeckoLib** (conferida no código do GeckoLib 5.5, não só no Blockbench):
  a biblioteca grava as laterais com os nomes que o GeckoLib usa ("east" do arquivo = lado -X) e o
  renderizador lê do mesmo jeito. Não troque isso à mão: antes da correção, os olhos e tudo que é
  pintado nas laterais apareciam no lado oposto e espelhados dentro do jogo.
- **Nada de faces no mesmo plano** (no jogo elas "piscam", z-fighting): `cubo_arredondado` já é feito
  de peças que não se sobrepõem, e o gerador esconde faces de enchimento ou infla de leve o cubo menor.
  O validador acusa "vão PISCAR no jogo" — trate como erro.
- Na face `north`, sprites aparecem exatamente como desenhados (é o rosto visto de frente). A
  orientação das outras faces já está calibrada contra o Blockbench/GeckoLib; não "corrija" UVs à mão.
- Tamanhos inteiros (× densidade) em todos os cubos. Mesma densidade no modelo inteiro.
- Pivô de cada osso na articulação. Pai criado antes do filho.
- Cabeça nunca é um cubo só. Cabeça grande (35–45% da altura) e pernas curtas deixam fofo;
  criaturas grandes precisam de esqueleto de verdade (joelho, tornozelo, cotovelo), ver anatomia.md.
- Poucas peças grandes, todas encostadas: uma por parte do corpo que alguém nomearia. Um olho por
  lado. Nada que a referência não tenha (ver anatomia.md, "Simplicidade").
- A luz do jogo escurece frente (×0,74) e laterais (×0,5): amarelos viram oliva. Se a prévia
  parecer suja, esquente/clareie a base.
- Cores vivas e lisas, com poucas cores (~15–40) e pouco ruído: o usuário rejeitou cor apagada e
  granulado ("spray manchado"). A forma, o rosto e as juntas fechadas é que dão o acabamento.
- Não copie geometria nem textura do Cobblemon (CC BY-NC-SA): estude e faça a sua.

## Texturas 2D (itens, blocos)

`Textura2D` usa as mesmas camadas e rampas (ver `references/api.md`). Itens: silhueta com
`contorno` e `luz_de_cima=True`. Blocos: precisam ladrilhar; use `ruido` (granulado) em vez de
`ruido_escala` e evite elementos cortados na borda.

## Arquivos da skill

- `scripts/mcmodel/` — biblioteca (modelo, pintura, cores, animação, render, textura2d)
- `scripts/referencias.py` — baixa referências (Wikimon, Cobblemon, URL) e estuda modelos prontos
- `scripts/comparar.py` — referências | modelo | Cobblemon lado a lado, com razão altura/largura
- `scripts/silhueta.py` — sobrepõe silhuetas (lado/frente) e diz em que altura o modelo erra
- `scripts/vaos.py` — acha frestas onde o fundo aparece entre as peças (repouso e animação)
- `scripts/vanilla.py` — paleta e granulado dos mobs do Minecraft (opcional; o usuário NÃO gostou como padrão)
- `scripts/previa.py`, `scripts/validar.py`, `scripts/paleta.py` — prévias, validação, paleta/rampas
- `exemplos/raposa.py` — quadrúpede completo
- `references/referencias-e-estilo.md` — busca de referências, lições do Cobblemon, loop de comparação
- `references/anatomia.md` — método do esqueleto, medidas por arquétipo, evolução entre estágios
- `references/arte.md` — princípios de arte e checklist de crítica
- `references/api.md` — referência da biblioteca
- `references/receitas.md` — olhos, bocas, padrões, materiais, asas
- `references/formatos.md` — formatos, pastas do GeckoLib por versão, Bedrock, Java, Blockbench
