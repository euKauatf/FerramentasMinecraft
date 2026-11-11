"""
Compara o modelo com imagens de referência, lado a lado e na mesma altura.

    python comparar.py modelo.geo.json textura.png ref1.png [ref2.png ...]
                       [--vistas 3/4,frente,esquerda] [--anim X.animation.json --pose idle]
                       [--estilo pasta_do_cobblemon] [--saida comparacao.png]

Monta uma folha com: as referências (fundo removido quando é branco/liso) | o modelo nas vistas
pedidas | opcionalmente um modelo do Cobblemon na mesma vista (--estilo, a pasta baixada por
referencias.py), para comparar acabamento e proporção com um mod que já é bonito.
Também imprime a proporção altura/largura da silhueta de cada imagem e a "cabeça : corpo" estimada,
para ajudar a pegar cabeças pequenas demais ou corpos compridos demais.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

from mcmodel import render  # noqa: E402
from mcmodel.animacao import pose_em  # noqa: E402

FUNDO = (236, 238, 242)


def fonte(tam=14):
    """Fonte com acentos (a padrão do Pillow não tem 'ê', 'ç'...)."""
    from PIL import ImageFont
    for nome in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            pass
    return ImageFont.load_default()


def sem_fundo(im):
    """Recorta a figura: usa o alfa se houver; senão tira a cor da borda (fundo branco/liso)."""
    im = im.convert("RGBA")
    a = np.array(im)
    if (a[..., 3] < 250).mean() > 0.02:
        mask = a[..., 3] > 20
    else:
        borda = np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]]).astype(int)
        cor = np.median(borda, axis=0)
        dist = np.abs(a[..., :3].astype(int) - cor).sum(-1)
        mask = dist > 40
        a[..., 3] = np.where(mask, 255, 0)
        im = Image.fromarray(a)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return im, mask
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)), mask[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def proporcao(mask):
    h, w = mask.shape
    return h / max(1, w)


def no_fundo(im, altura):
    im = im.convert("RGBA")
    esc = altura / im.height
    im = im.resize((max(1, int(im.width * esc)), altura), Image.NEAREST if im.height < altura / 2 else Image.LANCZOS)
    f = Image.new("RGBA", im.size, FUNDO + (255,))
    return Image.alpha_composite(f, im).convert("RGB")


def render_recortado(geo, tex, vista, pose, altura):
    im = render.renderizar(geo, tex, vista, extra=pose, fundo=(0, 0, 0, 0), altura_alvo=altura)
    im, mask = sem_fundo(im)
    return im, mask


def pose_de(anim_path, nome):
    if not anim_path or not nome:
        return None
    with open(anim_path, encoding="utf-8") as f:
        anims = json.load(f)["animations"]
    chave = next((k for k in anims if k.endswith("." + nome) or k.endswith(nome)), None)
    return pose_em(anims[chave], 0.0) if chave else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geo")
    ap.add_argument("textura")
    ap.add_argument("refs", nargs="*")
    ap.add_argument("--vistas", default="3/4,frente,esquerda")
    ap.add_argument("--anim")
    ap.add_argument("--pose", default="idle")
    ap.add_argument("--estilo", help="pasta de um modelo do Cobblemon baixado com referencias.py")
    ap.add_argument("--altura", type=int, default=360)
    ap.add_argument("--saida")
    a = ap.parse_args()

    H = a.altura
    pecas = []   # (imagem, rótulo)
    for r in a.refs:
        im, mask = sem_fundo(Image.open(r))
        pecas.append((no_fundo(im, H), f"ref: {os.path.basename(r)[:28]}  a/l={proporcao(mask):.2f}"))
    pose = pose_de(a.anim, a.pose)
    for v in [x.strip() for x in a.vistas.split(",") if x.strip()]:
        im, mask = render_recortado(a.geo, a.textura, v, pose, H)
        pecas.append((no_fundo(im, H), f"modelo {v}  a/l={proporcao(mask):.2f}"))
    if a.estilo:
        geos = sorted(glob.glob(os.path.join(a.estilo, "*.geo.json")), key=len)
        pngs = [p for p in glob.glob(os.path.join(a.estilo, "*.png")) if not os.path.basename(p).startswith("_")]
        anims = glob.glob(os.path.join(a.estilo, "*.animation.json"))
        if geos and pngs:
            pz = pose_de(anims[0] if anims else None, "ground_idle")
            v = a.vistas.split(",")[0].strip()
            im, mask = render_recortado(geos[0], pngs[0], v, pz, H)
            pecas.append((no_fundo(im, H), f"Cobblemon {os.path.basename(a.estilo)} {v}"))

    marg = 12
    W = sum(p.width for p, _ in pecas) + marg * (len(pecas) + 1)
    folha = Image.new("RGB", (W, H + 40), FUNDO)
    dr = ImageDraw.Draw(folha)
    x = marg
    for im, rot in pecas:
        folha.paste(im, (x, 10))
        dr.text((x, H + 16), rot, fill=(30, 30, 30), font=fonte(13))
        x += im.width + marg
    saida = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.geo)), "previas",
                                    os.path.basename(a.geo).replace(".geo.json", "") + "_comparacao.png")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    folha.save(saida)
    for _, rot in pecas:
        print(rot)
    print(saida)


if __name__ == "__main__":
    main()
