"""
Texturas 2D (itens, blocos, ícones, partículas) com as mesmas ferramentas de pintura dos modelos.

    t = Textura2D("rubi", 16, 16)
    t.material("gema", rampa("#D0213A", n=6, base=3), pontilhado=0)
    img = t.pintar(sprite(ARTE, CORES), contorno="#3A0A14", luz_de_cima=True)
    img.save("rubi.png")

Coordenadas: ctx.i / ctx.j em pixels (j cresce para baixo); ctx.p = (i, altura-1-j, 0), então
condições 3D como acima(y) funcionam com y para cima, em pixels.
Pixels não pintados ficam transparentes (itens). Para blocos, comece com base("material").
"""
import numpy as np
from PIL import Image

from .cores import rgba
from .pintura import Contexto, Material, sombrear_e_quantizar


class Textura2D:
    def __init__(self, nome, largura=16, altura=16):
        self.nome = nome
        self.largura, self.altura = largura, altura
        self.materiais = {}
        self.lista_materiais = []

    def material(self, nome, rampa, **kw):
        kw.setdefault("volume", 0.0)
        kw.setdefault("oclusao", 0.0)
        kw.setdefault("aresta_clara", 0.0)
        kw.setdefault("aresta_escura", 0.0)
        mat = Material(nome, rampa, **kw)
        self.lista_materiais.append(mat)
        self.materiais[nome] = mat
        return mat

    def indice_material(self, nome):
        if isinstance(nome, int):
            return nome
        return self.lista_materiais.index(self.materiais[nome])

    def id_cubo(self, _):
        return 0

    def pintar(self, *camadas, contorno=None, luz_de_cima=False, forca_luz=1.0):
        """
        contorno: cor (ex. '#2A1A10') para a linha de 1 pixel em volta da silhueta, ou
                  um número negativo (ex. -2) para escurecer a borda dentro da própria rampa.
        luz_de_cima: realça bordas viradas para cima/esquerda e escurece as de baixo/direita
                     (o jeito clássico de dar volume a itens do Minecraft).
        """
        w, h = self.largura, self.altura
        jj, ii = np.mgrid[0:h, 0:w]
        p = np.stack([ii.astype(float), (h - 1 - jj).astype(float), np.zeros((h, w))], axis=-1)
        l = np.stack([(ii + 0.5) / w, 1 - (jj + 0.5) / h, np.full((h, w), 0.5)], axis=-1)
        ctx = Contexto(self, None, "north", w, h, p, np.array([0, 0, -1.0]), l,
                       np.zeros((h, w)), np.zeros((h, w), dtype=bool))
        ctx.fixo[:] = True                       # começa transparente
        for c in camadas:
            c(ctx)
        cheio = ~(ctx.fixo & (ctx.cor[..., 3] == 0))
        vazio = ~cheio

        def vizinho_vazio(dj, di):
            v = np.ones((h, w), dtype=bool)
            src = vazio
            ys, xs = slice(max(0, dj), h + min(0, dj)), slice(max(0, di), w + min(0, di))
            yd, xd = slice(max(0, -dj), h + min(0, -dj)), slice(max(0, -di), w + min(0, -di))
            v[yd, xd] = src[ys, xs]
            return v

        cima, baixo = vizinho_vazio(-1, 0), vizinho_vazio(1, 0)
        esq, dir_ = vizinho_vazio(0, -1), vizinho_vazio(0, 1)
        borda = cheio & (cima | baixo | esq | dir_)
        livre = cheio & ~ctx.fixo
        if luz_de_cima:
            ctx.luz[livre & (cima | esq)] += 1.0 * forca_luz
            ctx.luz[livre & (baixo | dir_)] -= 1.0 * forca_luz
        if isinstance(contorno, (int, float)):
            ctx.luz[livre & borda] += contorno
        img = sombrear_e_quantizar(ctx)
        img[vazio] = (0, 0, 0, 0)
        if contorno is not None and not isinstance(contorno, (int, float)):
            img[borda] = rgba(contorno)
        return Image.fromarray(img, "RGBA")
