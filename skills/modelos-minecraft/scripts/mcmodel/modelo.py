"""
Descrição de modelos em código e exportação para GeckoLib / Bedrock (.geo.json, .animation.json, .png).

    m = Modelo("raposa", densidade=2)
    m.material("pelo", rampa("#D9822B", n=6))
    corpo = m.osso("body", pivo=[0, 10, 0])
    corpo.cubo([-3, 7, -5], [6, 6, 10], [base("pelo")])
    m.salvar(r"D:\\saida")

densidade = texels por unidade do modelo. 1 = padrão do Minecraft (16 px por bloco),
2 = "HD" (o dobro de detalhe; ainda combina com o jogo), 4 = só para peças pequenas e especiais.
"""
import json
import math
import os

import numpy as np
from PIL import Image

from . import geometria as geo
from .pintura import Contexto, Material, sombrear_e_quantizar


def _rotacao_para(u):
    """Ângulos Bedrock [rx, 0, rz] que levam o eixo +Y do cubo até a direção u."""
    dx, dy, dz = (float(v) for v in u)
    teta = math.degrees(math.asin(max(-1.0, min(1.0, dz))))
    c = math.cos(math.radians(teta))
    fi = math.degrees(math.atan2(-dx, dy)) if c > 1e-9 else 0.0
    melhor = None
    for sx in (1, -1):
        for sz in (1, -1):
            rot = [sx * teta, 0.0, sz * fi]
            v = geo.matriz_rotacao(rot) @ np.array([0.0, 1.0, 0.0])
            erro = float(np.linalg.norm(v - np.array(u)))
            if melhor is None or erro < melhor[0]:
                melhor = (erro, rot)
    if melhor[0] > 1e-4:
        raise RuntimeError(f"não consegui alinhar o segmento (erro {melhor[0]:.3f})")
    return [round(v, 3) for v in melhor[1]]


class Cubo:
    def __init__(self, osso, origem, tamanho, pintura=None, faces=None, rotacao=None, pivo=None,
                 inflar=0.0, ocultar=(), nome=None, grupo=None):
        self.osso = osso
        self.grupo = grupo            # cubos do mesmo grupo (ex.: um cubo arredondado) não se sombreiam
        self.origem = [float(v) for v in origem]
        self.tamanho = [float(v) for v in tamanho]
        self.pintura = list(pintura or [])
        self.faces = {k: (v if isinstance(v, (list, tuple)) else [v]) for k, v in (faces or {}).items()}
        self.rotacao = rotacao
        self.pivo = pivo
        self.inflar = inflar
        self.ocultar = set(ocultar)   # faces que não existem (ex.: a de baixo de um chapéu colado)
        self.nome = nome

    def como_json(self):
        c = {"origin": self.origem, "size": self.tamanho}
        if self.rotacao and any(self.rotacao):
            c["rotation"] = list(self.rotacao)
            c["pivot"] = list(self.pivo) if self.pivo else [self.origem[k] + self.tamanho[k] / 2 for k in range(3)]
        if self.inflar:
            c["inflate"] = self.inflar
        return c


class Osso:
    def __init__(self, modelo, nome, pivo, pai=None, rotacao=None):
        self.modelo = modelo
        self.nome = nome
        self.pivo = [float(v) for v in pivo]
        self.pai = pai
        self.rotacao = rotacao
        self.cubos = []

    def cubo(self, origem, tamanho, pintura=None, **kw):
        c = Cubo(self, origem, tamanho, pintura, **kw)
        self.cubos.append(c)
        return c

    def cubo_centrado(self, centro, tamanho, pintura=None, **kw):
        """Cubo dado pelo centro em vez do canto."""
        origem = [centro[k] - tamanho[k] / 2 for k in range(3)]
        return self.cubo(origem, tamanho, pintura, **kw)

    def cubo_arredondado(self, origem, tamanho, pintura=None, raio=1, arestas="todas", **kw):
        """
        "Cubo de quinas chanfradas" feito de 3 a 5 peças que se encaixam sem se sobrepor (técnica do Cobblemon para
        cabeças, barrigas, focinhos e coxas que não podem parecer caixas).
            arestas="todas"      3 cubos: chanfra as 12 quinas (cabeça, barriga)
            arestas="verticais"  2 cubos: chanfra só as quinas em pé (vistas de cima ficam octogonais)
            arestas="frente"     2 cubos: chanfra as quinas paralelas ao eixo X (perfil de lado oitavado)
            arestas="x"/"y"/"z"  2 cubos: chanfra as quinas paralelas a esse eixo ("y" = "verticais",
                                 "x" = "frente", "z" = caudas e pescoços que vão para trás)
        raio em unidades do modelo (use múltiplos de 1/densidade). Mesma pintura em todos os cubos;
        como a pintura usa posição 3D, padrões continuam certinhos de um cubo para o outro.
        Devolve a lista de cubos.
        """
        x0, y0, z0 = origem
        W, H, D = tamanho
        r = raio
        arestas = {"y": "verticais", "x": "frente"}.get(arestas, arestas)
        # raio grande demais para o tamanho vira uma "cruz" de placas finas (só avisa; não muda o modelo)
        lados = {"todas": (W, H, D), "verticais": (W, D), "frente": (H, D), "z": (W, H)}.get(arestas, (W, H, D))
        if r > min(lados) / 3 + 1e-6:
            print(f"  aviso: cubo_arredondado em '{self.nome}' {list(tamanho)}: raio {raio} passa de 1/3 do menor "
                  f"lado ({min(lados)}); se aparecer uma 'cruz' de placas, diminua o raio")
        # Partes SEM sobreposição (cada pedaço ocupa uma região só). A versão antiga usava 2-3 cubos
        # que se sobrepunham e tinham faces no MESMO plano: no jogo isso "pisca" (z-fighting).
        # Cada parte leva as faces internas (encostadas no miolo) em `ocultar`.
        if arestas == "todas":
            partes = [((x0, y0 + r, z0 + r), (W, H - 2 * r, D - 2 * r), ()),                       # miolo
                      ((x0 + r, y0 + H - r, z0 + r), (W - 2 * r, r, D - 2 * r), ("down",)),       # tampa
                      ((x0 + r, y0, z0 + r), (W - 2 * r, r, D - 2 * r), ("up",)),                 # fundo
                      ((x0 + r, y0 + r, z0), (W - 2 * r, H - 2 * r, r), ("south",)),              # frente
                      ((x0 + r, y0 + r, z0 + D - r), (W - 2 * r, H - 2 * r, r), ("north",))]      # trás
        elif arestas == "verticais":
            partes = [((x0, y0, z0 + r), (W, H, D - 2 * r), ()),
                      ((x0 + r, y0, z0), (W - 2 * r, H, r), ("south",)),
                      ((x0 + r, y0, z0 + D - r), (W - 2 * r, H, r), ("north",))]
        elif arestas == "frente":
            partes = [((x0, y0 + r, z0), (W, H - 2 * r, D), ()),
                      ((x0, y0, z0 + r), (W, r, D - 2 * r), ("up",)),
                      ((x0, y0 + H - r, z0 + r), (W, r, D - 2 * r), ("down",))]
        elif arestas == "z":
            partes = [((x0, y0 + r, z0), (W, H - 2 * r, D), ()),
                      ((x0 + r, y0, z0), (W - 2 * r, r, D), ("up",)),
                      ((x0 + r, y0 + H - r, z0), (W - 2 * r, r, D), ("down",))]
        else:
            raise ValueError("arestas deve ser 'todas', 'verticais'/'y', 'frente'/'x' ou 'z'")
        grupo = kw.pop("grupo", None) or f"arred{len(self.modelo.todos_cubos())}_{self.nome}"
        ocultar_extra = tuple(kw.pop("ocultar", ()))
        cubos = []
        for o, t, internas in partes:
            if min(t) <= 0:
                continue
            cubos.append(self.cubo(list(o), list(t), list(pintura or []), grupo=grupo,
                                   ocultar=tuple(internas) + ocultar_extra, **kw))
        return cubos

    def segmento(self, de, ate, largura, profundidade=None, pintura=None, raio=0, arestas="y",
                 sobra=0.0, **kw):
        """
        Peça de membro que vai de uma articulação `de` até a próxima `ate` (pontos 3D): coxa, canela,
        braço, antebraço, dedo, pescoço, gomo de cauda. O cubo é girado para alinhar com a linha entre
        os pontos, com pivô em `de` (a articulação). É assim que se faz perna dobrada de dinossauro,
        cotovelo, pescoço em "S" e cauda curva sem calcular ângulo na mão.
            largura (x) e profundidade (z) da seção; raio > 0 usa cubo_arredondado (arestas="y" =
            quinas ao longo do membro arredondadas).
            sobra: estica o segmento nas duas pontas (unidades) para cobrir a junta com o vizinho.
        O comprimento é arredondado para múltiplos de 1/densidade (pixel inteiro).
        Devolve a lista de cubos.
        """
        a = np.array(de, float)
        b = np.array(ate, float)
        d = b - a
        L = float(np.linalg.norm(d))
        if L < 1e-6:
            raise ValueError("segmento com comprimento zero")
        u = d / L
        passo = 1.0 / self.modelo.densidade
        comp = max(passo, round((L + 2 * sobra) / passo) * passo)
        prof = largura if profundidade is None else profundidade
        rot = _rotacao_para(u)
        origem = [a[0] - largura / 2, a[1] - sobra, a[2] - prof / 2]
        tam = [largura, comp, prof]
        kw = dict(kw, rotacao=rot, pivo=[float(a[0]), float(a[1]), float(a[2])])
        if raio:
            return self.cubo_arredondado(origem, tam, pintura, raio=raio, arestas=arestas, **kw)
        return [self.cubo(origem, tam, pintura, **kw)]

    def cadeia(self, pontos, secoes, pintura=None, raio=0, arestas="y", sobra=0.5, **kw):
        """
        Vários segmentos encadeados (cauda, pescoço, tentáculo, dedo comprido): pontos = articulações
        [p0, p1, ...]; secoes = [(largura, profundidade), ...] uma por segmento (afinando = cauda).
        """
        cubos = []
        for k in range(len(pontos) - 1):
            w, d = secoes[min(k, len(secoes) - 1)]
            r = raio if min(w, d) > 2 * raio + 0.5 else 0
            cubos += self.segmento(pontos[k], pontos[k + 1], w, d, pintura, raio=r, arestas=arestas,
                                   sobra=sobra, **kw)
        return cubos

    def plano(self, origem, tamanho, pintura=None, **kw):
        """
        Peça de espessura zero (um dos lados do tamanho = 0): garras, dentes, unhas, orelhas finas,
        chamas, cílios, franjas. Só as 2 faces grandes vão para a textura; o jogo desenha as duas.
        """
        if sum(1 for v in tamanho if v == 0) != 1:
            raise ValueError("plano precisa de exatamente um lado igual a 0")
        return self.cubo(origem, tamanho, pintura, **kw)


class Modelo:
    def __init__(self, nome, densidade=1, largura_textura=None, escala=1.0):
        """
        escala: aumenta/diminui o modelo PRONTO por inteiro (geometria, pivôs e posições das animações),
        mantendo a textura: os texels ficam maiores/menores por igual. Use para "deixe ele maior" sem
        refazer as medidas (1.3 = 30% maior). Escreva o modelo sempre no tamanho base.
        """
        self.escala = float(escala)
        self.nome = nome
        self.densidade = densidade
        self.largura_textura = largura_textura
        self.ossos = {}
        self.materiais = {}
        self.lista_materiais = []
        self.animacoes = {}
        self._ids = {}
        self.deslocamentos = {}

    def deslocar(self, nome_osso, delta):
        """Move o osso e todos os filhos dele no arquivo final, sem mudar a pintura (as condições de
        pintura continuam nas coordenadas escritas no script). Use para alongar pernas: escreva o tronco
        como estava e desloque "body" para cima."""
        self.deslocamentos[nome_osso] = [float(v) for v in delta]

    # ----------------------------------------------------------- descrição
    ESTILOS = {
        # Cobblemon / mobs oficiais: cor chapada em manchas grandes de 2-3 tons, sem chuvisco,
        # pouco degradê (a luz do jogo já sombreia as faces), quinas discretas.
        "limpo": dict(volume=0.3, aresta_clara=0.35, aresta_escura=0.3, ruido=0.4, ruido_escala=2.5,
                      pontilhado=0.0, oclusao=0.8),
        # superfície lisa sem manchas (olhos, garras, dentes, plástico, metal polido)
        "liso": dict(volume=0.35, aresta_clara=0.6, aresta_escura=0.3, ruido=0.0, pontilhado=0.0, oclusao=0.5),
        # Minecraft de verdade (mobs vanilla): granulado de 2-3 tons próximos em toda a superfície
        # (40-60% dos pixels diferem do vizinho), degradê suave escurecendo embaixo, quase sem
        # borda clara desenhada. Use com rampa_vanilla() (cores menos saturadas, tiradas do jogo).
        "vanilla": dict(volume=0.45, aresta_clara=0.15, aresta_escura=0.3, ruido=0.7, ruido_escala=0.0,
                        pontilhado=0.0, oclusao=0.9),
        # pelagem / pedra / casca: mais textura, granulado fino
        "rustico": dict(volume=0.4, aresta_clara=0.5, aresta_escura=0.45, ruido=0.3, ruido_escala=0.0,
                        pontilhado=0.25, oclusao=1.0),
    }

    def material(self, nome, rampa, estilo=None, **kw):
        """estilo: "limpo" (padrão: cor viva e lisa), "liso", "rustico" ou "vanilla"; kw sobrescreve."""
        if estilo:
            kw = {**self.ESTILOS[estilo], **kw}
        mat = Material(nome, rampa, **kw)
        if nome in self.materiais:
            self.lista_materiais[self.lista_materiais.index(self.materiais[nome])] = mat
        else:
            self.lista_materiais.append(mat)
        self.materiais[nome] = mat
        return mat

    def indice_material(self, nome):
        if isinstance(nome, int):
            return nome
        if nome not in self.materiais:
            raise KeyError(f"material '{nome}' não foi definido com m.material(...)")
        return self.lista_materiais.index(self.materiais[nome])

    def osso(self, nome, pivo=(0, 0, 0), pai=None, rotacao=None):
        if nome in self.ossos:
            raise ValueError(f"osso '{nome}' repetido")
        if pai is not None and pai not in self.ossos:
            raise ValueError(f"osso pai '{pai}' não existe (crie os pais antes dos filhos)")
        o = Osso(self, nome, pivo, pai, rotacao)
        self.ossos[nome] = o
        return o

    def animacao(self, nome, duracao, ossos, loop=True):
        """ossos: {nome_osso: {"rotation": ..., "position": ..., "scale": ...}} (ver animacao.py)."""
        self.animacoes[nome] = {"loop": loop, "animation_length": duracao, "bones": ossos}

    def id_cubo(self, cubo):
        return self._ids.setdefault(id(cubo), len(self._ids))

    def todos_cubos(self):
        return [c for o in self.ossos.values() for c in o.cubos]

    # ------------------------------------------------------------ geometria
    def _ossos_json(self):
        saida = []
        for o in self.ossos.values():
            j = {"name": o.nome, "pivot": o.pivo}
            if o.pai:
                j["parent"] = o.pai
            if o.rotacao and any(o.rotacao):
                j["rotation"] = list(o.rotacao)
            saida.append(j)
        return saida

    def _caixas_mundo(self, pose):
        """AABB (no repouso) de cada cubo, usada na oclusão."""
        caixas = []
        for c in self.todos_cubos():
            x0, y0, z0 = c.origem
            W, H, D = c.tamanho
            cantos = np.array([[x, y, z] for x in (x0, x0 + W) for y in (y0, y0 + H) for z in (z0, z0 + D)])
            pts = pose.transformar(c.osso.nome, geo.girar_no_cubo(c.como_json(), cantos))
            caixas.append((pts.min(0), pts.max(0)))
        return caixas

    def _oclusao(self, cubo_id, pts, normal, caixas, raio=2.2, grupos=None):
        """Oclusão aproximada: quão perto (e na frente da face) estão os outros cubos."""
        q = pts + normal * 0.15
        livre = np.ones(pts.shape[:-1])
        oculto = np.zeros(pts.shape[:-1], dtype=bool)
        for k, (mn, mx) in enumerate(caixas):
            if k == cubo_id:
                continue
            if mx[0] - mn[0] < 1e-6 or mx[1] - mn[1] < 1e-6 or mx[2] - mn[2] < 1e-6:
                continue     # planos não fazem sombra nem escondem nada
            mesmo = grupos is not None and grupos[k] is not None and grupos[k] == grupos[cubo_id]
            if mesmo:
                oculto |= np.all((q > mn + 1e-4) & (q < mx - 1e-4), axis=-1)
                continue
            perto = np.clip(q, mn, mx)
            dv = perto - q
            d = np.linalg.norm(dv, axis=-1)
            dentro = d < 1e-6
            oculto |= dentro & np.all((q > mn + 1e-4) & (q < mx - 1e-4), axis=-1)
            frente = np.where(dentro, 1.0, np.clip((dv @ normal) / np.maximum(d, 1e-6) + 0.3, 0, 1))
            w = np.clip(1 - d / raio, 0, 1) ** 2 * frente
            livre *= 1 - 0.55 * w
        return np.clip(1 - livre, 0, 1), oculto

    def _resolver_faces_coplanares(self, cubos):
        """
        Duas faces no MESMO plano, viradas para o mesmo lado e uma por cima da outra "brigam" no jogo
        (z-fighting: a textura pisca). Resolve sozinho:
          - uma face inteira dentro da outra -> esconde a menor (enchimentos por dentro, fundo da boca);
          - sobreposição parcial -> infla o cubo menor em 0,04 (some da briga sem mudar o visual).
        Usa a pose de repouso.
        """
        pose = geo.Pose(self._ossos_json())
        escondidas, infladas = 0, 0
        vol = lambda c: c.tamanho[0] * c.tamanho[1] * c.tamanho[2]  # noqa: E731
        for _passo in range(10):
            infos = []
            for c in cubos:
                cj = c.como_json()
                e = c.inflar or 0.0
                org = [v - e for v in c.origem]
                tam = [v + 2 * e for v in c.tamanho]
                for f in geo.FACES:
                    if f in c.ocultar:
                        continue
                    fw, fh = geo.dimensoes_face(f, c.tamanho)
                    if fw == 0 or fh == 0:
                        continue
                    C, U, V = (np.array(v, float) for v in geo.quadro_face(f, org, tam))
                    pts = np.array([C, C + U, C + U + V, C + V])
                    w = pose.transformar(c.osso.nome, geo.girar_no_cubo(cj, pts))
                    n = pose.girar_normal(c.osso.nome, geo.girar_normal_cubo(cj, geo.NORMAIS[f]))
                    ax = int(np.argmax(np.abs(n)))
                    if abs(n[ax]) < 0.9999:
                        continue
                    infos.append((c, f, ax, int(np.sign(n[ax])), float(w[:, ax].mean()), w))
            mudou = False
            for i in range(len(infos)):
                ci, fi, axi, si, pi, wi = infos[i]
                for j in range(i + 1, len(infos)):
                    cj_, fj, axj, sj, pj, wj = infos[j]
                    if cj_ is ci or axi != axj or si != sj or abs(pi - pj) > 0.02:
                        continue
                    if fi in ci.ocultar or fj in cj_.ocultar:
                        continue
                    comum, a_i, a_j = geo.sobreposicao_faces(wi, wj, axi)
                    if comum < 1e-3:
                        continue
                    if comum >= 0.995 * min(a_i, a_j) and not (ci.inflar or cj_.inflar):
                        (cj_.ocultar.add(fj) if a_j <= a_i else ci.ocultar.add(fi))
                        escondidas += 1
                        mudou = True
                        continue
                    # infla o menor; cada cubo inflado recebe um valor diferente (0,03; 0,045; 0,06...)
                    # para que dois pedaços encostados nunca voltem a ficar no mesmo plano
                    cand = min((ci, cj_), key=vol)
                    if cand.inflar and cand.inflar >= 0.12:
                        cand = max((ci, cj_), key=vol)
                    cand.inflar = round((cand.inflar or 0.0) + 0.03 + 0.015 * (infladas % 4), 3)
                    infladas += 1
                    mudou = True
            if not mudou:
                break
        return escondidas, infladas

    def _caixa_do_grupo(self, cubo):
        """Origem e tamanho da caixa que envolve o cubo e os irmãos do mesmo grupo."""
        membros = [cubo] + [c for c in cubo.osso.cubos if c is not cubo and cubo.grupo is not None
                            and c.grupo == cubo.grupo]
        mn = np.min([c.origem for c in membros], axis=0)
        mx = np.max([np.array(c.origem) + np.array(c.tamanho) for c in membros], axis=0)
        return mn, mx - mn

    def _bordas_internas(self, cubo, pts, du, dv):
        """
        Quais bordas da face continuam em outro cubo do mesmo grupo (ex.: as partes de um
        cubo_arredondado). Nessas bordas não se desenha realce/sombra de quina, senão aparecem
        listras no meio da superfície.
        """
        h, w = pts.shape[:2]
        vazio = {"cima": np.zeros(w, bool), "baixo": np.zeros(w, bool),
                 "esq": np.zeros(h, bool), "dir": np.zeros(h, bool)}
        if cubo.grupo is None:
            return vazio
        irmaos = [c for c in cubo.osso.cubos if c is not cubo and c.grupo == cubo.grupo]
        if not irmaos:
            return vazio

        def dentro(q):
            r = np.zeros(q.shape[:-1], bool)
            for c in irmaos:
                mn = np.array(c.origem)
                mx = mn + np.array(c.tamanho)
                r |= np.all((q > mn - 1e-4) & (q < mx + 1e-4), axis=-1)
            return r
        return {"cima": dentro(pts[0] - dv), "baixo": dentro(pts[-1] + dv),
                "esq": dentro(pts[:, 0] - du), "dir": dentro(pts[:, -1] + du)}

    # ------------------------------------------------------------- empacotar
    def _empacotar(self, pedidos):
        """Empacota os retângulos das faces em prateleiras; escolhe a largura que gasta menos área."""
        maior = max(w for _, _, w, _ in pedidos)
        melhor = None
        larguras = [self.largura_textura] if self.largura_textura else [2 ** k for k in range(4, 12) if 2 ** k >= maior]
        ordem = sorted(pedidos, key=lambda p: (-p[3], -p[2]))
        for largura in larguras:
            x = y = alt_prat = 0
            pos = {}
            for chave, face, w, h in ordem:
                if x + w > largura:
                    x, y, alt_prat = 0, y + alt_prat, 0
                pos[(chave, face)] = (x, y)
                x += w
                alt_prat = max(alt_prat, h)
            altura = 16
            while altura < y + alt_prat:
                altura *= 2
            custo = (largura * altura, abs(largura - altura))
            if melhor is None or custo < melhor[0]:
                melhor = (custo, largura, altura, pos)
        return melhor[1], melhor[2], melhor[3]

    # ---------------------------------------------------------------- gerar
    def gerar(self):
        """Pinta a textura e monta os JSONs. Devolve (geo_json, anim_json, imagem, relatorio)."""
        if not self.lista_materiais:
            raise ValueError("defina pelo menos um material com m.material(...)")
        dens = self.densidade
        cubos = self.todos_cubos()
        pedidos, avisos = [], []
        escondidas, infladas = self._resolver_faces_coplanares(cubos)
        self._anti_piscar = (escondidas, infladas)
        for c in cubos:
            for f in geo.FACES:
                if f in c.ocultar:
                    continue
                fw, fh = geo.dimensoes_face(f, c.tamanho)
                if fw == 0 or fh == 0:
                    continue         # face sem área (lados de um plano)
                w, h = fw * dens, fh * dens
                if abs(w - round(w)) > 1e-6 or abs(h - round(h)) > 1e-6:
                    avisos.append(f"{c.osso.nome}: face {f} mede {fw}x{fh} -> {w}x{h} texels (não inteiro, pixel esticado)")
                pedidos.append((self.id_cubo(c), f, max(1, int(round(w))), max(1, int(round(h)))))
        tw, th, pos = self._empacotar(pedidos)
        tamanhos = {(k, f): (w, h) for k, f, w, h in pedidos}
        img = np.zeros((th, tw, 4), dtype=np.uint8)

        ossos_json = self._ossos_json()
        pose = geo.Pose(ossos_json)
        caixas = self._caixas_mundo(pose)
        grupos = [c.grupo for c in cubos]
        ocultos_total = 0
        cubos_json = {o.nome: [] for o in self.ossos.values()}
        for c in cubos:
            cid = self.id_cubo(c)
            cj = c.como_json()
            uv = {}
            x0, y0, z0 = c.origem
            W, H, D = c.tamanho
            for f in geo.FACES:
                if f in c.ocultar or (cid, f) not in tamanhos:
                    continue
                w, h = tamanhos[(cid, f)]
                u0, v0 = pos[(cid, f)]
                C, U, V = (np.array(v, float) for v in geo.quadro_face(f, c.origem, c.tamanho))
                jj, ii = np.mgrid[0:h, 0:w]
                local_pts = C + U * ((ii + 0.5) / w)[..., None] + V * ((jj + 0.5) / h)[..., None]
                g0, gt = self._caixa_do_grupo(c)
                rel = (local_pts - g0) / np.maximum(gt, 1e-6)   # 0..1 no grupo (cubo arredondado inteiro)
                mundo = pose.transformar(c.osso.nome, geo.girar_no_cubo(cj, local_pts.reshape(-1, 3))).reshape(h, w, 3)
                normal = pose.girar_normal(c.osso.nome, geo.girar_normal_cubo(cj, geo.NORMAIS[f]))
                ao, oculto = self._oclusao(cid, mundo, normal, caixas, grupos=grupos)
                ocultos_total += int(oculto.sum())
                # A pintura usa as coordenadas como foram ESCRITAS no script (com a rotação do próprio
                # cubo, mas sem a rotação dos ossos): assim "abaixo(35)", esferas, listras e decalques
                # caem onde o autor pensou mesmo num osso inclinado. A oclusão usa a pose real.
                autor = geo.girar_no_cubo(cj, local_pts.reshape(-1, 3)).reshape(h, w, 3)
                normal_autor = geo.girar_normal_cubo(cj, geo.NORMAIS[f])
                ctx = Contexto(self, c, f, w, h, autor, normal_autor, rel, ao, oculto)
                ctx.p_mundo, ctx.n_mundo = mundo, normal
                ctx.borda_interna = self._bordas_internas(c, local_pts, U / w, V / h)
                for camada in c.pintura + c.faces.get(f, []):
                    camada(ctx)
                pintado = sombrear_e_quantizar(ctx)
                img[v0:v0 + h, u0:u0 + w] = pintado
                if not (pintado[..., 3] > 0).any():
                    continue        # face toda recortada (ponta de garra): nem entra no modelo
                # Nome da face no arquivo = nome que o GeckoLib usa (conferido no código do GeckoLib 5.5):
                # a face pintada no lado +X do arquivo ("east" aqui) é a "west" dele, e vice-versa.
                chave = geo.CHAVE_ARQUIVO.get(f, f)
                if f == "down":
                    uv[chave] = {"uv": [u0, v0 + h], "uv_size": [w, -h]}
                else:
                    uv[chave] = {"uv": [u0, v0], "uv_size": [w, h]}
            cj["uv"] = uv
            cubos_json[c.osso.nome].append(cj)
        for o in ossos_json:
            if cubos_json[o["name"]]:
                o["cubes"] = cubos_json[o["name"]]

        todos = np.array([p for (mn, mx) in caixas for p in (mn, mx)]) if caixas else np.zeros((1, 3))
        if self.deslocamentos:
            def delta_de(nome):
                d = np.zeros(3)
                while nome is not None:
                    if nome in self.deslocamentos:
                        d += self.deslocamentos[nome]
                    nome = self.ossos[nome].pai if hasattr(self.ossos[nome], "pai") else None
                return d
            for o in ossos_json:
                d = delta_de(o["name"])
                if not d.any():
                    continue
                o["pivot"] = [round(float(a + b), 4) for a, b in zip(o["pivot"], d)]
                for cj in o.get("cubes", []):
                    cj["origin"] = [round(float(a + b), 4) for a, b in zip(cj["origin"], d)]
                    if "pivot" in cj:
                        cj["pivot"] = [round(float(a + b), 4) for a, b in zip(cj["pivot"], d)]
            todos = todos + np.array([0, max(v[1] for v in self.deslocamentos.values()), 0])
        k = self.escala
        if abs(k - 1.0) > 1e-9:
            def esc(v):
                return [round(float(x) * k, 4) for x in v]
            for o in ossos_json:
                o["pivot"] = esc(o["pivot"])
                for cj in o.get("cubes", []):
                    cj["origin"] = esc(cj["origin"])
                    cj["size"] = esc(cj["size"])
                    if "pivot" in cj:
                        cj["pivot"] = esc(cj["pivot"])
                    if cj.get("inflate"):
                        cj["inflate"] = round(cj["inflate"] * k, 4)
            todos = todos * k
        largura_vis = max(1.0, float(np.ceil(max(np.abs(todos[:, 0]).max(), np.abs(todos[:, 2]).max()) * 2 / 16 + 1)))
        altura_vis = max(1.0, float(np.ceil(todos[:, 1].max() / 16 + 1)))
        geo_json = {
            "format_version": "1.12.0",
            "minecraft:geometry": [{
                "description": {
                    "identifier": f"geometry.{self.nome}",
                    "texture_width": tw,
                    "texture_height": th,
                    "visible_bounds_width": largura_vis,
                    "visible_bounds_height": altura_vis,
                    "visible_bounds_offset": [0, altura_vis / 2, 0],
                },
                "bones": ossos_json,
            }],
        }
        animacoes = self.animacoes
        if abs(self.escala - 1.0) > 1e-9:
            import copy

            def esc_canal(v):
                if isinstance(v, list):
                    return [x * self.escala if isinstance(x, (int, float)) else f"({x}) * {self.escala}" for x in v]
                if isinstance(v, dict):          # chaves por tempo
                    return {t: esc_canal(x) if not isinstance(x, dict) else
                            {kk: esc_canal(vv) for kk, vv in x.items()} for t, x in v.items()}
                return v
            animacoes = copy.deepcopy(self.animacoes)
            for a in animacoes.values():
                for canais in a.get("bones", {}).values():
                    if "position" in canais:
                        canais["position"] = esc_canal(canais["position"])
        anim_json = {"format_version": "1.8.0", "animations": {
            f"animation.{self.nome}.{n}": a for n, a in animacoes.items()}}
        relatorio = {"textura": (tw, th), "cubos": len(cubos), "ossos": len(self.ossos),
                     "texels_ocultos": ocultos_total, "avisos": avisos}
        return geo_json, anim_json, Image.fromarray(img, "RGBA"), relatorio

    def salvar(self, pasta=None, modelos=None, animacoes=None, texturas=None, silencioso=False):
        """
        Grava os três arquivos. Ou passe uma pasta só, ou as três pastas separadas
        (ex.: as do mod: assets/<modid>/geckolib/models/entity, .../animations/entity, textures/entity).
        Devolve os caminhos gravados.
        """
        modelos = modelos or pasta
        animacoes = animacoes or pasta
        texturas = texturas or pasta
        geo_json, anim_json, img, rel = self.gerar()
        caminhos = {}
        for p in {modelos, animacoes, texturas}:
            os.makedirs(p, exist_ok=True)
        caminhos["geo"] = os.path.join(modelos, f"{self.nome}.geo.json")
        with open(caminhos["geo"], "w", encoding="utf-8") as f:
            json.dump(geo_json, f, indent=1)
        if self.animacoes:
            caminhos["anim"] = os.path.join(animacoes, f"{self.nome}.animation.json")
            with open(caminhos["anim"], "w", encoding="utf-8") as f:
                json.dump(anim_json, f, indent=1)
        caminhos["png"] = os.path.join(texturas, f"{self.nome}.png")
        img.save(caminhos["png"])
        if not silencioso:
            print(f"{self.nome}: textura {rel['textura'][0]}x{rel['textura'][1]}, {rel['ossos']} ossos, "
                  f"{rel['cubos']} cubos, {rel['texels_ocultos']} texels escondidos")
            for a in rel["avisos"]:
                print("  AVISO:", a)
        return caminhos
