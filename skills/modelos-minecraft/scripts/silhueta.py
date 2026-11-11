"""
Sobrepõe a silhueta do modelo à silhueta de uma referência na MESMA vista e mede onde erra.

    python silhueta.py modelo.geo.json textura.png ref.png --vista esquerda
                       [--recorte x0,y0,x1,y1] [--anim X.animation.json --pose idle] [--saida arq.png]

Serve para anatomia e proporção: lateral (vista "esquerda" ou "direita") contra um desenho de lado
(model sheet, lineart, render de perfil), frente contra uma vista de frente.
- Funciona com render 3D (fundo liso ou transparente) e com lineart (preenche o contorno).
- `--recorte` pega só um pedaço de uma folha de modelo (coordenadas em pixels da imagem original).
- A referência é espelhada automaticamente se isso encaixar melhor (desenho virado para o outro lado).
- As duas silhuetas são postas na mesma altura e alinhadas pelos pés.

Saída: imagem com azul = só na referência (falta no modelo), vermelho = só no modelo (sobra),
cinza = os dois; e uma tabela por faixas de altura (topo -> chão) com a largura de cada um, para
dizer "o pescoço está fino", "a coxa está curta", "a cabeça está pequena", "a cauda está baixa".
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


def mascara_referencia(im):
    a = np.array(im.convert("RGBA")).astype(int)
    if (a[..., 3] < 250).mean() > 0.02:
        m = a[..., 3] > 30
    else:
        borda = np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]])
        fundo = np.median(borda, axis=0)
        m = np.abs(a[..., :3] - fundo).sum(-1) > 60
        m = ndimage.binary_closing(m, iterations=3)          # fecha falhas do traço
        m = ndimage.binary_fill_holes(m)                       # lineart: pinta o miolo
    rot, n = ndimage.label(m)
    if n > 1:                                                  # fica com o maior pedaço (a criatura)
        tam = ndimage.sum(m, rot, range(1, n + 1))
        m = rot == (int(np.argmax(tam)) + 1)
        m = ndimage.binary_fill_holes(m)
    return m


def recortar_bbox(m):
    ys, xs = np.nonzero(m)
    return m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]


def na_altura(m, H):
    im = Image.fromarray((m * 255).astype(np.uint8))
    w = max(1, round(m.shape[1] * H / m.shape[0]))
    return np.array(im.resize((w, H), Image.NEAREST)) > 127


def alinhar(a, b):
    """Põe as duas máscaras (mesma altura) numa tela comum, centradas pela base (pés)."""
    H = a.shape[0]
    W = max(a.shape[1], b.shape[1])

    def centro_base(m):
        base = m[int(H * 0.85):]
        xs = np.nonzero(base.any(0))[0]
        return (xs.min() + xs.max()) / 2 if len(xs) else m.shape[1] / 2
    ca, cb = centro_base(a), centro_base(b)
    off_a = int(round(W / 2 - ca))
    off_b = int(round(W / 2 - cb))
    lo = min(0, off_a, off_b)
    hi = max(W, off_a + a.shape[1], off_b + b.shape[1])
    ta = np.zeros((H, hi - lo), bool)
    tb = np.zeros((H, hi - lo), bool)
    ta[:, off_a - lo:off_a - lo + a.shape[1]] = a
    tb[:, off_b - lo:off_b - lo + b.shape[1]] = b
    return ta, tb


def iou(a, b):
    return (a & b).sum() / max(1, (a | b).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geo")
    ap.add_argument("textura")
    ap.add_argument("ref")
    ap.add_argument("--vista", default="esquerda")
    ap.add_argument("--recorte")
    ap.add_argument("--anim")
    ap.add_argument("--pose", default="idle")
    ap.add_argument("--faixas", type=int, default=10)
    ap.add_argument("--espelhar", choices=("auto", "sim", "nao"), default="auto",
                    help="auto escolhe pelo encaixe; use 'nao'/'sim' quando as formas são muito diferentes "
                         "(o auto pode virar a referência ao contrário)")
    ap.add_argument("--saida")
    a = ap.parse_args()

    ref = Image.open(a.ref)
    if a.recorte:
        x0, y0, x1, y1 = (int(v) for v in a.recorte.split(","))
        ref = ref.crop((x0, y0, x1, y1))
    mr = recortar_bbox(mascara_referencia(ref))
    pose = None
    if a.anim:
        with open(a.anim, encoding="utf-8") as f:
            anims = json.load(f)["animations"]
        k = next((k for k in anims if k.endswith("." + a.pose)), None)
        pose = pose_em(anims[k], 0.0) if k else None
    rm = render.renderizar(a.geo, a.textura, a.vista, extra=pose, fundo=(0, 0, 0, 0), altura_alvo=500)
    mm = recortar_bbox(np.array(rm)[..., 3] > 0)

    H = 500
    mr_h, mm_h = na_altura(mr, H), na_altura(mm, H)
    melhor = None
    opcoes = {"auto": (False, True), "sim": (True,), "nao": (False,)}[a.espelhar]
    for esp in opcoes:
        r = mr_h[:, ::-1] if esp else mr_h
        ta, tb = alinhar(r, mm_h)
        v = iou(ta, tb)
        if melhor is None or v > melhor[0]:
            melhor = (v, esp, ta, tb)
    v, esp, R, M = melhor

    # imagem
    cor = np.full(R.shape + (3,), 245, np.uint8)
    cor[R & ~M] = (60, 110, 230)      # falta no modelo
    cor[M & ~R] = (230, 70, 60)       # sobra no modelo
    cor[R & M] = (150, 150, 160)
    im = Image.fromarray(cor)
    dr = ImageDraw.Draw(im)
    nf = a.faixas
    linhas = []
    for k in range(nf):
        y0, y1 = k * H // nf, (k + 1) * H // nf
        dr.line([(0, y0), (im.width, y0)], fill=(210, 210, 215))
        lr = R[y0:y1].any(0)
        lm = M[y0:y1].any(0)
        wr = lr.sum() / H
        wm = lm.sum() / H
        xr = np.nonzero(lr)[0]
        xm = np.nonzero(lm)[0]
        desloc = ((xm.mean() if len(xm) else 0) - (xr.mean() if len(xr) else 0)) / H
        linhas.append((k, wr, wm, desloc))
        dr.text((4, y0 + 2), f"{k}", fill=(40, 40, 40), font=fonte(12))
    saida = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.geo)), "previas",
                                    os.path.basename(a.geo).replace(".geo.json", "") + f"_silhueta_{a.vista.replace('/', '-')}.png")
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    larg_ref = recortar_bbox(R).shape[1] / H
    larg_mod = recortar_bbox(M).shape[1] / H
    rodape = Image.new("RGB", (im.width, 40), (245, 245, 245))
    ImageDraw.Draw(rodape).text((6, 4), f"azul = falta no modelo   vermelho = sobra   IoU {v:.2f}"
                                f"{'   (ref espelhada)' if esp else ''}", fill=(30, 30, 30), font=fonte(13))
    tela = Image.new("RGB", (im.width, im.height + 40), (245, 245, 245))
    tela.paste(im, (0, 0))
    tela.paste(rodape, (0, im.height))
    tela.save(saida)

    print(f"vista {a.vista}: IoU {v:.2f}  (1 = idêntico; > 0.75 já está bom)")
    print(f"largura total / altura: ref {larg_ref:.2f}  modelo {larg_mod:.2f}")
    print("faixa (0 = topo)  largura ref  largura modelo  diferença  deslocamento")
    for k, wr, wm, dsl in linhas:
        dif = wm - wr
        aviso = ""
        if wr > 0.02 and abs(dif) > 0.06:
            aviso = "  <- modelo LARGO demais aqui" if dif > 0 else "  <- modelo ESTREITO/curto demais aqui"
        print(f"  {k:2d}            {wr:5.2f}        {wm:5.2f}        {dif:+5.2f}     {dsl:+5.2f}{aviso}")
    print(saida)


if __name__ == "__main__":
    main()
