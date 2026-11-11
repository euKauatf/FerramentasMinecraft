"""
Renderizador de prévias para qualquer .geo.json (GeckoLib/Bedrock) + textura, com rotações de
ossos e cubos, pose animada, z-buffer e a iluminação de entidades do Minecraft.

Funções principais:
    renderizar(geo, textura, ...)   -> imagem de uma vista
    folha(geo, textura, ...)        -> várias vistas lado a lado, com rótulos
    gif(geo, textura, anim, nome)   -> animação em GIF
    atlas(geo, textura)             -> textura ampliada com grade e o nome de cada face

geo/textura/anim podem ser caminhos ou objetos já carregados (dict / PIL.Image).
"""
import json
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def fonte(tam=13):
    """Fonte com acentos (a padrão do Pillow não tem 'ê', 'ç'...)."""
    for nome in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            pass
    return ImageFont.load_default()

from . import geometria as g
from .animacao import pose_em

LUZ0 = np.array([0.2, 1.0, -0.7]) / np.linalg.norm([0.2, 1.0, -0.7])
LUZ1 = np.array([-0.2, 1.0, 0.7]) / np.linalg.norm([-0.2, 1.0, 0.7])

VISTAS = {
    "frente": (0, 0), "tras": (180, 0), "esquerda": (90, 0), "direita": (-90, 0),
    "3/4": (32, 18), "3/4 tras": (148, 18), "3/4 dir": (-32, 18), "cima": (0, 89.9), "baixo": (0, -89.9),
}


def carregar_geo(geo):
    if isinstance(geo, str):
        with open(geo, encoding="utf-8") as f:
            geo = json.load(f)
    if "minecraft:geometry" in geo:
        geo = geo["minecraft:geometry"][0]
    return geo


def carregar_img(tex):
    return (Image.open(tex) if isinstance(tex, str) else tex).convert("RGBA")


def carregar_anims(anim):
    if anim is None:
        return {}
    if isinstance(anim, str):
        with open(anim, encoding="utf-8") as f:
            anim = json.load(f)
    return anim.get("animations", anim)


def _faces_do_modelo(geo, extra=None):
    """Lista de (P0, P1, P3, normal, regiao_uv) já posicionados no mundo."""
    ossos = geo["bones"]
    pose = g.Pose(ossos, extra)
    faces = []
    for o in ossos:
        for c in o.get("cubes", []):
            uvs = c.get("uv")
            if not isinstance(uvs, dict):
                uvs = _box_uv(c)
            infl = c.get("inflate", 0)
            origem = [v - infl for v in c["origin"]]
            tam = [v + 2 * infl for v in c["size"]]
            for chave in g.FACES:
                if chave not in uvs:
                    continue
                f = g.FACE_DA_CHAVE.get(chave, chave)     # a chave do arquivo segue a convenção do GeckoLib
                C, U, V = (np.array(v, float) for v in g.quadro_uv(f, origem, tam))
                pts = np.array([C, C + U, C + V])
                pts = pose.transformar(o["name"], g.girar_no_cubo(c, pts))
                n = pose.girar_normal(o["name"], g.girar_normal_cubo(c, g.NORMAIS[f]))
                faces.append((pts[0], pts[1], pts[2], n, uvs[chave]["uv"], uvs[chave]["uv_size"]))
    return faces


def _box_uv(c):
    """UV no formato antigo (box UV: "uv": [u, v]) convertido para por-face."""
    u, v = c.get("uv", [0, 0])
    x, y, z = c["size"]
    return {
        "east": {"uv": [u, v + z], "uv_size": [z, y]}, "north": {"uv": [u + z, v + z], "uv_size": [x, y]},
        "west": {"uv": [u + z + x, v + z], "uv_size": [z, y]}, "south": {"uv": [u + 2 * z + x, v + z], "uv_size": [x, y]},
        "up": {"uv": [u + z, v], "uv_size": [x, z]}, "down": {"uv": [u + z + x, v + z], "uv_size": [x, -z]},
    }


def _camera(yaw, pitch):
    a, b = math.radians(yaw), math.radians(pitch)
    ry = np.array([[math.cos(a), 0, math.sin(a)], [0, 1, 0], [-math.sin(a), 0, math.cos(a)]])
    rx = np.array([[1, 0, 0], [0, math.cos(b), math.sin(b)], [0, -math.sin(b), math.cos(b)]])
    return rx @ ry


def renderizar(geo, textura, vista="3/4", escala=None, extra=None, fundo=(232, 234, 238, 255),
               altura_alvo=420, margem=12, limites=None, sombra_chao=True):
    """
    Renderiza uma vista. vista: nome em VISTAS ou (yaw, pitch) em graus.
    escala: pixels por unidade do modelo (None = ajusta para ~altura_alvo).
    extra: pose animada (ver animacao.pose_em). limites: força a caixa de enquadramento.
    """
    geo = carregar_geo(geo)
    tex = np.array(carregar_img(textura))
    th, tw = tex.shape[:2]
    escx = tw / geo["description"].get("texture_width", tw)
    escy = th / geo["description"].get("texture_height", th)
    yaw, pitch = VISTAS[vista] if isinstance(vista, str) else vista
    M = _camera(yaw, pitch)
    faces = _faces_do_modelo(geo, extra)
    if not faces:
        return Image.new("RGBA", (64, 64), fundo)
    todos = np.array([p for f in faces for p in (f[0], f[1], f[2], f[1] + f[2] - f[0])]) @ M.T
    if limites is None:
        mn, mx = todos.min(0), todos.max(0)
    else:
        mn, mx = limites
    if escala is None:
        escala = max(2, int(altura_alvo / max(1e-6, mx[1] - mn[1], (mx[0] - mn[0]) * 0.8)))
    W = int(math.ceil((mx[0] - mn[0]) * escala)) + 2 * margem
    H = int(math.ceil((mx[1] - mn[1]) * escala)) + 2 * margem
    cor = np.zeros((H, W, 3))
    cor[:] = fundo[:3]
    alfa = np.zeros((H, W), dtype=bool)
    zbuf = np.full((H, W), np.inf)

    def tela(p):
        return np.array([(p[0] - mn[0]) * escala + margem, (mx[1] - p[1]) * escala + margem, p[2]])

    for P0, P1, P3, n, uv, tam in faces:
        nv = M @ n
        if nv[2] > 1e-6:
            continue  # de costas
        a, b, c = tela(M @ P0), tela(M @ P1), tela(M @ P3)
        e1, e2 = b - a, c - a
        det = e1[0] * e2[1] - e1[1] * e2[0]
        if abs(det) < 1e-9:
            continue
        cantos = np.array([a, b, c, b + e2])
        x0, y0 = np.floor(cantos[:, :2].min(0)).astype(int)
        x1, y1 = np.ceil(cantos[:, :2].max(0)).astype(int)
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1 + 1), min(H, y1 + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        qx, qy = xx + 0.5 - a[0], yy + 0.5 - a[1]
        s = (qx * e2[1] - qy * e2[0]) / det
        t = (e1[0] * qy - e1[1] * qx) / det
        dentro = (s >= 0) & (s < 1) & (t >= 0) & (t < 1)
        if not dentro.any():
            continue
        z = a[2] + s * e1[2] + t * e2[2]
        su, sv = tam
        u0, v0 = uv
        n_u, n_v = max(1, int(round(abs(su)))), max(1, int(round(abs(sv))))
        ci = np.clip(np.floor(s * n_u).astype(int), 0, n_u - 1)
        cj = np.clip(np.floor(t * n_v).astype(int), 0, n_v - 1)
        col = (u0 + ci) if su >= 0 else (u0 - 1 - ci)
        lin = (v0 + cj) if sv >= 0 else (v0 - 1 - cj)
        col = np.clip((col * escx).astype(int), 0, tw - 1)
        lin = np.clip((lin * escy).astype(int), 0, th - 1)
        amostra = tex[lin, col]
        ok = dentro & (amostra[..., 3] >= 26) & (z < zbuf[y0:y1, x0:x1])
        if not ok.any():
            continue
        brilho = min(1.0, 0.4 + 0.6 * (max(0, n @ LUZ0) + max(0, n @ LUZ1)))
        reg = cor[y0:y1, x0:x1]
        reg[ok] = amostra[ok][:, :3] * brilho
        zbuf[y0:y1, x0:x1][ok] = z[ok]
        alfa[y0:y1, x0:x1][ok] = True

    img = np.zeros((H, W, 4), dtype=np.uint8)
    img[..., :3] = np.clip(cor, 0, 255).astype(np.uint8)
    img[..., 3] = np.where(alfa, 255, fundo[3])
    if fundo[3] == 255:
        img[..., 3] = 255
    return Image.fromarray(img, "RGBA")


def folha(geo, textura, vistas=("frente", "3/4", "esquerda", "tras", "3/4 tras", "cima"), extra=None,
          altura_alvo=360, fundo=(232, 234, 238, 255), titulo=None):
    """Várias vistas na mesma escala, lado a lado, com o nome de cada uma."""
    geo = carregar_geo(geo)
    imgs = []
    escala = None
    for v in vistas:
        im = renderizar(geo, textura, v, escala=escala, extra=extra, fundo=fundo, altura_alvo=altura_alvo)
        if escala is None:
            escala = _escala_usada(geo, v, altura_alvo, extra)
        imgs.append((v, im))
    alt = max(im.height for _, im in imgs) + 22 + (24 if titulo else 0)
    larg = sum(im.width for _, im in imgs) + 10 * (len(imgs) + 1)
    out = Image.new("RGBA", (larg, alt), fundo)
    d = ImageDraw.Draw(out)
    topo = 24 if titulo else 0
    if titulo:
        d.text((10, 4), titulo, fill=(40, 40, 50, 255), font=fonte(14))
    x = 10
    for nome, im in imgs:
        out.paste(im, (x, topo + alt - topo - 22 - im.height))
        d.text((x + 4, alt - 18), nome if isinstance(nome, str) else str(nome), fill=(70, 70, 80, 255), font=fonte(13))
        x += im.width + 10
    return out


def _escala_usada(geo, vista, altura_alvo, extra):
    yaw, pitch = VISTAS[vista] if isinstance(vista, str) else vista
    M = _camera(yaw, pitch)
    faces = _faces_do_modelo(geo, extra)
    todos = np.array([p for f in faces for p in (f[0], f[1], f[2], f[1] + f[2] - f[0])]) @ M.T
    mn, mx = todos.min(0), todos.max(0)
    return max(2, int(altura_alvo / max(1e-6, mx[1] - mn[1], (mx[0] - mn[0]) * 0.8)))


def gif(geo, textura, anims, nome_anim, saida, vista="3/4", fps=15, altura_alvo=300, voltas=1,
        fundo=(232, 234, 238, 255)):
    """Grava um GIF da animação (enquadramento fixo para não "tremer")."""
    geo = carregar_geo(geo)
    anims = carregar_anims(anims)
    chave = nome_anim if nome_anim in anims else next((k for k in anims if k.endswith("." + nome_anim)), None)
    if chave is None:
        raise KeyError(f"animação '{nome_anim}' não encontrada. Existem: {list(anims)}")
    an = anims[chave]
    dur = float(an.get("animation_length", 1.0) or 1.0)
    n = max(2, int(dur * fps * voltas))
    poses = [pose_em(an, k / fps) for k in range(n)]
    yaw, pitch = VISTAS[vista] if isinstance(vista, str) else vista
    M = _camera(yaw, pitch)
    pts = []
    for ex in poses:
        for f in _faces_do_modelo(geo, ex):
            pts += [f[0], f[1], f[2], f[1] + f[2] - f[0]]
    pts = np.array(pts) @ M.T
    lim = (pts.min(0), pts.max(0))
    quadros = [renderizar(geo, textura, vista, extra=ex, limites=lim, altura_alvo=altura_alvo, fundo=fundo).convert("RGB")
               for ex in poses]
    quadros[0].save(saida, save_all=True, append_images=quadros[1:], duration=int(1000 / fps), loop=0)
    return saida


def atlas(geo, textura, ampliar=None, grade=True):
    """Textura ampliada com grade de texels e o rótulo (osso:face) de cada região."""
    geo = carregar_geo(geo)
    img = carregar_img(textura)
    tw, th = img.size
    if ampliar is None:
        ampliar = max(2, min(16, 1400 // max(tw, th)))
    big = img.resize((tw * ampliar, th * ampliar), Image.NEAREST)
    fundo = Image.new("RGBA", big.size, (40, 40, 46, 255))
    xadrez = Image.new("RGBA", big.size, (0, 0, 0, 0))
    dx = ImageDraw.Draw(xadrez)
    for y in range(0, big.height, ampliar * 2):
        for x in range(0, big.width, ampliar * 2):
            dx.rectangle([x, y, x + ampliar - 1, y + ampliar - 1], fill=(55, 55, 62, 255))
            dx.rectangle([x + ampliar, y + ampliar, x + 2 * ampliar - 1, y + 2 * ampliar - 1], fill=(55, 55, 62, 255))
    fundo = Image.alpha_composite(fundo, xadrez)
    out = Image.alpha_composite(fundo, big)
    d = ImageDraw.Draw(out)
    if grade and ampliar >= 6:
        for x in range(0, out.width, ampliar):
            d.line([(x, 0), (x, out.height)], fill=(0, 0, 0, 40))
        for y in range(0, out.height, ampliar):
            d.line([(0, y), (out.width, y)], fill=(0, 0, 0, 40))
    letras = {"north": "N", "south": "S", "east": "L", "west": "O", "up": "C", "down": "B"}
    for o in geo["bones"]:
        for k, c in enumerate(o.get("cubes", [])):
            uvs = c.get("uv")
            if not isinstance(uvs, dict):
                continue
            for f, r in uvs.items():
                (u, v), (su, sv) = r["uv"], r["uv_size"]
                x0, x1 = sorted((u, u + su))
                y0, y1 = sorted((v, v + sv))
                d.rectangle([x0 * ampliar, y0 * ampliar, x1 * ampliar - 1, y1 * ampliar - 1], outline=(255, 60, 200, 255))
                if (x1 - x0) * ampliar > 30 and (y1 - y0) * ampliar > 12:
                    d.text((x0 * ampliar + 2, y0 * ampliar + 1), f"{o['name'][:8]}{k}:{letras[f]}", fill=(255, 255, 255, 230))
    return out
