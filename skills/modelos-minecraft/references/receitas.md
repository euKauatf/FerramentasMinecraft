# Receitas prontas (copie e ajuste)

Todas testadas com `densidade=2`. Coordenadas de sprite em texels da face.

## Olhos

```python
# Fofo/grande (5x5): contorno, íris em 2 tons, pupila; brilho aplicado sem espelhar
OLHO_FOFO = """
.kkk.
kaaak
kaPak
kAAAk
.kkk.
"""
cores = {"k": "#1C1418", "a": "#2E6FD0", "A": "#6FB0F5", "P": "#0E0A14"}
par_de_sprites(OLHO_FOFO, cores, (0.3, 0.42), (0.7, 0.42), brilho=[(1, 1)])

# Feroz (5x3): pálpebra diagonal caindo para o centro do rosto
OLHO_FEROZ = """
kk...
kkkkk
.ayPk
"""
par_de_sprites(OLHO_FEROZ, {"k": "#1C1418", "a": "#E0A030", "y": "#F7D560", "P": "#1C1418"},
               (0.3, 0.4), (0.7, 0.4))

# Densidade 1 (2x2): um texel escuro + um claro já basta
OLHO_PEQ = """
wk
"""
par_de_sprites(OLHO_PEQ, {"w": "#F4F4F0", "k": "#1C1418"}, (0.28, 0.45), (0.72, 0.45))
```
O sprite descreve o olho **esquerdo de quem olha** (direito da criatura); o outro sai espelhado.

## Boca e nariz

```python
SORRISO = """
k....k
.kkkk.
"""
sprite(SORRISO, {"k": "#2A1A1A"}, centro=(0.5, 0.78))
BOCA_ABERTA = """
kkkkkk
kwrrwk
.kkkk.
"""
sprite(BOCA_ABERTA, {"k": "#2A1414", "r": "#A8394A", "w": "#F4F0E6"}, centro=(0.5, 0.8))
retangulo(5, 2, 2, 1, "#1C1418")          # nariz 2x1
```

## Barriga/peito mais claro com borda de pelo

```python
onde(e_(faces("north", "down"), regiao(0.2, 0.25, 0.8, 1.0)), mat="barriga")
# borda em zigue-zague no topo da barriga, contínua nas laterais:
onde(e_(abaixo(10.5), listras(0, 1.0, 0.5, ondulacao=0.5, eixo_onda=0, freq_onda=1)), mat="barriga")
```

## Listras (tigre, zebra, Gabumon)

```python
# listras verticais pelo corpo, afinando de cima para baixo
onde(listras(2, 3.0, 1.0, afinar=(1, 14, 8)), mat="listra")
# anéis ao redor da cauda (eixo do comprimento = z)
onde(listras(2, 2.0, 0.5), mat="listra")
```

## Manchas (onça, vaca, musgo, ferrugem)

```python
onde(manchas(escala=2.5, limiar=0.3, semente=4), mat="mancha")
onde(e_(acima(12), manchas(1.5, 0.15, 9)), mat="musgo")      # musgo só no topo
```

## Escamas

```python
def escamas(mat_borda, periodo=2):
    def camada(ctx):
        u = (ctx.i % periodo == 0) | ((ctx.j % periodo == 0) & ((ctx.i // periodo + ctx.j // periodo) % 2 == 0))
        ctx.aplicar(u & ~ctx.fixo, mat=mat_borda)
    return camada
```

## Metal (armadura, robô)

```python
m.material("aco", rampa("#9AA4AE", n=7, base=4, contraste=1.4, desvio=0.5), ruido=0, pontilhado=0,
           aresta_clara=1.0, aresta_escura=0.8)
# faixa de reflexo: clara no terço de cima, escura logo abaixo
onde(local(1, 0.62, 0.75), somar_luz=1.5), onde(local(1, 0.5, 0.62), somar_luz=-1)
pixels([(1, 1), (6, 1)], ("aco", 2))       # rebites
```

## Pedra/golem

```python
m.material("pedra", rampa("#8E8C86", n=6, base=3), ruido=0.35, ruido_escala=2.5)
linha(2, 1, 5, 6, ("pedra", -2))           # rachadura
```

## Asa membranosa / barbatana (plano fino com transparência)

```python
asa = m.osso("wing_left", pivo=[3, 14, 0], pai="body", rotacao=[0, 0, -15])
ASA = """
mmmmmmmmmm
mmmmmmmm__
mmmmm_____
mm________
"""
asa.cubo([3, 10, 0], [10, 4, 0], [base("membrana")],
         faces={"north": [sprite(ASA, {"m": "membrana"})], "south": [sprite(ASA, {"m": "membrana"}, espelhar=True)]})
```
Espessura 0 em um eixo: só as duas faces grandes aparecem. Desenhe a silhueta com `_`.

## Chifre/garra com ponta clara

```python
chifre.cubo([-0.5, 20, -2], [1, 4, 1], [base("osso"), gradiente(1, 20, 24, -1.2, 1.5)],
            rotacao=[-20, 0, 0], pivo=[0, 20, -1.5])
```

## Roupa com costura

```python
m.material("tecido", rampa("#3E5BA8", n=5, base=3), ruido=0, volume=0.35)
onde(e_(entre(1, 9.0, 9.5), listras(0, 1.0, 0.5)), mat="tecido", somar_luz=-1)   # costura tracejada
```

## Parte que brilha (olhos de golem, runas)

```python
onde(regiao(0.4, 0.3, 0.6, 0.5), cor="#7CF5FF")     # cor fixa: não recebe sombra nem oclusão
```
Brilho no escuro de verdade precisa de uma camada emissiva no código do mod (GeckoLib:
`AutoGlowingGeoLayer` + textura `<nome>_glowmask.png` só com as partes que brilham).
