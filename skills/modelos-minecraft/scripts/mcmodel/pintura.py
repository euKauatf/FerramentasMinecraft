"""
Pintura pixel a pixel das faces.

Cada texel da textura sabe onde está no espaço 3D do modelo (ctx.p), em que face está, qual é a
sua normal e sua posição relativa dentro do cubo. As camadas de pintura são funções que recebem
esse contexto e marcam, texel a texel:

    ctx.mat  -> índice do material (cada material tem uma rampa de cores)
    ctx.luz  -> deslocamento de tom em "passos de rampa" (+1 = uma cor mais clara)
    ctx.cor / ctx.fixo -> cor exata, que ignora sombreamento (olhos, emblemas, contornos)

Depois das camadas vem o sombreamento automático do material (volume, oclusão nas junções,
arestas, granulado) e a quantização para a rampa, com pontilhado opcional. O resultado é pixel art
de paleta limitada, contínua entre faces vizinhas (padrões 3D não "quebram" nas quinas).
"""
import numpy as np

from .cores import rgba

BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0


# ================================================================== materiais

class Material:
    """
    rampa: lista de cores escura -> clara.  base: índice da cor "normal" da rampa.
    volume: degradê de luz dentro de cada cubo (topo claro, base escura). 0 desliga.
    oclusao: escurece junções e reentrâncias (pescoço, axilas, entre as pernas).
    aresta_clara / aresta_escura: realce de 1 texel nas bordas superiores / sombra nas inferiores.
    ruido: granulado em passos de rampa (0.3 sutil, 0.6 rústico). ruido_escala > 0 usa manchas
           3D suaves desse tamanho (em unidades do modelo) em vez de granulado por texel.
    pontilhado: 0..1, quanto as transições de tom usam padrão xadrez (Bayer) em vez de corte seco.
    """

    def __init__(self, nome, rampa, base=None, volume=0.45, oclusao=1.0, aresta_clara=0.6,
                 aresta_escura=0.45, ruido=0.1, ruido_escala=0.0, pontilhado=0.3, emissivo=False):
        self.nome = nome
        self.rampa = [rgba(c) for c in rampa]
        if base is None:
            base = getattr(rampa, "base", None)      # rampa() e rampa_manual() lembram a cor original
        self.base = len(self.rampa) // 2 if base is None else base
        self.volume = volume
        self.oclusao = oclusao
        self.aresta_clara = aresta_clara
        self.aresta_escura = aresta_escura
        self.ruido = ruido
        self.ruido_escala = ruido_escala
        self.pontilhado = pontilhado
        self.emissivo = emissivo


# ================================================================== contexto

class Contexto:
    """Tudo o que uma camada precisa saber sobre os texels de UMA face."""

    def __init__(self, modelo, cubo, face, w, h, p, n, l, oclusao, oculto):
        self.modelo = modelo
        self.cubo = cubo
        self.face = face
        self.w, self.h = w, h
        self.j, self.i = np.mgrid[0:h, 0:w]
        self.s = (self.i + 0.5) / w          # 0..1 da esquerda para a direita (como se vê a face)
        self.t = (self.j + 0.5) / h          # 0..1 de cima para baixo
        self.p = p                           # (h, w, 3) posição 3D (repouso) de cada texel
        self.n = n                           # normal da face (3,)
        self.l = l                           # (h, w, 3) posição relativa no cubo, 0..1 em x, y, z
        self.ao = oclusao                    # (h, w) 0..1
        self.oculto = oculto                 # (h, w) texel enterrado dentro de outro cubo
        self.mat = np.zeros((h, w), dtype=int)
        self.luz = np.zeros((h, w))
        self.cor = np.zeros((h, w, 4), dtype=np.uint8)
        self.fixo = np.zeros((h, w), dtype=bool)
        self.sem_sombra = np.zeros((h, w), dtype=bool)

    @property
    def x(self):
        return self.p[..., 0]

    @property
    def y(self):
        return self.p[..., 1]

    @property
    def z(self):
        return self.p[..., 2]

    def idx(self, material):
        return self.modelo.indice_material(material)

    def aplicar(self, mascara, mat=None, luz=None, somar_luz=None, cor=None, sem_sombra=False):
        """Aplica material/luz/cor onde a máscara for verdadeira."""
        m = np.broadcast_to(mascara, (self.h, self.w)).astype(bool)
        if mat is not None:
            self.mat[m] = self.idx(mat)
            self.fixo[m] = False
        if luz is not None:
            self.luz[m] = luz
        if somar_luz is not None:
            v = np.broadcast_to(somar_luz, (self.h, self.w))
            self.luz[m] += v[m]
        if cor is not None:
            c = rgba(cor)
            self.cor[m] = c
            self.fixo[m] = True
        if sem_sombra:
            self.sem_sombra[m] = True


# ===================================================================== ruído

def _hash(ix, iy, iz, semente):
    h = (ix.astype(np.int64) * 374761393 + iy.astype(np.int64) * 668265263
         + iz.astype(np.int64) * 2147483647 + semente * 1274126177) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((h ^ (h >> 16)) & 0xFFFF) / 65535.0 * 2 - 1


def ruido3(p, escala=1.0, semente=0):
    """Ruído de valor 3D suave em [-1, 1]. p: (..., 3)."""
    q = np.asarray(p, dtype=float) / escala
    b = np.floor(q)
    f = q - b
    f = f * f * (3 - 2 * f)
    bi = b.astype(np.int64)
    tot = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                v = _hash(bi[..., 0] + dx, bi[..., 1] + dy, bi[..., 2] + dz, semente)
                w = (f[..., 0] if dx else 1 - f[..., 0]) * (f[..., 1] if dy else 1 - f[..., 1]) * (f[..., 2] if dz else 1 - f[..., 2])
                tot = tot + v * w
    return tot


def fbm(p, escala=4.0, oitavas=3, semente=0):
    tot, amp, norm = 0, 1.0, 0
    for k in range(oitavas):
        tot = tot + ruido3(p, escala / (2 ** k), semente + k * 31) * amp
        norm += amp
        amp *= 0.5
    return tot / norm


def granulado(ctx, semente=0):
    """Ruído branco por texel, estável (mesma semente -> mesmo resultado)."""
    cid = ctx.modelo.id_cubo(ctx.cubo) * 7 + list(("north", "south", "east", "west", "up", "down")).index(ctx.face)
    return _hash(ctx.i, ctx.j, np.full_like(ctx.i, cid), semente)


# ======================================================= sombreamento final

def sombrear_e_quantizar(ctx):
    """Aplica o sombreamento automático dos materiais e converte para cores da rampa."""
    mats = ctx.modelo.lista_materiais
    out = ctx.cor.copy()
    lado = ctx.face in ("north", "south", "east", "west")
    for k, mat in enumerate(mats):
        m = (ctx.mat == k) & ~ctx.fixo
        if not m.any():
            continue
        luz = ctx.luz.copy()
        livre = ~ctx.sem_sombra
        if mat.volume:
            if lado:
                luz += np.where(livre, mat.volume * (ctx.l[..., 1] - 0.5) * 1.6, 0)
            elif ctx.face == "up":
                luz += np.where(livre, mat.volume * 0.8, 0)
            else:
                luz += np.where(livre, -mat.volume * 1.0, 0)
        if mat.oclusao:
            luz -= np.where(livre, mat.oclusao * ctx.ao * 2.6, 0)
        if (mat.aresta_clara or mat.aresta_escura) and ctx.w >= 3 and ctx.h >= 3:
            borda = np.zeros_like(luz)
            bi = getattr(ctx, "borda_interna", None)
            livre_b = {k: (~v).astype(float) for k, v in bi.items()} if bi else                 {"cima": 1.0, "baixo": 1.0, "esq": 1.0, "dir": 1.0}
            if lado:
                borda[0, :] += mat.aresta_clara * livre_b["cima"]
                borda[-1, :] -= mat.aresta_escura * livre_b["baixo"]
                if ctx.w >= 4:
                    borda[1:-1, 0] -= mat.aresta_escura * 0.4 * np.asarray(livre_b["esq"] * np.ones(ctx.h))[1:-1]
                    borda[1:-1, -1] -= mat.aresta_escura * 0.4 * np.asarray(livre_b["dir"] * np.ones(ctx.h))[1:-1]
            elif ctx.face == "up":
                # só a quina da frente (última linha) ganha brilho; moldura nas 4 bordas vira "almofada"
                borda[-1, :] += mat.aresta_clara * 0.5 * livre_b["baixo"]
            luz += np.where(livre, borda, 0)
        if mat.ruido:
            if mat.ruido_escala:
                luz += mat.ruido * fbm(ctx.p, mat.ruido_escala, 2, semente=k) * 1.6
            else:
                luz += mat.ruido * granulado(ctx, semente=k)
        limiar = 0.5 + mat.pontilhado * (BAYER4[ctx.j % 4, ctx.i % 4] - 0.5)
        idx = np.floor(mat.base + luz + limiar).astype(int)
        idx = np.clip(idx, 0, len(mat.rampa) - 1)
        rampa = np.array(mat.rampa, dtype=np.uint8)
        out[m] = rampa[idx[m]]
    return out


# ================================================================= camadas
# Uma camada é qualquer função f(ctx). As fábricas abaixo cobrem quase tudo; para algo
# específico, escreva uma função e use ctx.aplicar(mascara, ...).

def base(material, luz=0.0):
    """Preenche a face inteira com um material."""
    def camada(ctx):
        ctx.mat[:] = ctx.idx(material)
        ctx.fixo[:] = False
        ctx.luz[:] = luz
    return camada


def onde(condicao, mat=None, luz=None, somar_luz=None, cor=None, sem_sombra=False):
    """Aplica material/luz/cor onde a condição (função ctx -> máscara) for verdadeira."""
    def camada(ctx):
        ctx.aplicar(condicao(ctx), mat=mat, luz=luz,
                    somar_luz=somar_luz(ctx) if callable(somar_luz) else somar_luz,
                    cor=cor, sem_sombra=sem_sombra)
    return camada


def gradiente(eixo, a, b, de, ate, condicao=None):
    """Soma luz variando linearmente ao longo de um eixo do mundo (0=x,1=y,2=z) de a até b."""
    def camada(ctx):
        t = np.clip((ctx.p[..., eixo] - a) / (b - a), 0, 1)
        v = de + (ate - de) * t
        m = condicao(ctx) if condicao else True
        ctx.aplicar(m, somar_luz=v)
    return camada


def so_faces(nomes, *camadas):
    """Aplica as camadas só nas faces citadas (ex.: so_faces('north', sprite(...)))."""
    if isinstance(nomes, str):
        nomes = (nomes,)

    def camada(ctx):
        if ctx.face in nomes:
            for c in camadas:
                c(ctx)
    return camada


def sprite(arte, cores, pos=None, centro=None, espelhar=False, ancora="topo_esq"):
    """
    Carimba pixel art escrita como texto. Cada caractere vira um texel:
      '.' ou ' ' -> não mexe      '_' -> transparente
      outro -> procurado em `cores`: uma cor ('#RRGGBB') = cor exata, sem sombra;
               um nome de material = muda o material (recebe sombreamento);
               (material, luz) = material com deslocamento de tom.
    pos=(i, j): canto superior esquerdo em texels da face. centro=(s, t): centro em frações da face.
    """
    linhas = [ln for ln in arte.strip("\n").split("\n")]
    larg = max(len(ln) for ln in linhas)
    linhas = [ln.ljust(larg, ".") for ln in linhas]
    if espelhar:
        linhas = [ln[::-1] for ln in linhas]
    alt = len(linhas)

    def camada(ctx):
        if centro is not None:
            i0 = int(round(centro[0] * ctx.w - larg / 2))
            j0 = int(round(centro[1] * ctx.h - alt / 2))
        else:
            i0, j0 = pos or (0, 0)
        for dj, ln in enumerate(linhas):
            for di, ch in enumerate(ln):
                if ch in ". ":
                    continue
                i, j = i0 + di, j0 + dj
                if not (0 <= i < ctx.w and 0 <= j < ctx.h):
                    continue
                if ch == "_":
                    ctx.cor[j, i] = (0, 0, 0, 0)
                    ctx.fixo[j, i] = True
                    continue
                v = cores[ch]
                if isinstance(v, tuple) and len(v) == 2 and isinstance(v[0], str) and not v[0].startswith("#"):
                    ctx.mat[j, i] = ctx.idx(v[0])
                    ctx.luz[j, i] = v[1]
                    ctx.fixo[j, i] = False
                elif isinstance(v, str) and not v.startswith("#"):
                    ctx.mat[j, i] = ctx.idx(v)
                    ctx.fixo[j, i] = False
                else:
                    ctx.cor[j, i] = rgba(v)
                    ctx.fixo[j, i] = True
    return camada


def par_de_sprites(arte, cores, centro_esq, centro_dir, brilho=None, cor_brilho="#FFFFFF"):
    """
    Dois sprites espelhados (olhos, bochechas): a arte é o do lado esquerdo de quem olha.
    brilho=[(i, j), ...]: texels de brilho relativos ao canto do sprite, aplicados SEM espelhar nos
    dois (a luz vem do mesmo lado para os dois olhos).
    """
    linhas = arte.strip("\n").split("\n")
    larg, alt = max(len(ln) for ln in linhas), len(linhas)
    a = sprite(arte, cores, centro=centro_esq)
    b = sprite(arte, cores, centro=centro_dir, espelhar=True)

    def camada(ctx):
        a(ctx)
        b(ctx)
        for c in (centro_esq, centro_dir):
            i0 = int(round(c[0] * ctx.w - larg / 2))
            j0 = int(round(c[1] * ctx.h - alt / 2))
            for di, dj in brilho or ():
                if 0 <= i0 + di < ctx.w and 0 <= j0 + dj < ctx.h:
                    _por(ctx, j0 + dj, i0 + di, cor_brilho)
    return camada


def pixels(lista, valor):
    """Pinta texels específicos [(i, j), ...] com uma cor exata ou um material."""
    def camada(ctx):
        for i, j in lista:
            if 0 <= i < ctx.w and 0 <= j < ctx.h:
                _por(ctx, j, i, valor)
    return camada


def retangulo(i, j, w, h, valor):
    def camada(ctx):
        for jj in range(max(0, j), min(ctx.h, j + h)):
            for ii in range(max(0, i), min(ctx.w, i + w)):
                _por(ctx, jj, ii, valor)
    return camada


def linha(i0, j0, i1, j1, valor):
    """Linha pixel-perfect (Bresenham), sem degraus duplos."""
    def camada(ctx):
        di, dj = abs(i1 - i0), -abs(j1 - j0)
        si, sj = (1 if i0 < i1 else -1), (1 if j0 < j1 else -1)
        err, i, j = di + dj, i0, j0
        while True:
            if 0 <= i < ctx.w and 0 <= j < ctx.h:
                _por(ctx, j, i, valor)
            if i == i1 and j == j1:
                break
            e2 = 2 * err
            if e2 >= dj:
                err += dj
                i += si
            if e2 <= di:
                err += di
                j += sj
    return camada


def elipse(ci, cj, ri, rj, valor, contorno=None):
    """Elipse cheia em coordenadas de texel (centro pode ser fracionário: 3.5 = entre dois texels)."""
    def camada(ctx):
        d = ((ctx.i + 0.5 - ci) / ri) ** 2 + ((ctx.j + 0.5 - cj) / rj) ** 2
        dentro = d <= 1.0
        for jj, ii in zip(*np.nonzero(dentro)):
            _por(ctx, jj, ii, valor)
        if contorno is not None:
            borda = dentro & ~(np.roll(dentro, 1, 0) & np.roll(dentro, -1, 0) & np.roll(dentro, 1, 1) & np.roll(dentro, -1, 1))
            for jj, ii in zip(*np.nonzero(borda)):
                _por(ctx, jj, ii, contorno)
    return camada


def _por(ctx, j, i, valor):
    if isinstance(valor, tuple) and len(valor) == 2 and isinstance(valor[0], str) and not valor[0].startswith("#"):
        ctx.mat[j, i] = ctx.idx(valor[0])
        ctx.luz[j, i] = valor[1]
        ctx.fixo[j, i] = False
    elif isinstance(valor, str) and not valor.startswith("#"):
        ctx.mat[j, i] = ctx.idx(valor)
        ctx.fixo[j, i] = False
    else:
        ctx.cor[j, i] = rgba(valor)
        ctx.fixo[j, i] = True


# ======================================================= condições (máscaras)
# Funções ctx -> máscara booleana. Combine com e_(), ou_(), nao().

def acima(y):
    return lambda ctx: ctx.y >= y


def abaixo(y):
    return lambda ctx: ctx.y < y


def entre(eixo, a, b):
    return lambda ctx: (ctx.p[..., eixo] >= a) & (ctx.p[..., eixo] < b)


def caixa(minimo, maximo):
    mn, mx = np.array(minimo, float), np.array(maximo, float)
    return lambda ctx: np.all((ctx.p >= mn) & (ctx.p < mx), axis=-1)


def esfera(centro, raio, achatar=(1, 1, 1)):
    c, a = np.array(centro, float), np.array(achatar, float)
    return lambda ctx: np.sum(((ctx.p - c) / a) ** 2, axis=-1) <= raio ** 2


def faces(*nomes):
    return lambda ctx: np.full((ctx.h, ctx.w), ctx.face in nomes)


def local(eixo, a, b):
    """Faixa em coordenadas relativas do cubo (0..1), ex.: local(1, 0, 0.3) = terço de baixo."""
    return lambda ctx: (ctx.l[..., eixo] >= a) & (ctx.l[..., eixo] < b)


def regiao(s0, t0, s1, t1):
    """Retângulo em frações da face (s da esquerda p/ direita, t de cima p/ baixo)."""
    return lambda ctx: (ctx.s >= s0) & (ctx.s < s1) & (ctx.t >= t0) & (ctx.t < t1)


def borda_da_face(largura=1):
    return lambda ctx: ((ctx.i < largura) | (ctx.j < largura) | (ctx.i >= ctx.w - largura) | (ctx.j >= ctx.h - largura))


def listras(eixo, periodo, largura, fase=0.0, ondulacao=0.0, eixo_onda=None, freq_onda=0.5, afinar=None):
    """
    Listras 3D ao longo de um eixo do mundo. Continuam certinhas de uma face para a outra.
    ondulacao: amplitude (unidades) da curva da listra; eixo_onda: eixo que faz a listra ondular.
    afinar=(eixo, inicio, fim): a listra vai afinando até sumir ao longo de outro eixo (listras de tigre).
    """
    def cond(ctx):
        v = ctx.p[..., eixo] + fase
        if ondulacao and eixo_onda is not None:
            v = v + ondulacao * np.sin(ctx.p[..., eixo_onda] * freq_onda * np.pi)
        larg = np.full(v.shape, float(largura))
        if afinar is not None:
            e, ini, fim = afinar
            larg = larg * np.clip(1 - (ctx.p[..., e] - ini) / (fim - ini), 0, 1)
        return (v % periodo) < larg
    return cond


def manchas(escala=3.0, limiar=0.35, semente=1):
    """Manchas orgânicas 3D (pelagem de onça, musgo, sujeira). Maior limiar = menos manchas."""
    return lambda ctx: fbm(ctx.p, escala, 2, semente) > limiar


def _mascara(ctx, c):
    return np.broadcast_to(np.asarray(c(ctx), dtype=bool), (ctx.h, ctx.w))


def e_(*conds):
    return lambda ctx: np.logical_and.reduce([_mascara(ctx, c) for c in conds])


def ou_(*conds):
    return lambda ctx: np.logical_or.reduce([_mascara(ctx, c) for c in conds])


def nao(cond):
    return lambda ctx: ~cond(ctx)


def sempre(ctx):
    return np.ones((ctx.h, ctx.w), dtype=bool)


# ============================================================ formas por recorte
_EIXOS = {"x": 0, "y": 1, "z": 2}
_NORMAL_EIXO = {"east": 0, "west": 0, "up": 1, "down": 1, "north": 2, "south": 2}


def afinar(ponta="-y", largura_ponta=0.0, curva=1.0, apoio=None):
    """
    Recorta (texels transparentes) o cubo inteiro numa forma de cone/cunha: garras, dentes, chifres,
    espinhos, unhas, pontas de orelha. Use num cubo pequeno, em TODAS as faces (vai em `pintura`).
        ponta: para onde aponta a ponta: "-y" (para baixo), "+y", "-z" (para a frente), "+z", "-x", "+x"
        largura_ponta: 0 = ponta fina; 0.4 = ponta rombuda
        curva: 1 = cone reto; > 1 = fica larga e afina só perto da ponta (lâmina, garra grande);
               < 1 = afina logo no começo (agulha, espinho fino)
        apoio: "y" mantém o lado de baixo reto (garras do pé apoiadas no chão), "-y" o de cima, etc.
    O jogo precisa de render type com recorte (o GeoEntityRenderer padrão usa entityCutoutNoCull).
    """
    sinal = -1 if ponta.startswith("-") else 1
    a = _EIXOS[ponta[-1]]
    ap_eixo = _EIXOS[apoio[-1]] if apoio else None
    ap_baixo = not (apoio or "").startswith("-")

    def camada(ctx):
        l = ctx.l
        t = l[..., a] if sinal > 0 else 1 - l[..., a]
        t = np.clip(t, 0, 1)
        w = 1 - (1 - largura_ponta) * np.power(t, curva)
        manter = np.ones((ctx.h, ctx.w), dtype=bool)
        k = _NORMAL_EIXO[ctx.face]
        for m in range(3):
            if m == a or m == k:
                continue
            tol_px = 1.0 / max(ctx.w, ctx.h)
            if ap_eixo == m:
                d = l[..., m] if ap_baixo else 1 - l[..., m]
            else:
                d = np.abs(l[..., m] - 0.5) * 2
            manter &= d <= w + tol_px
        if k == a and t.mean() > 0.5 and largura_ponta < 0.35:
            manter[:] = False      # a tampa da ponta some quando a ponta é fina
        ctx.cor[~manter] = (0, 0, 0, 0)
        ctx.fixo[~manter] = True
    return camada


def decalque(arte, cores, centro, direcao=(0, 0, -1), px=None, cima=(0, 1, 0), profundidade=1.5,
             so_frente=0.15):
    """
    Projeta pixel art no modelo como um "adesivo" 3D, vindo da `direcao` para onde ele olha.
    Diferente de `sprite` (que vive numa face só), o decalque atravessa quinas e cubos vizinhos:
    olhos que dobram a lateral da cabeça, marcas no peito sobre cubos arredondados, emblemas.
        arte/cores: iguais às de `sprite` ('.' não mexe, '_' transparente)
        centro: ponto 3D (repouso) onde fica o centro da arte
        direcao: para onde o adesivo "olha" (ex.: olho esquerdo virado para a frente e para fora:
                 (0.5, 0, -1)). Vista de quem olha nessa direção para o modelo, a arte aparece
                 exatamente como desenhada.
        px: tamanho de um caractere em unidades (padrão: 1/densidade)
        profundidade: até que distância (ao longo da direção) do centro a arte é aplicada
        so_frente: só pinta faces cuja normal concorda com a direção (n·d > so_frente)
    Use em `pintura` de todos os cubos que o adesivo pode tocar (ex.: os 3 de um cubo_arredondado).
    """
    linhas = [ln for ln in arte.strip("\n").split("\n")]
    larg = max(len(ln) for ln in linhas)
    linhas = [ln.ljust(larg, ".") for ln in linhas]
    alt = len(linhas)
    d = np.array(direcao, float)
    d /= np.linalg.norm(d)
    up = np.array(cima, float)
    up = up - d * (up @ d)
    up /= np.linalg.norm(up)
    direita = np.cross(d, up)          # direita de quem olha o adesivo de frente
    c = np.array(centro, float)

    def camada(ctx):
        if ctx.n @ d <= so_frente:
            return
        tam = px or 1.0 / ctx.modelo.densidade
        rel = ctx.p - c
        prof = rel @ d
        u = rel @ direita / tam + larg / 2
        v = -(rel @ up) / tam + alt / 2
        ii = np.floor(u + 1e-6).astype(int)
        jj = np.floor(v + 1e-6).astype(int)
        ok = (ii >= 0) & (ii < larg) & (jj >= 0) & (jj < alt) & (np.abs(prof) <= profundidade)
        for j, i in zip(*np.nonzero(ok)):
            ch = linhas[jj[j, i]][ii[j, i]]
            if ch in ". ":
                continue
            if ch == "_":
                ctx.cor[j, i] = (0, 0, 0, 0)
                ctx.fixo[j, i] = True
                continue
            _por(ctx, j, i, cores[ch])
    return camada
