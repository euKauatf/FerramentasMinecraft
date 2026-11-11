"""
Procura VÃOS: frestas onde se vê o fundo através do modelo (peças que não encostam direito,
junta de membro aberta, degrau entre blocos). Renderiza várias vistas e pinta de magenta todo
buraco pequeno cercado pelo modelo.

    python vaos.py modelo.geo.json textura.png [--anim X.animation.json --pose walk --tempos 0,0.2,0.4]
                   [--altura 700] [--max 0.02] [--saida arq.png]

Só buracos FINOS contam (frestas de até ~1% da altura da imagem); espaços largos, como entre as
pernas ou entre o braço e o corpo, são normais e ficam de fora. --max limita a área (fração da figura).
Com --anim, confere também quadros da animação (frestas que só abrem quando a perna mexe).
Buracos FEITOS DE PROPÓSITO (asa furada de morcego, renda, grade) também aparecem na contagem:
olhe a imagem e ignore os que caem nessas peças.
Saída: imagem com as vistas + lista de vãos por vista (posição na imagem e tamanho).
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage  # noqa: E402

from mcmodel import render  # noqa: E402
from mcmodel.animacao import pose_em  # noqa: E402
from mcmodel.render import fonte  # noqa: E402

VISTAS = ["frente", "3/4", "esquerda", "tras", "3/4 tras", "direita", "cima"]


def achar_vaos(im, frac_max, espessura_max=None):
    """
    Buracos fechados pelo modelo onde se vê o fundo. Só conta como VÃO o buraco FINO (fresta):
    espessura até ~1% da altura da imagem. Espaços largos (entre as pernas, axila, entre o braço e a
    barriga) são normais e ficam de fora.
    """
    a = np.array(im)
    figura = a[..., 3] > 0
    buracos = ndimage.binary_fill_holes(figura) & ~figura
    rot, n = ndimage.label(buracos)
    area_fig = figura.sum()
    esp_max = espessura_max or max(4.0, im.size[1] * 0.012)
    dist = ndimage.distance_transform_edt(buracos)
    vaos = []
    for k in range(1, n + 1):
        m = rot == k
        area = int(m.sum())
        if area < 2 or area > frac_max * area_fig:
            continue
        espessura = 2 * float(dist[m].max())
        if espessura > esp_max:
            continue                      # espaço largo e natural, não é fresta
        ys, xs = np.nonzero(m)
        vaos.append((m, area, int(xs.mean()), int(ys.mean())))
    return vaos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geo")
    ap.add_argument("textura")
    ap.add_argument("--anim")
    ap.add_argument("--pose", default="walk")
    ap.add_argument("--tempos", default="")
    ap.add_argument("--altura", type=int, default=700)
    ap.add_argument("--max", type=float, default=0.02)
    ap.add_argument("--saida")
    a = ap.parse_args()

    poses = [("repouso", None)]
    if a.anim:
        with open(a.anim, encoding="utf-8") as f:
            anims = json.load(f)["animations"]
        k = next((k for k in anims if k.endswith("." + a.pose)), None)
        if k:
            dur = float(anims[k].get("animation_length", 1))
            ts = [float(t) for t in a.tempos.split(",")] if a.tempos else [0, dur * 0.25, dur * 0.5, dur * 0.75]
            poses += [(f"{a.pose} {t:.2f}s", pose_em(anims[k], t)) for t in ts]

    quadros, total = [], 0
    for nome_pose, pose in poses:
        vistas = VISTAS if pose is None else ["frente", "3/4", "esquerda"]
        for v in vistas:
            im = render.renderizar(a.geo, a.textura, v, extra=pose, fundo=(0, 0, 0, 0), altura_alvo=a.altura)
            vaos = achar_vaos(im, a.max)
            total += len(vaos)
            vis = Image.new("RGBA", im.size, (236, 238, 242, 255))
            vis = Image.alpha_composite(vis, im)
            arr = np.array(vis)
            for m, area, x, y in vaos:
                arr[ndimage.binary_dilation(m, iterations=2)] = (255, 0, 255, 255)
            vis = Image.fromarray(arr)
            d = ImageDraw.Draw(vis)
            for m, area, x, y in vaos:
                d.ellipse([x - 14, y - 14, x + 14, y + 14], outline=(255, 0, 255, 255), width=3)
            d.text((6, 4), f"{nome_pose} | {v}: {len(vaos)} vão(s)", fill=(20, 20, 20, 255), font=fonte(16))
            quadros.append(vis.convert("RGB"))
            if vaos:
                print(f"{nome_pose:>14} | {v:<9}: {len(vaos)} vão(s) " +
                      ", ".join(f"({x},{y}) {area}px" for _, area, x, y in vaos[:6]))
    # folha
    lado = 360
    cols = 4
    linhas = (len(quadros) + cols - 1) // cols
    folha = Image.new("RGB", (cols * lado, linhas * lado), (236, 238, 242))
    for i, q in enumerate(quadros):
        q = q.copy()
        q.thumbnail((lado, lado), Image.NEAREST)
        folha.paste(q, ((i % cols) * lado, (i // cols) * lado))
    saida = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.geo)), "previas",
                                    os.path.basename(a.geo).replace(".geo.json", "") + "_vaos.png")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    folha.save(saida)
    print(f"TOTAL: {total} vão(s)" + ("  -> feche as juntas (sobra maior, peça de junta, cubo maior)" if total else "  ok"))
    print(saida)


if __name__ == "__main__":
    main()
