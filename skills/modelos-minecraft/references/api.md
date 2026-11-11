# API do mcmodel

`from mcmodel import *` (com `scripts/` no `sys.path`). Python do ambiente:
`D:\FerramentasMinecraft\venv\Scripts\python.exe`.

## Sumário
- Modelo, ossos e cubos
- Materiais e rampas
- Camadas de pintura
- Condições (máscaras 3D)
- Contexto (para camadas próprias)
- Animações
- Render (uso direto em Python)
- Textura2D (itens e blocos)

---

## Modelo, ossos e cubos

```python
m = Modelo("nome", densidade=2)            # nome vira geometry.nome / animation.nome.*
m = Modelo("nome", densidade=2, escala=1.3)   # modelo pronto 30% maior (geometria + animação; textura igual)
m.deslocar("body", [0, 5, 0])   # move o osso e os filhos no arquivo final SEM mudar a pintura (alongar pernas)
m.material("pelo", rampa("#C8742E", n=6, base=3), ruido=0.1)
corpo = m.osso("body", pivo=[0, 12, 0])                 # pivo = ponto de rotação (articulação)
cab = m.osso("head", pivo=[0, 16, -4], pai="body", rotacao=[5, 0, 0])
cab.cubo(origem, tamanho, pintura=[...], faces={"north": [...]}, rotacao=None, pivo=None,
         inflar=0.0, ocultar=("down",))
cab.cubo_centrado(centro, tamanho, pintura=[...])       # mesmo, dado pelo centro
cab.cubo_arredondado(origem, tamanho, pintura, raio=1, arestas="todas")   # 2–3 cubos, quinas chanfradas
#   arestas: "todas" (3 cubos) | "frente"/"x" | "verticais"/"y" | "z"  (2 cubos, chanfra as
#   quinas paralelas a esse eixo). Devolve a lista de cubos. Pintura contínua entre eles; o
#   volume, local() e afinar() usam a caixa do grupo inteiro; as quinas internas não ganham realce.
cab.plano(origem, [0, 1, 1.5], pintura=[...])           # espessura 0 em um eixo: dente, unha, chama
cab.segmento(de, ate, largura, profundidade, pintura, raio=0, arestas="y", sobra=0.0)
#   cubo girado de uma articulação até a outra (pivô em `de`): coxa, canela, braço, dedo, pescoço
cab.cadeia([p0, p1, ...], [(larg, prof), ...], pintura, raio=0, sobra=0.5)
#   segmentos encadeados afinando: cauda, pescoço, chifre curvo, tentáculo (ver anatomia.md)
m.animacao("walk", duracao, {"osso": {"rotation": ..., "position": ..., "scale": ...}}, loop=True)
m.salvar(pasta)                                          # ou salvar(modelos=..., animacoes=..., texturas=...)
geo, anim, img, relatorio = m.gerar()                    # sem gravar
```

- Coordenadas absolutas do modelo (não relativas ao osso). Criatura olha para **-Z**.
- A pintura (condições, esferas, listras, decalques) usa as coordenadas como você as escreveu,
  sem a rotação dos ossos; a oclusão usa a pose real. Osso inclinado não desloca a pintura.
  **+X = lado esquerdo da criatura** (aparece à direita de quem olha o rosto). Y para cima, pés em 0.
- Crie o osso pai antes do filho. Nomes de ossos em inglês minúsculo combinam com o código de mods
  (`head`, `body`, `arm_left`...).
- `pintura` vale para as 6 faces; `faces={"north": [...]}` acrescenta camadas só naquela face
  (executadas depois das do cubo).
- `ocultar`: faces que nunca aparecem (economiza textura). Cuidado com faces que aparecem quando
  o osso anima.
- `rotacao` do cubo gira em torno de `pivo` (padrão: centro do cubo). Use para orelhas, chifres,
  espinhos inclinados. Rotação de osso gira o osso e todos os filhos.
- Ordem/sinal das rotações (graus): X+ abaixa o que aponta para frente e levanta o que aponta
  para trás; Y+ vira o focinho para a direita da criatura (-X); Z+ gira horário visto de frente.

## Materiais e rampas

```python
rampa(cor, n=6, base=None, contraste=1.0, desvio=1.0, saturar_sombras=1.0, luz_max=None, sombra_min=None)
rampa_manual("#2A1A12", "#5A3220", "#8A5230", "#B87A48", base=2)   # escura -> clara, à mão
m.material(nome, rampa, estilo=None, base=None, volume=0.45, oclusao=1.0, aresta_clara=0.6,
           aresta_escura=0.45, ruido=0.1, ruido_escala=0.0, pontilhado=0.3)
#   estilo="limpo"   (PADRÃO para pele/pelo/escama: cor viva e lisa, manchas grandes e suaves)
#   estilo="vanilla" (granulado de 2–3 tons como os mobs do jogo; o usuário achou apagado/manchado)
#   estilo="liso"    (olhos, garras, dentes, metal polido, plástico)
#   estilo="rustico" (pedra, casca, pelagem áspera: granulado fino + pontilhado)
#   kw explícitos sobrescrevem o estilo.
tom(cor, passos), misturar(c1, c2, t), luminancia(cor), hexa(cor), rgba(cor)
amostra_rampas({"pelo": r1, "barriga": r2}).save("rampas.png")   # conferir a paleta
```
rampa_vanilla(cor, n=6, base=None, croma=0.88, trava_matiz=7)   # cores reais dos mobs do jogo
#   parte da cor, tira um pouco de saturação e encaixa cada tom na cor mais próxima das texturas
#   do Minecraft (sem deixar o matiz escorregar: laranja não vira rosa). trava_matiz=4 = mais fiel.
`base` = índice da cor "normal" na rampa (luz 0). Deixe pelo menos 2 tons abaixo e 1 acima.
`rampa()` e `rampa_manual()` devolvem uma lista que lembra a própria `base`; o material usa essa
base automaticamente (não repita `base=` no `m.material`). As rampas que `paleta.py` imprime já vêm
prontas como `rampa_manual(..., base=N)`.

### Camadas de forma e projeção

```python
afinar(ponta="-y", largura_ponta=0.0, curva=1.0, apoio=None)
#   recorta o cubo (texels transparentes) em cone/cunha: garras, dentes, chifres, espinhos.
#   ponta: "-y" "+y" "-z" "+z" "-x" "+x"; curva < 1 = garra gorda; apoio="y" mantém o fundo reto.
#   Faces que ficam 100% transparentes saem do modelo sozinhas.
decalque(arte, cores, centro, direcao=(0, 0, -1), px=None, cima=(0, 1, 0), profundidade=1.5, so_frente=0.15)
#   sprite projetado em 3D a partir de `direcao`; atravessa cubos vizinhos. Para olhos que dobram a
#   quina, use dois decalques (frente com direcao (0,0,-1) e lateral com (±1,0,0)) no mesmo y.
#   Ponha na `pintura` de todos os cubos que ele pode tocar.
```

## Camadas de pintura

Cada camada é uma função `f(ctx)`. Executam em ordem; a última ganha.

| camada | o que faz |
|---|---|
| `base(mat, luz=0)` | preenche a face com o material |
| `onde(cond, mat=, luz=, somar_luz=, cor=, sem_sombra=)` | aplica onde `cond(ctx)` é verdadeiro. `cor` = cor exata (ignora sombra) |
| `gradiente(eixo, a, b, de, ate, condicao=None)` | soma luz de `de` a `ate` ao longo do eixo do mundo (0=x 1=y 2=z) |
| `sprite(arte, cores, pos=(i,j) ou centro=(s,t), espelhar=False)` | pixel art em texto (ver abaixo) |
| `par_de_sprites(arte, cores, centro_esq, centro_dir, brilho=[(i,j)])` | olhos/bochechas espelhados, brilho sem espelhar |
| `pixels([(i,j),...], valor)` | texels avulsos |
| `retangulo(i, j, w, h, valor)` / `linha(i0,j0,i1,j1, valor)` / `elipse(ci,cj,ri,rj, valor, contorno=)` | desenho em texels da face |
| `so_faces("north", camada1, ...)` | restringe camadas a certas faces |

`valor` em pixels/retangulo/linha/elipse: `"#RRGGBB"` (cor exata), `"material"` ou `("material", luz)`.

**Sprite**: cada caractere é um texel; `.` ou espaço = não mexe; `_` = transparente. `cores` mapeia
caractere → `"#hex"` (cor exata), `"material"` ou `("material", passos)`.
```python
OLHO = """
kkkk
kaak
kAAk
"""
par_de_sprites(OLHO, {"k": "#1C1418", "a": "#3A7AD0", "A": "#6AA8F0"},
               centro_esq=(0.3, 0.45), centro_dir=(0.7, 0.45), brilho=[(1, 1)])
```
Coordenadas de face: `i` da esquerda para a direita **como se vê a face de fora**, `j` de cima para
baixo. Na face `north` isso é exatamente o rosto visto de frente. Em `up`, o topo da imagem é a
parte de trás (sul) e a base é a frente.

## Condições (máscaras 3D)

`acima(y)`, `abaixo(y)`, `entre(eixo, a, b)`, `caixa(min, max)`, `esfera(centro, raio, achatar=(1,1,1))`,
`faces("north", ...)`, `local(eixo, a, b)` (0..1 dentro do cubo), `regiao(s0, t0, s1, t1)` (frações da face),
`borda_da_face(largura)`, `listras(eixo, periodo, largura, fase=0, ondulacao=0, eixo_onda=None, freq_onda=0.5, afinar=None)`,
`manchas(escala=3, limiar=0.35, semente=1)`, `sempre`.
Combinar: `e_(c1, c2)`, `ou_(c1, c2)`, `nao(c)`.

As condições 3D usam a posição de repouso do texel (com rotações aplicadas), então continuam na
quina entre faces e acompanham peças giradas.

## Contexto (para camadas próprias)

```python
def minha_camada(ctx):
    m = (ctx.y > 10) & (np.sin(ctx.x * 2) > 0.5)
    ctx.aplicar(m, mat="listra", somar_luz=-0.5)
```
Campos: `ctx.p` (h,w,3) posição, `ctx.x/y/z`, `ctx.n` normal, `ctx.face`, `ctx.i/j` (texels),
`ctx.s/t` (0..1), `ctx.w/h`, `ctx.l` (h,w,3) posição relativa no cubo, `ctx.ao` oclusão,
`ctx.mat`, `ctx.luz`, `ctx.cor`, `ctx.fixo`, `ctx.sem_sombra`. Ruído: `ruido3(p, escala, semente)`, `fbm(...)`.

## Animações

```python
onda(amplitude, periodo, fase=0, eixo=0, base=(0,0,0), deslocamento=0)   # vetor Molang senoidal
chaves({0: [0,0,0], 0.25: [-30,0,0], 0.5: [0,0,0]}, suave=True)           # quadros-chave
bipede(nomes=None, peso=1.0, passo=0.9, balanco=1.0)     # idle/walk/attack
quadrupede(nomes=None, peso=1.0, passo=0.8)
voador(nomes=None, batida=0.6)
bolinha(nomes=None)
for nome, a in quadrupede().items():
    m.animacao(nome, a["animation_length"], a["bones"], a["loop"])
```
`nomes` troca os ossos padrão (ex. `{"tail": "cauda"}`). Ossos ausentes no modelo são ignorados
pelo GeckoLib, mas o `validar.py` acusa — remova-os do dicionário se não existirem.

## Render (uso direto em Python)

```python
from mcmodel import render
render.renderizar(geo, png, vista="3/4", escala=None, extra=None).save("v.png")
render.folha(geo, png, ["frente", "3/4", "esquerda"]).save("folha.png")
render.gif(geo, png, anim_json, "walk", "walk.gif")
render.atlas(geo, png).save("atlas.png")
```
Vistas: frente, tras, esquerda, direita, 3/4, 3/4 tras, 3/4 dir, cima, baixo, ou `(yaw, pitch)`.
`geo`/`png` podem ser caminhos ou objetos (dict/PIL). A iluminação imita a das entidades no jogo
(frente ~75%, laterais ~50%, topo 100%).

## Textura2D (itens e blocos)

```python
t = Textura2D("rubi", 16, 16)
t.material("gema", rampa("#D0213A", n=6, base=3), pontilhado=0, ruido=0)
img = t.pintar(sprite(ARTE, {"g": "gema"}), gradiente(1, 2, 13, -1.2, 1.2),
               contorno="#4A0816", luz_de_cima=True)
```
Pixels não pintados ficam transparentes. Bloco: comece com `base("pedra")` e use `ruido` maior.
`contorno` = cor da linha da silhueta ou número negativo (escurecer dentro da rampa).
