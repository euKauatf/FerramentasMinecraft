# Referências visuais e o estilo Cobblemon

Leia isto **antes de projetar** qualquer criatura que existe fora do Minecraft (Digimon, Pokémon,
personagem de anime, de jogo ou de desenho). O que mais deixa um modelo "feio e pouco parecido" é
projetar de memória. O segundo é pintar como textura de bloco em vez de como mob.

## Sumário
1. Buscar referências (obrigatório)
2. Escolher as imagens certas
3. Tirar cor e proporção da referência
4. O que os modelos do Cobblemon ensinam (números reais)
5. Técnicas do estilo Cobblemon nesta biblioteca
6. Comparar lado a lado (o loop que mais melhora o resultado)
7. Armadilhas que já aconteceram

## 1. Buscar referências (obrigatório)

```
python <skill>/scripts/referencias.py digimon Agumon --n 12
python <skill>/scripts/referencias.py cobblemon charmander totodile      # 1 a 3 parecidos no corpo
python <skill>/scripts/referencias.py lista-cobblemon saur               # procurar por nome
python <skill>/scripts/referencias.py url https://.../imagem.png nome    # qualquer outra imagem
```
Tudo vai para `D:\FerramentasMinecraft\referencias\` (nunca no C:).
- **Digimon:** baixa da Wikimon (`Category:Images_of_<Nome>`), já ordenado por utilidade: arte
  oficial, renders de modelos 3D dos jogos (`Model`, `3d`), lineart e zukan. Cartas, pôsteres e
  imagens em grupo ficam de fora. A grafia é a da Wikimon (`MetalGreymon`, `WarGreymon`).
  Gera `_contato.png` com todas lado a lado; **abra essa imagem** antes de projetar.
- **Pokémon / estilo:** baixa do repositório oficial do Cobblemon o `.geo.json`, a textura, a
  animação e a licença. Renderiza na pose idle (`_vistas.png`, `_atlas.png`) e escreve
  `_estudo.txt` (textura, cores, nº de ossos e cubos, rotações, planos).
- Licença do Cobblemon: CC BY-NC-SA. Serve para **estudar** (proporção, técnica, quantidade de
  detalhe). Não copie geometria nem textura para outro mod.
- Para Pokémon que você vai modelar, o próprio modelo do Cobblemon é a melhor referência de
  como aquela forma vira cubos. Para Digimon, escolha 1 a 3 Pokémon de corpo parecido:

| Corpo | Cobblemon para estudar |
|---|---|
| dinossauro bípede pequeno (Agumon, Guilmon) | charmander, totodile, bagon |
| dinossauro bípede médio/grande (Greymon) | charmeleon, feraligatr, tyranitar, garchomp |
| quadrúpede canino (Gabumon, Garurumon) | growlithe, arcanine, riolu (bípede), lucario |
| bolinha / bebê (Botamon, Koromon, Punimon) | ditto, jigglypuff, swablu, wooper |
| com asas (Biyomon, Patamon) | pidgey, togekiss, dragonite |
| humanoide/armadura (WarGreymon, Knightmon) | lucario, gallade, machamp, aegislash |
| inseto (Tentomon, Kabuterimon) | heracross, scizor, pinsir |

## 2. Escolher as imagens certas

Em ordem de utilidade:
1. **Render de modelo 3D oficial** (Digimon: `*_Model_*.png`, `*3d*`): mostra volume, proporção
   real e cor sem traço de desenho. É a melhor base para silhueta e paleta.
2. **Arte oficial principal** (`Agumon.jpg`): traços característicos, olhos, marcas.
3. **Lineart / zukan**: detalhes de garras, dentes e marcas.
Ignore fan art estilizada, chibi e arte de cartas para medir proporção.

## 3. Tirar cor e proporção da referência

- `paleta.py ref.png` agora imprime **rampas prontas** (`rampa_manual(...)`) com as cores de
  matiz parecido agrupadas do escuro ao claro. Use essas em vez de gerar rampa de uma cor só: as
  sombras do personagem oficial nem sempre giram para o roxo (as do Agumon continuam laranja).
- **A luz do jogo escurece**: topo ×1,0, frente/trás ×0,74, laterais ×0,5. Amarelo escurecido vira
  oliva/mostarda e azul claro vira cinza. Se a prévia parecer "suja", puxe a base para uma cor um
  pouco mais quente e saturada (amarelo → laranja-amarelo) ou suba a `base` um tom.
- **Proporção:** `comparar.py` imprime a razão altura/largura (a/l) da silhueta da referência e do
  modelo. Vista de frente: diferença maior que ~0,15 = modelo alto/estreito ou baixo/largo
  demais. Conte quantas "cabeças" de altura a referência tem (Agumon ≈ 2,5; bebês ≈ 1,3).

## 4. O que os modelos do Cobblemon ensinam (números reais)

Medidos com `referencias.py` (Charmander, Charmeleon, Totodile, Bagon):

| | Charmander | Charmeleon | Totodile | Bagon |
|---|---|---|---|---|
| textura | 64×64 | 128×64 | 128×64 | 64×32 |
| cores na textura | 22 | 23 | 41 | 25 |
| ossos / cubos | 56 / 55 | 58 / 61 | 44 / 45 | 35 / 41 |
| cubos girados | 17 | 14 | 13 | 8 |
| planos (espessura 0) | 27 | 26 | 16 | 6 |
| altura (unidades) | 21 | 28 | 23 | 18 |

O que isso quer dizer:
- **Densidade 1** (1 texel por unidade, box UV), com **poucas cores** (~20–40) e **manchas
  grandes de 2–3 tons** em vez de chuvisco ou pontilhado. A "beleza" vem da forma e da cor limpa,
  não de ruído. Para o nosso HD (densidade 2), use o estilo de material `"limpo"`.
- **Cabeça enorme** (35–45% da altura) e corpo curto. Pernas curtas e grossas.
- **Muitos ossos** (olhos, pálpebras, mandíbula, cotovelo, joelho, cada segmento de cauda):
  a animação ganha vida com piscadas, boca abrindo e cauda ondulando.
- **Planos** para tudo o que é fino: garras, dentes, chamas, pálpebras, franjas, espinhos.
- **Olhos grandes com brilho**, muitas vezes numa peça própria um pouco à frente da cabeça,
  dobrando a quina para aparecer de frente e de lado.
- **Pose de repouso em T**: braços abertos no `.geo.json`, a pose real vem da animação idle.
  (Nossa biblioteca já põe a pose natural no repouso; não precisa imitar isso.)
- Nomes de animação: `ground_idle`, `ground_walk`, `battle_idle`, `cry`, `blink`, `sleep`.

## 4b. Cor: viva e lisa (decisão do usuário)

Foi testado o visual dos mobs vanilla (cores do jogo menos saturadas + granulado de 2–3 tons,
`rampa_vanilla` + `estilo="vanilla"`, medido com `vanilla.py`). O usuário achou "muito apagado" e
"parece spray manchado" e pediu para voltar às cores vivas e lisas. Padrão: rampas da referência
oficial, `estilo="limpo"`, ruído baixo. O vanilla fica como opção só se ele pedir.

## 5. Técnicas do estilo Cobblemon nesta biblioteca

```python
m.material("pele", rampa_manual(...), estilo="limpo")   # cor viva e lisa (padrão do usuário)
m.material("garra", rampa_manual(...), estilo="liso")   # garras, dentes, olhos, metal

osso.cubo_arredondado(origem, tamanho, pintura, raio=1, arestas="todas")  # cabeça, barriga, coxa
osso.cubo_arredondado(..., arestas="frente")   # perfil oitavado; frente e laterais retas (rosto)
osso.cubo_arredondado(..., arestas="verticais")# vistas de cima oitavadas (pés, braços)
osso.cubo_arredondado(..., arestas="z")        # caudas e pescoços que vão para trás
osso.plano(origem, [0, 1, 1], pintura)         # peça fina (um lado = 0): dente, unha, chama

afinar("-y", largura_ponta=0.1, curva=0.6, apoio="-z")   # garra cônica recortada (transparente)
decalque(arte, cores, centro=[x, y, z], direcao=(0, 0, -1)) # olho/marca projetado em 3D
```
- **Rosto em "pera"**: bochechas largas embaixo e crânio mais estreito em cima, com os olhos nas
  quinas do crânio. Funciona para quase todo réptil/dinossauro fofo.
- **Olhos que dobram a quina**: dois `decalque` por olho, um com `direcao=(0,0,-1)` (parte da
  frente) e outro com `direcao=(±1,0,0)` (parte da lateral), com o mesmo `y`. Fica pixel-perfeito
  nas duas faces e o olho aparece de frente, de lado e em 3/4.
- **Dente pequeno** = plano de 1×1 unidade com sprite `"gg\ng_"` (presinha em "L"), pendurado
  logo para fora da mandíbula. Dente grande = cubo com `afinar("-y")`.
- **Garra de mão** = cubo 1×3×1,5 com `afinar("-y", largura_ponta=0.3, curva=0.5, apoio="-z")`,
  um pouco girado para a frente. **Garra de pé** = cubo 1×1,5×2 com `afinar("-z", apoio="y")`
  (fundo reto, apoiado no chão).
- **Boca que abre**: mandíbula num osso próprio (`jaw`) com pivô na articulação, `céu da boca` e
  `língua` pintados com o material da boca nas faces de dentro (`so_faces("down"/"up", ...)`).
  A animação de ataque gira a mandíbula ~30° em X.

## 6. Comparar lado a lado (o loop que mais melhora o resultado)

```
python <skill>/scripts/comparar.py X.geo.json X.png ref_modelo3d.png ref_arte.png
       --vistas 3/4,frente,esquerda --estilo D:\FerramentasMinecraft\referencias\cobblemon\0004_charmander
```
Gera `previas/X_comparacao.png`: referências | modelo em 3 vistas | um Cobblemon na mesma vista,
tudo na mesma altura. Abra e responda:
1. A silhueta de frente tem a mesma razão a/l? A cabeça tem o mesmo tamanho relativo?
2. A cabeça tem o mesmo **formato** (ex.: Agumon = bochechas largas, crânio alto, focinho curto
   e largo; não um focinho comprido de jacaré)?
3. Os traços da lista (§7 de `arte.md`) estão todos lá?
4. A cor, depois da luz do jogo, ainda lembra a da referência (sem oliva/mostarda)?
5. Comparado ao Cobblemon: o nosso tem a mesma limpeza (poucas cores, sem chuvisco) e a mesma
   "fofura" (cabeça grande, pernas curtas)?
Faça pelo menos **três** rodadas disto. No Agumon, cada rodada mudou algo grande: a 1ª deixou a
proporção atarracada, a 2ª trocou o focinho de jacaré por um curto e alto, e a 3ª fez a cabeça em pera.

## 7. Armadilhas que já aconteceram

- **Cabeça-caixa**: um cubo só para a cabeça nunca parece o personagem. Use 2–3 cubos
  arredondados (bochechas, crânio, focinho, mandíbula).
- **Focinho longo e baixo demais** vira jacaré. Meça na referência: o focinho do Agumon tem a
  largura quase da cabeça e sai pouco mais da metade do comprimento do crânio.
- **Olho tampado pelo focinho** na vista 3/4: o topo do focinho tem que ficar abaixo do olho.
- **Sobrancelhas como blocos soltos** em cima da cabeça viram "orelhas". Prefira o contorno
  escuro grosso em cima do olho, ou um calombo de 0,5 unidade.
- **Listras no meio de superfícies arredondadas**: já tratadas (as quinas internas de um
  `cubo_arredondado` não ganham realce). Se aparecer, verifique se os cubos são do mesmo grupo.
- **Rampa com `base` errada**: `rampa()`/`rampa_manual()` agora levam a base junto. Não passe
  `base=` de novo no `m.material` a menos que queira mudar.
