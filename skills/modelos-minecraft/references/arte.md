# Arte: como um modelo de Minecraft fica bonito

Leia isto antes de desenhar a primeira peça e de novo na hora de criticar as prévias.
O objetivo é o padrão "mod caprichado / Bedrock oficial": silhueta clara, poucas cores bem
escolhidas, sombreamento intencional, pixels limpos.

## Sumário
1. Silhueta e proporções
2. Densidade (tamanho do pixel)
3. Paleta e rampas
4. Sombreamento
5. Rosto e olhos
6. Detalhes, padrões e materiais
7. Fidelidade a uma referência
8. Checklist de crítica (use a cada prévia)

---

## 1. Silhueta e proporções

- **A forma vem antes da textura.** Uma criatura tem que ser reconhecível só pela sombra preta.
  Exagere o que a define (orelhas de raposa, chifre de unicórnio, carapaça de tartaruga).
- **Poucos cubos grandes > muitos cubos pequenos.** Mob vanilla tem de 6 a 20 cubos; mod caprichado
  de 15 a 60. Cubo de 1 unidade só para detalhe (garra, dente, chifre fino).
- **Cabeças grandes = fofo; cabeças pequenas = ameaçador/realista.** Personagem fofo: cabeça
  40–60% da altura. Monstro/realista: 15–25%.
- **Escala do mundo:** 16 unidades = 1 bloco. Jogador = 32 de altura (2 blocos), cabeça 8×8×8.
  Porta = 2 blocos. Pés da criatura em y = 0. Criatura centrada em x = 0, z = 0.
- **Tamanhos inteiros** (ou múltiplos de 1/densidade). 7.3 unidades vira pixel esticado.
- **Profundidade conta:** dê espessura a orelhas (≥1), patas e caudas. Planos de espessura 0 só para
  asas/membranas/cabelo com transparência.
- **Encaixe sem frestas:** cubos vizinhos devem se tocar ou se sobrepor um pouco (0.5–1 unidade).
  Pescoço entra na cabeça; perna entra no corpo. A oclusão automática escurece essas junções.
- **Pivôs nas articulações:** o pivô do osso é onde a peça gira (ombro, quadril, base do pescoço,
  raiz da cauda). Erro clássico: pivô no centro da perna, aí a perna gira pelo meio.
- **Rotação de repouso** dá vida: cabeça inclinada 5–10°, cauda levantada ou caída, orelhas
  abertas 10–20° (`rotacao=` no osso ou no cubo).

## 2. Densidade (tamanho do pixel)

| densidade | quando usar |
|---|---|
| 1 | igual ao vanilla. Mobs comuns, blocos animados, estilo "Minecraft puro". |
| 2 | "HD" que ainda combina com o jogo. Criaturas que precisam de rosto expressivo e detalhes. **Padrão recomendado.** |
| 4 | só se o usuário pedir algo bem detalhado, ou peças pequenas (joias, olhos) — nunca misture densidades no mesmo modelo sem motivo. |

Pixel uniforme é o que separa "pixel art" de "textura borrada". Use a mesma densidade em todas as faces.

## 3. Paleta e rampas

- **Um material = uma rampa de 4 a 7 cores** (escura → clara). Ex.: pelo laranja, barriga creme,
  focinho escuro, olho. Modelos bons usam 4–8 materiais e 20–50 cores no total.
- **Desvio de matiz (hue shift):** sombra não é "a mesma cor mais escura"; ela gira para azul/roxo,
  e a luz gira para amarelo. `rampa()` faz isso sozinha. Para algo estilizado, `desvio=1.5`;
  para metal frio, `desvio=0.5`.
- **Saturação:** cores muito saturadas cansam. Meio-tons saturados, extremos menos saturados.
- **Contraste entre materiais vizinhos:** se dois materiais encostam (pelo e barriga), as cores
  base devem diferir em luminosidade (≥ 0.12 em OKLab), não só em matiz. O jogo escurece as
  laterais (~50%) e a frente (~75%): cores claras demais viram cinza, escuras demais somem.
- **Branco e preto puros quase nunca.** Branco = `#F4F4F0`; preto = `#1C1418`. Só brilho de olho
  usa `#FFFFFF`.
- **Cores de referência:** rode `paleta.py` na imagem e use as cores dela como base das rampas.

## 4. Sombreamento

O sombreamento automático (por material) já faz o básico; ajuste os parâmetros em vez de
pintar sombra à mão em todo lugar:
- `volume` (0.3–0.6): degradê dentro de cada cubo, topo claro e base escura.
- `oclusao` (0.6–1.2): escurece junções (debaixo da cabeça, entre as pernas, axilas).
- `aresta_clara` / `aresta_escura`: realce de 1 texel na borda de cima / sombra na de baixo.
  Dá leitura de volume a distância. Desligue (0) em peças muito finas.
- `ruido` 0.05–0.15 para pele/pelo/couro; 0.2–0.4 para pedra, terra, casca; 0 para metal liso,
  olhos, roupas lisas. **Ruído demais é o erro nº 1 de textura amadora.**
- `ruido_escala` 2–4 para manchas suaves (pedra, musgo, ferrugem), em vez de granulado.
- `pontilhado` 0–0.4: transição em xadrez entre tons. 0 = faixas limpas (estilo cartoon).

Sombra pintada à mão (com `onde(..., somar_luz=-1)`) para:
- sob a franja, sob a aba do chapéu, dentro da boca, dobras de roupa;
- a parte de baixo de barrigas redondas;
- **luz de borda**: 1 texel mais claro no topo de ombros, nariz, sobrancelha.

Evite **pillow shading** (escurecer todas as bordas igualmente, como uma almofada): a luz vem de
cima, então o topo clareia e a base escurece, e as laterais ficam no meio.

## 5. Rosto e olhos

O rosto é para onde todo mundo olha. Gaste tempo aqui e faça um close (`--zoom head`).
- Olhos ficam na face `north` da cabeça. Sprite desenhado como se vê de frente: `par_de_sprites`
  espelha o olho para o outro lado.
- **Estrutura de olho que lê bem** (densidade 2, 3 a 5 texels de largura):
  contorno escuro em cima (pálpebra/cílio), íris colorida com 2 tons (escuro em cima, claro
  embaixo), pupila escura, 1 texel de brilho `#FFFFFF` no alto, do mesmo lado nos dois olhos
  (não espelhe o brilho: os dois olham a mesma luz).
- Olho feroz: pálpebra diagonal descendo para o centro. Olho fofo: grande, redondo, brilho grande.
- Espaço entre os olhos ≥ 1 olho de largura em criatura fofa; menos em predador.
- Boca e focinho: 1 linha escura com cantos 1 texel acima já dá sorriso. Nariz: 2×1 escuro com 1
  texel de brilho.
- Rosto em densidade 1 é minúsculo: olho de 1×2 ou 2×2 com um único brilho já funciona.

## 6. Detalhes, padrões e materiais

- Padrões que atravessam faces (listras, manchas, faixas) devem ser 3D: `listras()`, `manchas()`,
  `entre()`, `acima()`. Assim continuam certinhos na quina. Padrões 2D (sprite, regiao) só para
  coisas que vivem numa face (olhos, emblemas, botões).
- **Pelo:** base + 1 rampa, ruído 0.1, borda de topo clara; barriga mais clara com transição em
  zigue-zague (sprite ou listras com ondulação).
- **Escamas:** padrão de meia-lua repetido (sprite pequeno) ou `listras` em 2 eixos com somar_luz
  -1; brilho de 1 texel por escama.
- **Metal:** rampa com contraste alto (`contraste=1.4`), desvio baixo, sem ruído, faixa clara forte
  perto do topo e faixa escura abaixo (reflexo), rebites de 1 texel claro + 1 escuro.
- **Pedra:** cinza levemente quente, `ruido_escala=3`, rachaduras escuras com `linha()`, musgo em
  `manchas()` só no topo (`acima`).
- **Roupa/tecido:** sem ruído, costura em linha tracejada 1 tom mais escura, dobras com somar_luz.
- **Chifres, garras, dentes:** rampa creme/osso, ponta mais clara, base mais escura (gradiente no
  eixo do comprimento).
- **Partes que brilham** (olho de golem, runas): cor saturada e clara, sem sombra (`sem_sombra=True`
  ou cor fixa). Avise que brilho real no escuro exige uma camada emissiva no código do mod.
- **Transparência** (asas membranosas, vidro, cabelo recortado): use `_` no sprite ou cor com alfa 0.
  Só alfa 0 ou 255: o jogo recorta (cutout), não mistura.

## 7. Fidelidade a uma referência

Sempre que o personagem existe fora do Minecraft, mesmo que o usuário não mande imagem
(baixe com `referencias.py`; detalhes em `referencias-e-estilo.md`):
1. Liste em texto os **traços que identificam** o personagem (5 a 10): cores principais, marcas,
   forma da cabeça, acessórios, cor dos olhos, detalhes únicos. Isso vira um checklist.
2. Rode `paleta.py` no melhor render 3D oficial (e com `--recorte` no rosto) e use as
   `rampa_manual(...)` que ele imprime.
3. Decida proporções olhando a referência (quantas "cabeças" de altura, largura do focinho etc.).
4. Depois de cada prévia, rode `comparar.py` e compare lado a lado: o que está faltando, sobrando
   ou trocado de cor? Erros de cor (barriga da cor errada, faixa a mais) e de formato da cabeça
   são os que o usuário mais nota.
5. Não invente elementos que a referência não tem. Simplifique, mas sem trocar.

## 8. Checklist de crítica (a cada prévia)

Olhe a folha de vistas, o zoom do rosto e o atlas, e responda com honestidade:
- [ ] A silhueta lê como a criatura certa nas vistas frente e lado?
- [ ] Os pés tocam o chão (y=0)? O modelo está centrado?
- [ ] Nenhum cubo flutuando ou com fresta visível; junções com sombra?
- [ ] Os olhos leem a 3 metros de distância (vista 3/4 pequena)? Brilho do mesmo lado nos dois?
- [ ] Os materiais se distinguem mesmo nas laterais escuras?
- [ ] Padrões contínuos nas quinas (listras não "pulam" de uma face para outra)?
- [ ] Ruído na medida? (`validar.py`: pixels isolados idealmente < 10%; cores < 64)
- [ ] Nenhuma face com cor errada por engano (barriga lisa onde devia ter marca etc.)?
- [ ] Comparado à referência: todos os traços do checklist presentes?
- [ ] Animação: as pernas giram no quadril (não no meio)? Nada atravessa o corpo de forma feia?

Corrija o que falhar e gere de novo. Dois ou três passes de crítica costumam separar um modelo
mediano de um bonito. Só apresente ao usuário depois disso.
