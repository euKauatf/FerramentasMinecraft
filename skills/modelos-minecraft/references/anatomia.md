# Anatomia e proporção (leia antes de qualquer criatura média ou grande)

Modelos pequenos e redondos (bebês, Agumon) perdoam anatomia errada. Criaturas grandes não: um
Greymon de pernas retas e tronco de caixa parece um boneco de blocos, por mais que a cor esteja
certa. O jeito de acertar é **montar o esqueleto primeiro** (articulações em 3D), medir na
referência e só depois vestir com cubos.

## Sumário
1. O método: medir, esqueleto, volumes, detalhes
2. Ferramentas (segmento, cadeia, silhueta)
3. Arquétipos: medidas prontas
4. Desenvolvimento entre estágios (evolução)
5. Erros que já cometemos
6. Checklist de anatomia

## 1. O método

1. **Junte vistas ortogonais.** Procure "reference art", "model sheet", "lineart", "front", "back"
   e renders de modelo 3D (`referencias.py digimon` já prioriza esses). Uma vista de **lado** é
   obrigatória para bípedes e quadrúpedes; recorte-a da folha de modelo e salve como
   `lado_*.png` na pasta da referência.
2. **Meça em H** (altura até o topo da cabeça, sem chifres/orelhas). Anote na docstring do script:
   comprimento/altura/largura da cabeça, comprimento de cada segmento de membro, onde ficam
   ombro, cotovelo, quadril, joelho, tornozelo, e o ângulo do tronco e do pescoço.
3. **Esqueleto:** escreva os pontos das articulações (quadril, joelho, tornozelo, dedos; ombro,
   cotovelo, pulso; base e pontos da cauda e do pescoço) e ligue com `segmento`/`cadeia`.
   Os ossos (`m.osso`) ficam nas articulações que animam (quadril, ombro, base da cauda, mandíbula).
4. **Volumes:** tronco e cabeça como cubos arredondados ALINHADOS aos eixos (ficam limpos em pixel
   art); a inclinação do tronco vem do degrau entre dois blocos, não de girar o bloco. Gire só
   membros, pescoço, cauda, chifres e dedos.
5. **Silhueta:** `silhueta.py` contra a vista de lado e a de frente; ataque a faixa com maior
   diferença. Repita até a forma bater (IoU sobe), sem perseguir pose (perna andando na referência
   × parada no modelo).
6. **Detalhes por último:** listras, dentes, garras, olhos, rugas, placas.

## 2. Ferramentas

```python
osso.segmento(de, ate, largura, profundidade, pintura, raio=1, arestas="y", sobra=0.5)
osso.cadeia([p0, p1, p2, ...], [(larg, prof), ...], pintura, raio=1.5, sobra=1)
```
- `segmento` gira o cubo para ir de uma articulação à outra (pivô em `de`). `sobra` estica as
  pontas para esconder a junta. Use `arestas="y"` (quinas ao longo do membro) em vez de "todas"
  quando o segmento é girado: menos "degraus" visíveis.
- `cadeia` = segmentos em sequência com seções diminuindo (cauda, pescoço, chifre curvo, tentáculo).
- `python silhueta.py X.geo.json X.png ref_lado.png --vista esquerda` → imagem azul/vermelho e
  tabela por faixa de altura ("modelo ESTREITO demais aqui"). Funciona com lineart.
- Os comprimentos são arredondados para pixel inteiro; seções (largura/profundidade) devem ser
  múltiplos de 1/densidade (0,5 em densidade 2) senão o validador avisa.

## 3. Arquétipos: medidas prontas (em H)

**Terópode digimon (Greymon, Tyranomon, Growlmon)** — tronco inclinado 30–45°, cabeça grande.
| parte | medida |
|---|---|
| cabeça | comprimento 0,42–0,5 · altura 0,3 · largura 0,4 (tão larga quanto o quadril, vista de frente) |
| pescoço | grosso (≈ largura da mandíbula), curto, 45° para a frente |
| tronco | barriga redonda saliente, quadril largo (0,45–0,5); peito mais estreito |
| braço | ombro no alto do peito; braço 0,15 para baixo e para fora; cotovelo 90°; antebraço 0,15 para a frente; mão de 3 dedos com garras |
| perna | quadril a 0,42 H; coxa enorme (largura 0,22) para baixo-frente e para FORA até o joelho; canela para trás até tornozelo alto (0,1 H); metatarso para a frente; pé 0,25 de comprimento, 3 garras + esporão |
| postura de frente | pés bem afastados (≈ largura do quadril + 2 coxas), joelhos para fora |
| cauda | base ≈ 0,3 de largura; comprimento ≈ 0,9–1,0; sai do quadril, vai para trás e sobe suave |

**Bípede fofo/rookie (Agumon, Gabumon, Guilmon)** — cabeça 0,35–0,45, corpo em pera, pernas curtas e
grossas quase retas, braços finos e compridos (até o quadril), cauda curta e grossa.

**Quadrúpede lupino (Garurumon, Gaomon quadrúpede)** — comprimento do corpo ≈ 1,6 da altura da
cernelha; cabeça 0,35 do comprimento do corpo com focinho longo; pescoço para cima-frente 30°;
patas da frente quase retas; patas de trás com jarrete (articulação para trás) no meio; cauda
longa e cheia; peito fundo e cintura fina.

**Humanoide de armadura (WarGreymon, WereGarurumon, Knightmon)** — 6–7 cabeças de altura; ombros
largos (2,5–3 cabeças) com ombreiras que passam da linha do braço; cintura estreita; pernas 0,5 H;
mãos/manoplas grandes (garras compridas = 0,15 H). Armadura é casca (cubo um pouco maior que o
membro), não um membro mais grosso.

Cabeça de humanoide-DRAGÃO (WarGreymon, WarGrowlmon, Dukemon...): mesmo de armadura e em pé, a
cabeça continua de dragão. O usuário achou "estranha, humanoide demais" uma cabeça em cubo sentada
direto no peito. Faça: PESCOÇO visível (segmento grosso saindo do peito para cima e para a frente,
~0,15 H, quase em pé: inclinado no máximo ~25°), crânio + focinho que desce para a frente (comprimento
da cabeça ≈ 1,3 × a altura). Na vista de lado, a nuca fica em cima do peito e a ponta do focinho passa
da frente do peito no máximo ~0,15 H — o usuário achou "exagerado demais" uma cabeça com o pescoço a
~35° e focinho de 1,6 × a altura,
face/mandíbula embaixo do focinho, olhos nas laterais sob a aba do capacete, chifres nascendo do
focinho e de trás do crânio, juba caindo para trás. Herde o formato do capacete do estágio anterior
(Greymon → WarGreymon).

**Bebê/bolinha (Botamon, Koromon, Punimon, Tsunomon)** — mais largo que alto (a/l 0,8–1,0 sem
orelhas), olhos grandes na metade de baixo/meio, sem pescoço.

## 4. Desenvolvimento entre estágios

A linha evolutiva tem que parecer a MESMA criatura crescendo. Ao fazer o estágio seguinte:
- **Bebê → in-training → rookie:** ganha membros; a cabeça cai de 100% para ~40% da altura.
- **Rookie → champion (Agumon → Greymon):** a cabeça cai para ~25–30% da altura mas fica mais
  LARGA; o tronco inclina para a frente; as pernas viram digitígradas com coxas enormes; os
  braços encurtam em proporção; a cauda alonga; os olhos ficam menores e bravos (pupila pequena);
  os dentes aparecem; garras ficam maiores e mais escuras; surgem marcas (listras) e peças
  (capacete, chifres) que continuam nos estágios seguintes.
- **Champion → ultimate (Greymon → MetalGreymon):** mesmo corpo do champion (reaproveite o
  script com `herdar()`), maior e mais pesado; troca/adiciona peças (capacete de metal, braço
  mecânico, asas, placa no peito). A anatomia por baixo não muda.
- **Ultimate → mega (→ WarGreymon):** costuma virar humanoide de armadura; mantém cores e marcas
  da linha (laranja, chifres do capacete, cabelo vermelho, garras).
Antes de modelar um estágio, ponha lado a lado as referências do estágio anterior e do seguinte
e anote o que se mantém (cores, marcas, formato dos olhos) e o que muda (proporção, postura).

## 5. Erros que já cometemos

- **Pernas de pilar** (cubo reto do quadril ao chão) num terópode: some a postura. Use
  quadril → joelho para a frente → tornozelo para trás → dedos.
- **Tronco de caixa em pé** num dinossauro grande: incline com dois blocos em degrau.
- **Cabeça pequena** em criatura grande: meça a largura da cabeça contra o quadril na vista de frente.
- **Listras demais**: listras de tigre são poucas (período ≈ 0,14 H), finas, interrompidas e só
  nas costas/flancos. Use `fbm` para quebrar a listra e `fator` para afinar até sumir.
- **Barriga amarela vira oliva** nas faces viradas para baixo: barriga em laranja-claro, não amarelo.
- **Degraus demais** de cubos arredondados girados em ângulos diferentes: deixe o tronco alinhado e
  use `arestas="y"` nos segmentos.
- **Dentes de 2 texels** viram retângulos: dente triangular precisa de pelo menos 4 texels de
  largura (2 unidades em densidade 2).
- **Boca fechada** em criatura brava: abra a mandíbula ~12° no osso (`rotacao`) para mostrar dentes
  e o vermelho da boca já no repouso.

### Simplicidade (o usuário reprovou um Greymon "complexo demais")
Anatomia certa NÃO é muitas peças. Na 2ª versão do Greymon cada dedo, cada gomo de chifre e
cada pedaço de focinho virou um cubo; o resultado parecia montado de sucata. Regras:
- **Uma peça por parte do corpo que alguém nomearia**: crânio, focinho, mandíbula, pescoço,
  peito, quadril, coxa, canela, pé, braço, antebraço, mão, 2–3 gomos de cauda, cada chifre em
  2 gomos. Garras e dentes podem ser vários (são pequenos e leem como um grupo).
- **Sem calombos que a referência não tem.** Cada peça precisa corresponder a algo visível no
  desenho oficial; se você não sabe dizer o que é, tire.
- **Tudo encostado**: toda peça entra um pouco na vizinha (`sobra` nos segmentos). O validador
  avisa "peça solta" quando algo não encosta em nada.
- **Um olho por lado.** Nada de olho de frente E olho na lateral separados (vira 4 olhos na vista
  3/4). Use `olhos()` (arte da frente + arte da lateral se encontrando na quina) ou só a lateral.
- **Ponta fina girada não leva `afinar`**: o recorte numa peça de 3 texels girada mostra uma
  "coluna" em cada face e vira um garfo. Ponta fina = cubo pequeno simples; use `afinar` em
  peças alinhadas aos eixos ou largas (≥ 4 texels).
- **Validador**: > 60 cubos sólidos = complexo demais para um mob (Cobblemon usa 30–60).

### Juntas (o usuário reclamou do "corpo soltando")
Segmentos girados que só se tocam na ponta deixam frestas na dobra, e blocos do tronco em degrau
deixam ver o fundo. Em toda articulação ponha uma **peça de junta** (bloco um pouco mais largo que
os dois segmentos, centrado no ponto): ombro, cotovelo, quadril (grande, costura coxa e barriga),
joelho, tornozelo e base do pescoço (costura peito, pescoço e garganta). Boca aberta precisa de um
"fundo da boca" escuro, senão dá para ver através dela de lado. Confira com `vaos.py` parado e andando.

### Sinais de rotação que já erramos (asas "para dentro", espinhos virados para a cabeça)
- Peça que aponta para CIMA no lado +X (espinho de ombreira, chifre): para inclinar para FORA use
  rotação Z **positiva** × lado (`rotacao=[0, 0, 35 * lado]`). Z negativo inclina para dentro.
- Peça que pende para BAIXO no lado +X (braço): para abrir para fora use Z **negativo** × lado.
- Asa/placa que sai das costas para o lado +X: para varrer para TRÁS use Y **negativo** × lado
  (`rotacao=[-10, -28 * lado, ...]`). Y positivo joga a asa para a frente (fica "para dentro").
- Asa precisa nascer DENTRO das costas: pivô e raiz no z da superfície das costas, com uma peça de
  encaixe que entra no tronco. Asa a 2 unidades das costas parece "descolada".
- Na dúvida, gere a vista "cima" e a "tras": elas mostram na hora se algo está virado para dentro.

### Erros do Gabumon (apontados pelo usuário)
- **Emblema/desenho de barriga entortando de lado**: decalque com `profundidade` grande pinta também as
  quinas chanfradas do `cubo_arredondado` e o desenho "quebra" na vista 3/4. Faça a barriga com
  `arestas="verticais"` (frente lisa) e o decalque com `profundidade=0.4`, do tamanho da frente lisa.
- **Vão entre o pescoço e a mandíbula**: toda cabeça precisa de um segmento de garganta/pescoço
  saindo do peito até embaixo da mandíbula, mesmo em bichos "sem pescoço".
- **Vão entre a cauda e o corpo**: a cauda começa DENTRO do quadril (ponto inicial 1–2 unidades
  dentro do tronco) e a peça das costas desce até a altura da base da cauda.
- **Dentes que somem na boca aberta (3/4)**: a mandíbula de baixo precisa ser MAIS ESTREITA que o
  focinho de cima e os dentes ficam para fora dela (presa triangular de 1,5 × 1,5 com `afinar`,
  não o "L" de 1 × 1). Senão a mandíbula tapa os dentes de lado.

### Erros do Garurumon
- **Peça "escondida" aparecendo pelas quinas**: um segmento dentro de um `cubo_arredondado` aparece nos
  cantos chanfrados como um bloco escuro (escurecido pela oclusão). Ou a peça fica toda por dentro
  da área reta, ou tire-a (no Garurumon a própria juba virou o pescoço).
- **Juba de "agulhas"**: mechas com espessura 0 ou 2 × 2 viram palitos de lado. Use mechas largas
  (≥ 4 de largura, 2,5 de espessura) saindo de uma MASSA de pelo (cubo arredondado da juba).
- **Quadrúpede comprido demais**: tronco ≈ 1,4 × a altura da perna; peito fundo.
- **"Esquelético"** (o usuário reclamou): no estilo fofo de Digimon/Pokémon os membros são GROSSOS.
  Quadrúpede médio: tronco ~13 de largura e 11 de altura; coxa traseira 6–7; braço/antebraço 5,5 / 4,5;
  pata 6 de largura; barriga cheia (sem cintura fina). Na dúvida, engorde.
- **Olho sem pupila**: todo olho precisa de pupila preta de pelo menos 2 × 2 texels e um ponto de
  brilho branco; olho só de íris some à distância. Olho de lado: 6 × 6 texels no mínimo.

### Olhos cortados (Veemon)
`decalque` só pinta faces viradas para a direção dele: se o olho passa da parte LISA da frente para a
quina chanfrada de um `cubo_arredondado`, o pedaço da quina some e o olho fica estreito, com cara de
bravo. A frente lisa mede `largura - 2 * raio`: use raio pequeno (1) na cabeça quando os olhos são
grandes, e confira se `x_centro + largura_do_olho/2 <= largura/2 - raio`.

## 6. Checklist de anatomia (junto com o de arte.md §8)

- [ ] Medidas da docstring batem com a referência (cabeça, membros, cauda)?
- [ ] Vista de lado: postura (ângulo do tronco, joelho para a frente, tornozelo para trás)?
- [ ] Vista de frente: largura da cabeça × quadril; afastamento dos pés; braços abertos ou fechados?
- [ ] `silhueta.py` lado e frente: alguma faixa com "ESTREITO/LARGO demais" que não seja pose?
- [ ] O estágio anterior e o seguinte da linha parecem a mesma criatura?
- [ ] Cada peça é uma parte nomeável e visível na referência? Nenhuma solta, nenhum olho a mais?
- [ ] Desenhos de barriga/peito legíveis também em 3/4? Dentes visíveis em 3/4? Garganta e base da cauda sem vão?
