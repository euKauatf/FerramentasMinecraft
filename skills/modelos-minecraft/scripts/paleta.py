"""
Extrai a paleta de uma imagem de referência (arte oficial, foto, desenho do usuário).

    python paleta.py referencia.png [--cores 12] [--saida paleta.png] [--recorte x0,y0,x1,y1]

Ignora o fundo (transparente ou a cor que domina as bordas), agrupa as cores parecidas e imprime:
  - cada cor com a porcentagem da área (as maiores são os materiais principais)
  - uma linha pronta de m.material(...) com rampa() para cada cor principal
Também grava uma imagem com as amostras e as rampas sugeridas, para conferir de olho.
Use --recorte para pegar só uma parte (ex.: só o rosto, para acertar a cor dos olhos).
"""
import argparse
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from mcmodel.cores import hexa, luminancia, para_oklch, rampa  # noqa: E402


def extrair(caminho, n=12, recorte=None):
    img = Image.open(caminho).convert("RGBA")
    if recorte:
        img = img.crop(recorte)
    img.thumbnail((400, 400))
    a = np.array(img)
    px = a.reshape(-1, 4)
    mascara = px[:, 3] > 200
    # fundo = cor mais comum na borda da imagem, se ela dominar a borda
    borda = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    borda = borda[borda[:, 3] > 200][:, :3] // 16
    if len(borda):
        comum, qtd = Counter(map(tuple, borda)).most_common(1)[0]
        if qtd > len(borda) * 0.5:
            mascara &= ~np.all(px[:, :3] // 16 == np.array(comum), axis=1)
    util = px[mascara][:, :3].astype(np.uint8)
    if len(util) < 10:
        raise SystemExit("quase nada sobrou depois de tirar o fundo; use --recorte")
    tira = Image.fromarray(util.reshape(1, -1, 3), "RGB")
    q = tira.quantize(colors=n, method=Image.Quantize.MEDIANCUT, kmeans=3)
    pal = q.getpalette()[: n * 3]
    contagem = Counter(np.array(q).ravel().tolist())
    total = sum(contagem.values())
    cores = [((pal[i * 3], pal[i * 3 + 1], pal[i * 3 + 2]), contagem[i] / total) for i in contagem]
    cores.sort(key=lambda c: -c[1])
    return cores


def agrupar_rampas(cores, tol_matiz=18):
    """Junta cores de matiz parecido (e as neutras entre si) em rampas ordenadas por luminosidade."""
    grupos = []
    for c, f in cores:
        L, C, H = para_oklch(c)
        neutra = C < 0.03
        for g in grupos:
            if g["neutra"] == neutra and (neutra or abs((H - g["H"] + 180) % 360 - 180) < tol_matiz):
                g["cores"].append((c, f, L))
                break
        else:
            grupos.append({"neutra": neutra, "H": H, "cores": [(c, f, L)]})
    saida = []
    for g in grupos:
        ordenadas = sorted(g["cores"], key=lambda x: x[2])
        saida.append(([(c, f) for c, f, _ in ordenadas], sum(f for _, f, _ in ordenadas)))
    saida.sort(key=lambda x: -x[1])
    return saida


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("imagem")
    ap.add_argument("--cores", type=int, default=12)
    ap.add_argument("--saida")
    ap.add_argument("--recorte")
    a = ap.parse_args()
    rec = tuple(int(v) for v in a.recorte.split(",")) if a.recorte else None
    cores = extrair(a.imagem, a.cores, rec)
    print("cor       área   luminosidade  matiz")
    for c, f in cores:
        L, C, H = para_oklch(c)
        print(f"{hexa(c)}  {f*100:5.1f}%   {L:.2f}          {H:5.0f}{'  (neutra)' if C < 0.03 else ''}")
    print("\n# RAMPAS TIRADAS DA REFERÊNCIA (melhor opção: sombras e luzes do desenho oficial).")
    print("# Cores de matiz parecido viram uma rampa (escura -> clara); base = a cor de maior área.")
    print("# Lembre: a luz do jogo escurece frente (x0,74) e lados (x0,5); amarelos escurecidos viram")
    print("# oliva, então puxe a base um tom mais quente/clara se a prévia ficar 'mostarda'.")
    for k, (grupo, area) in enumerate(agrupar_rampas(cores)):
        txt = ", ".join(f'"{hexa(c)}"' for c, _ in grupo)
        maior = max(range(len(grupo)), key=lambda i: grupo[i][1])
        print(f'm.material("mat{k+1}", rampa_manual({txt}, base={maior}))   # {area*100:.0f}% da área')
    print("\n# alternativa: rampas geradas a partir de uma cor só")
    for k, (c, f) in enumerate(cores[:6]):
        print(f'm.material("cor{k+1}", rampa("{hexa(c)}", n=6, base=3))   # {f*100:.0f}% da área')

    saida = a.saida or os.path.splitext(a.imagem)[0] + "_paleta.png"
    t = 34
    im = Image.new("RGBA", (t * 7 + 120, t * len(cores)), (36, 36, 40, 255))
    d = ImageDraw.Draw(im)
    for y, (c, f) in enumerate(cores):
        d.rectangle([0, y * t, t * 2 - 1, (y + 1) * t - 1], fill=c + (255,))
        d.text((t * 2 + 4, y * t + 4), f"{hexa(c)}", fill=(235, 235, 235, 255))
        d.text((t * 2 + 4, y * t + 18), f"{f*100:.1f}%", fill=(170, 170, 170, 255))
        for k, rc in enumerate(rampa(c, n=6, base=3)):
            d.rectangle([120 + t * k, y * t, 120 + t * (k + 1) - 1, (y + 1) * t - 1], fill=rc)
    im.save(saida)
    print("\nimagem:", saida)


if __name__ == "__main__":
    main()
