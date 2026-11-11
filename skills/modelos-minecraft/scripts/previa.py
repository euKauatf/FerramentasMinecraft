"""
Prévias de um modelo pronto (feito por esta skill, pelo Blockbench ou por qualquer um).

    python previa.py modelo.geo.json textura.png [--anim arq.animation.json] [--saida pasta]
                     [--vistas frente,3/4,tras] [--gif walk,idle] [--atlas] [--zoom head]

Gera na pasta de saída (padrão: ao lado do .geo.json, em "previas/"):
    <nome>_folha.png     várias vistas na mesma escala
    <nome>_atlas.png     textura ampliada com grade e rótulo das faces (--atlas)
    <nome>_<anim>.gif    animações (--gif)
    <nome>_zoom.png      close-up de um osso e seus filhos, em frente e 3/4 (--zoom NOME_DO_OSSO)
    <nome>_<anim>_quadros.png   6 quadros da animação lado a lado (--quadros walk,attack)
                                (GIF só mostra o 1º quadro quando aberto como imagem; use isto para conferir)
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from mcmodel import render  # noqa: E402


def _so_osso(geo, raiz):
    """Cópia do modelo só com o osso pedido e seus descendentes (para close-ups)."""
    g = render.carregar_geo(geo)
    filhos = {raiz}
    mudou = True
    while mudou:
        mudou = False
        for o in g["bones"]:
            if o.get("parent") in filhos and o["name"] not in filhos:
                filhos.add(o["name"])
                mudou = True
    ossos = []
    for o in g["bones"]:
        o2 = dict(o)
        if o["name"] not in filhos:
            o2.pop("cubes", None)
        ossos.append(o2)
    return dict(g, bones=ossos)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("geo")
    ap.add_argument("textura")
    ap.add_argument("--anim")
    ap.add_argument("--saida")
    ap.add_argument("--vistas", default="frente,3/4,esquerda,tras,3/4 tras,cima")
    ap.add_argument("--gif", default="")
    ap.add_argument("--quadros", default="")
    ap.add_argument("--atlas", action="store_true")
    ap.add_argument("--zoom")
    ap.add_argument("--altura", type=int, default=360)
    ap.add_argument("--escuro", action="store_true", help="fundo escuro (bom para modelos claros)")
    a = ap.parse_args()

    nome = os.path.basename(a.geo).replace(".geo.json", "").replace(".json", "")
    saida = a.saida or os.path.join(os.path.dirname(os.path.abspath(a.geo)), "previas")
    os.makedirs(saida, exist_ok=True)
    fundo = (38, 40, 46, 255) if a.escuro else (232, 234, 238, 255)

    p = os.path.join(saida, f"{nome}_folha.png")
    render.folha(a.geo, a.textura, [v.strip() for v in a.vistas.split(",")], altura_alvo=a.altura,
                 fundo=fundo, titulo=nome).save(p)
    print(p)
    if a.atlas:
        p = os.path.join(saida, f"{nome}_atlas.png")
        render.atlas(a.geo, a.textura).save(p)
        print(p)
    if a.zoom:
        g = _so_osso(a.geo, a.zoom)
        p = os.path.join(saida, f"{nome}_zoom.png")
        render.folha(g, a.textura, ["frente", "3/4", "esquerda"], altura_alvo=420, fundo=fundo,
                     titulo=f"{nome}: {a.zoom}").save(p)
        print(p)
    for an in [x.strip() for x in a.gif.split(",") if x.strip()]:
        if not a.anim:
            sys.exit("--gif precisa de --anim arquivo.animation.json")
        p = os.path.join(saida, f"{nome}_{an}.gif")
        render.gif(a.geo, a.textura, a.anim, an, p, fundo=fundo)
        print(p)


    for an in [x.strip() for x in a.quadros.split(",") if x.strip()]:
        if not a.anim:
            sys.exit("--quadros precisa de --anim arquivo.animation.json")
        p = os.path.join(saida, f"{nome}_{an}_quadros.png")
        quadros(a.geo, a.textura, a.anim, an, fundo).save(p)
        print(p)


def quadros(geo, textura, anim, nome_anim, fundo, n=6, vista="esquerda"):
    from PIL import Image, ImageDraw
    from mcmodel.animacao import pose_em
    anims = render.carregar_anims(anim)
    chave = nome_anim if nome_anim in anims else next((k for k in anims if k.endswith("." + nome_anim)), None)
    if chave is None:
        sys.exit(f"animação '{nome_anim}' não existe. Há: {list(anims)}")
    an = anims[chave]
    dur = float(an.get("animation_length", 1.0) or 1.0)
    tempos = [dur * k / n for k in range(n)]
    imgs = []
    for vista_k in (vista, "3/4"):
        imgs.append([render.renderizar(geo, textura, vista_k, extra=pose_em(an, t), altura_alvo=200, fundo=fundo)
                     for t in tempos])
    larg = max(sum(i.width for i in linha) + 8 * (n + 1) for linha in imgs)
    alt = sum(max(i.height for i in linha) for linha in imgs) + 40
    out = Image.new("RGBA", (larg, alt), fundo)
    d = ImageDraw.Draw(out)
    y = 4
    for linha in imgs:
        x = 8
        for t, im in zip(tempos, linha):
            out.paste(im, (x, y))
            d.text((x + 2, y), f"{t:.2f}s", fill=(90, 90, 100, 255))
            x += im.width + 8
        y += max(i.height for i in linha) + 16
    return out


if __name__ == "__main__":
    main()
