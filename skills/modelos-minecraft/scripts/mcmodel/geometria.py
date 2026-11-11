"""
Geometria compartilhada pelo gerador e pelo renderizador.

Coordenadas = as do arquivo .geo.json (Bedrock/GeckoLib): 16 unidades = 1 bloco, Y para cima,
a criatura olha para -Z (norte). +X é o lado ESQUERDO da criatura (aparece à direita de quem
olha para o rosto dela).

Mapeamento das faces, conferido no Blockbench (que reproduz o GeckoLib/Bedrock):
cada face tem um canto C (onde fica o texel 0,0), um vetor U (direção das colunas, largura total)
e um vetor V (direção das linhas, altura total). "down" é gravada com uv_size negativo em V.
"""
import math

import numpy as np

FACES = ("north", "south", "east", "west", "up", "down")

NORMAIS = {
    "north": (0, 0, -1), "south": (0, 0, 1), "east": (1, 0, 0),
    "west": (-1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0),
}


def quadro_face(face, origem, tamanho):
    """(C, U, V) da face, em coordenadas do modelo (antes de rotações)."""
    x0, y0, z0 = origem
    W, H, D = tamanho
    x1, y1, z1 = x0 + W, y0 + H, z0 + D
    return {
        "north": ((x0, y1, z0), (W, 0, 0), (0, -H, 0)),
        "south": ((x1, y1, z1), (-W, 0, 0), (0, -H, 0)),
        "west": ((x0, y1, z1), (0, 0, -D), (0, -H, 0)),
        "east": ((x1, y1, z0), (0, 0, D), (0, -H, 0)),
        "up": ((x0, y1, z1), (W, 0, 0), (0, 0, -D)),
        "down": ((x0, y0, z1), (W, 0, 0), (0, 0, -D)),
    }[face]


def quadro_uv(face, origem, tamanho):
    """
    (C, U, V) tal que o ponto C + s*U + t*V recebe a coordenada de textura (u + s*su, v + t*sv),
    onde uv=[u, v] e uv_size=[su, sv] (valem tamanhos negativos). É a regra do GeckoLib/Bedrock,
    usada pelo renderizador para ler QUALQUER .geo.json. Igual a quadro_face, exceto "down".
    """
    if face == "down":
        x0, y0, z0 = origem
        W, H, D = tamanho
        return (x0, y0, z0), (W, 0, 0), (0, 0, D)
    return quadro_face(face, origem, tamanho)


def dimensoes_face(face, tamanho):
    W, H, D = tamanho
    return {"north": (W, H), "south": (W, H), "east": (D, H), "west": (D, H), "up": (W, D), "down": (W, D)}[face]


# ------------------------------------------------------------------ rotações

def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def matriz_rotacao(rot):
    """
    Matriz 3x3 da rotação Bedrock [rx, ry, rz] (graus), no espaço do arquivo.
    Ordem e sinais calibrados contra o Blockbench (ver ferramenta calibrar no SKILL.md).
    """
    if not rot or not any(rot):
        return np.eye(3)
    rx, ry, rz = (math.radians(v) for v in rot)
    return _rz(-rz) @ _ry(ry) @ _rx(-rx)


class Pose:
    """
    Transformação de cada osso numa pose (descanso ou animada).
    extra: {nome_osso: {"rotation": [..], "position": [..], "scale": [..]}} vindo da animação.
    """

    def __init__(self, ossos, extra=None):
        self.ossos = {o["name"]: o for o in ossos}
        self.extra = extra or {}
        self._cache = {}

    def transformar(self, nome_osso, pts):
        """Leva pontos (N,3) do espaço do modelo para o espaço do mundo, subindo a cadeia de ossos."""
        pts = np.asarray(pts, dtype=float)
        nome = nome_osso
        while nome:
            o = self.ossos[nome]
            piv = np.array(o.get("pivot", [0, 0, 0]), dtype=float)
            rot = list(o.get("rotation", [0, 0, 0]))
            ex = self.extra.get(nome, {})
            if "rotation" in ex:
                rot = [a + b for a, b in zip(rot, ex["rotation"])]
            esc = ex.get("scale")
            pts = pts - piv
            if esc is not None:
                pts = pts * np.array(esc, dtype=float)
            pts = pts @ matriz_rotacao(rot).T + piv
            if "position" in ex:
                p = ex["position"]
                pts = pts + np.array([-p[0], p[1], p[2]], dtype=float)
            nome = o.get("parent")
        return pts

    def girar_normal(self, nome_osso, n):
        n = np.asarray(n, dtype=float)
        nome = nome_osso
        while nome:
            o = self.ossos[nome]
            rot = list(o.get("rotation", [0, 0, 0]))
            ex = self.extra.get(nome, {})
            if "rotation" in ex:
                rot = [a + b for a, b in zip(rot, ex["rotation"])]
            n = n @ matriz_rotacao(rot).T
            nome = o.get("parent")
        return n


def girar_no_cubo(cubo, pts):
    """Aplica a rotação própria do cubo (em torno do pivô dele)."""
    rot = cubo.get("rotation")
    if not rot or not any(rot):
        return np.asarray(pts, dtype=float)
    piv = np.array(cubo.get("pivot", cubo["origin"]), dtype=float)
    return (np.asarray(pts, dtype=float) - piv) @ matriz_rotacao(rot).T + piv


def girar_normal_cubo(cubo, n):
    rot = cubo.get("rotation")
    if not rot or not any(rot):
        return np.asarray(n, dtype=float)
    return np.asarray(n, dtype=float) @ matriz_rotacao(rot).T


# Nome da face no .geo.json (convenção do GeckoLib) para cada face como esta biblioteca a pinta.
# Conferido no código do GeckoLib 5.5 (GeometryCube/VertexSet/GeometryQuadUvs): o GeckoLib inverte o X
# do arquivo e desenha a UV "east" no lado -X do arquivo (e "west" no +X), com a textura espelhada na
# horizontal em relação ao que se supunha. Trocar só os nomes leste/oeste deixa tudo igual ao jogo.
CHAVE_ARQUIVO = {"east": "west", "west": "east"}
FACE_DA_CHAVE = {"west": "east", "east": "west"}


def _recortar_poligono(sujeito, recorte):
    """Sutherland–Hodgman: interseção de dois polígonos convexos 2D (listas de pontos)."""
    def dentro(p, a, b):
        return (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0]) >= -1e-9

    def cruzamento(p1, p2, a, b):
        x1, y1 = p1
        x2, y2 = p2
        x3, y3 = a
        x4, y4 = b
        den = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(den) < 1e-12:
            return p2
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / den
        return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))

    saida = list(sujeito)
    for i in range(len(recorte)):
        a, b = recorte[i], recorte[(i + 1) % len(recorte)]
        entrada, saida = saida, []
        if not entrada:
            break
        s = entrada[-1]
        for e in entrada:
            if dentro(e, a, b):
                if not dentro(s, a, b):
                    saida.append(cruzamento(s, e, a, b))
                saida.append(e)
            elif dentro(s, a, b):
                saida.append(cruzamento(s, e, a, b))
            s = e
    return saida


def area_poligono(p):
    if len(p) < 3:
        return 0.0
    return abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2


def _ccw(p):
    return p if sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p))) > 0 else p[::-1]


def sobreposicao_faces(cantos_a, cantos_b, eixo):
    """
    Área em comum de duas faces retangulares no mesmo plano (cantos em ordem C, C+U, C+U+V, C+V; 3D).
    eixo = eixo da normal (0, 1 ou 2). Devolve (área comum, área a, área b).
    """
    o = [k for k in range(3) if k != eixo]
    pa = _ccw([(float(p[o[0]]), float(p[o[1]])) for p in cantos_a])
    pb = _ccw([(float(p[o[0]]), float(p[o[1]])) for p in cantos_b])
    inter = _recortar_poligono(pa, pb)
    return area_poligono(inter), area_poligono(pa), area_poligono(pb)
