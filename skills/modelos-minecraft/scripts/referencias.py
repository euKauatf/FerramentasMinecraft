"""
Busca referências visuais e salva em D:\\FerramentasMinecraft\\referencias (nunca no C:).

    python referencias.py digimon Agumon [--n 10]       imagens oficiais da Wikimon + folha de contato
    python referencias.py cobblemon charmander [--forma] modelo + textura + animação do Cobblemon,
                                                         já renderizados em várias vistas e estatísticas
    python referencias.py url https://.../imagem.png nome   qualquer imagem (fan art, sprite, foto de figura)
    python referencias.py lista-cobblemon [filtro]      lista os Pokémon disponíveis no Cobblemon

Saída:
    referencias/digimon/<nome>/*.png|jpg  e  _contato.png  (todas lado a lado, para abrir de uma vez)
    referencias/cobblemon/<pasta>/        .geo.json, .png, .animation.json, LICENSE e _vistas.png, _estudo.txt

Os modelos do Cobblemon são CC BY-NC-SA (ver o arquivo license de cada um): servem para ESTUDAR estilo,
proporção, quantidade de cubos e técnica de textura. Não copie geometria nem textura deles para o mod.
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from PIL import Image, ImageDraw  # noqa: E402

# <base>\skills\modelos-minecraft\scripts\referencias.py -> <base>\referencias (D: no PC, C: no notebook)
_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = os.environ.get("MC_REFERENCIAS", os.path.join(_RAIZ, "referencias"))
UA = {"User-Agent": "Mozilla/5.0 (modelos-minecraft skill; estudo pessoal)"}
WIKIMON = "https://wikimon.net/api.php"
GITLAB = "https://gitlab.com/api/v4/projects/cable-mc%2Fcobblemon/repository"
RAIZ_COBBLE = "common/src/main/resources/assets/cobblemon"


def _get(url, binario=False):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        dados = r.read()
    return dados if binario else json.loads(dados.decode("utf-8"))


def _seguro(nome):
    return re.sub(r"[^\w\-. ]", "_", nome).strip().replace(" ", "_")


# ----------------------------------------------------------------------------------------- Digimon
def _pontuar(arquivo, nome):
    """Quanto maior, mais útil para modelar: arte oficial limpa, renders 3D, lineart, zukan."""
    a = arquivo.lower().replace("file:", "")
    n = nome.lower().replace(" ", "").replace("-", "").replace(":", "")
    base, ext = os.path.splitext(a)
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        return -999
    base = base.replace("_", " ")
    compacto = base.replace(" ", "").replace("-", "")
    if not compacto.startswith(n):
        return -999          # imagens de grupo, cartas, pôsteres
    # tira do começo do nome do arquivo os caracteres que formam o nome (com ou sem espaço)
    k, i = 0, 0
    while i < len(base) and k < len(n):
        if base[i] not in " -":
            k += 1
        i += 1
    resto = base[i:].strip()
    p = 0
    if resto == "":
        p += 100             # arte oficial principal
    tabela = {"reference art": 98, "model sheet": 98, "model": 90, "front": 75, "back": 72, "side": 75,
              "movie lineart": 85, "movie head": 60, "movie back": 72, "movie": 50, "3d": 80, "lineart": 70, "zukan": 65, " b": 60, "artbook": 45, "re": 35,
              "rearise": 35, "dw": 30, "survive": 25, "ts": 40, "next0rder": 25, "cs": 20, "new century": 20,
              "super rumble": 25, "up": 10}
    for k, v in tabela.items():
        if resto == k.strip() or resto.startswith(k.strip() + " ") or (" " + k.strip()) in (" " + resto):
            p = max(p, v)
    for ruim in ("vpet", "digimonweb", "deck", "sleeve", "poster", "cutin", "costume", "dcg", "acrylic",
                 "keychain", "sticker", "battle", "map", "racing", "variants", "and ", "art mini", "dot",
                 "illustration", "promo", "art dr", "banner", "collab", "figure"):
        if ruim in resto:
            p -= 80
    if resto[:1].isdigit():
        p += 15              # Agumon3.jpg, Agumon4.jpg... costumam ser artes oficiais alternativas
    if ext == ".gif":
        p -= 30
    return p


def _arquivos_categoria(nome):
    titulos, cont = [], {}
    cat = "Category:Images_of_" + nome.replace(" ", "_")
    while True:
        q = {"action": "query", "list": "categorymembers", "cmtitle": cat, "cmtype": "file",
             "cmlimit": "500", "format": "json", **cont}
        d = _get(WIKIMON + "?" + urllib.parse.urlencode(q))
        titulos += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        if "continue" not in d:
            break
        cont = d["continue"]
    # a categoria nem sempre tem tudo: junta as imagens usadas na página do Digimon
    q = {"action": "query", "titles": nome, "prop": "images", "imlimit": "500", "format": "json"}
    d = _get(WIKIMON + "?" + urllib.parse.urlencode(q))
    for pg in d.get("query", {}).get("pages", {}).values():
        titulos += [i["title"] for i in pg.get("images", [])]
    return list(dict.fromkeys(titulos))


def _urls(titulos):
    out = {}
    for i in range(0, len(titulos), 40):
        q = {"action": "query", "titles": "|".join(titulos[i:i + 40]), "prop": "imageinfo",
             "iiprop": "url|size", "format": "json"}
        d = _get(WIKIMON + "?" + urllib.parse.urlencode(q))
        for pg in d.get("query", {}).get("pages", {}).values():
            ii = pg.get("imageinfo")
            if ii:
                out[pg["title"]] = ii[0]
    return out


def _fonte(tam=13):
    from PIL import ImageFont
    for nome in ("arial.ttf", "segoeui.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(nome, tam)
        except OSError:
            pass
    return ImageFont.load_default()


def folha_de_contato(imagens, saida, lado=320, colunas=4):
    """Junta várias imagens (caminhos) numa folha só, com o nome embaixo de cada uma."""
    if not imagens:
        return None
    linhas = (len(imagens) + colunas - 1) // colunas
    folha = Image.new("RGB", (colunas * lado, linhas * (lado + 18)), (236, 238, 242))
    dr = ImageDraw.Draw(folha)
    for k, cam in enumerate(imagens):
        try:
            im = Image.open(cam)
            im.seek(0)
            im = im.convert("RGBA")
        except Exception:
            continue
        fundo = Image.new("RGBA", im.size, (236, 238, 242, 255))
        im = Image.alpha_composite(fundo, im).convert("RGB")
        im.thumbnail((lado - 8, lado - 8), Image.LANCZOS)
        x, y = (k % colunas) * lado, (k // colunas) * (lado + 18)
        folha.paste(im, (x + (lado - im.width) // 2, y + (lado - im.height) // 2))
        dr.text((x + 4, y + lado + 2), os.path.basename(cam)[:44], fill=(40, 40, 40), font=_fonte())
    folha.save(saida)
    return saida


# Nomes que a Wikimon escreve diferente (romanização japonesa / espaços)
APELIDOS = {"tsunomon": "Tunomon", "gotsumon": "Gottsumon", "tentomon": "Tentomon", "piyomon": "Piyomon",
            "biyomon": "Piyomon", "gomamon": "Gomamon", "palmon": "Palmon", "patamon": "Patamon",
            "kabuterimon": "Kabuterimon", "birdramon": "Birdramon", "greymon": "Greymon",
            "pagumon": "Pagumon", "tanemon": "Tanemon", "yokomon": "Pyocomon", "bukamon": "Pukamon",
            "motimon": "Mochimon", "pyocomon": "Pyocomon", "veemon": "V-mon", "dorumon": "Dorumon"}


def _variantes(nome):
    """Grafias possíveis na Wikimon: 'MetalGreymon' -> 'Metal Greymon', apelidos conhecidos."""
    v = [nome]
    if nome.lower() in APELIDOS:
        v.insert(0, APELIDOS[nome.lower()])
    espacado = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", nome)
    if espacado != nome:
        v.insert(0, espacado)
    vistos, saida = set(), []
    for x in v:
        if x not in vistos:
            vistos.add(x)
            saida.append(x)
    return saida


def digimon(nome, n=10, todos=False):
    pasta = os.path.join(BASE, "digimon", _seguro(nome).lower().replace("_", ""))
    os.makedirs(pasta, exist_ok=True)
    titulos = []
    for grafia in _variantes(nome):
        titulos = _arquivos_categoria(grafia)
        if titulos:
            if grafia != nome:
                print(f"  (na Wikimon: '{grafia}')")
            nome_wiki = grafia
            break
    else:
        nome_wiki = nome
    nome = nome_wiki
    pont = sorted(((_pontuar(t, nome), t) for t in titulos), reverse=True)
    escolhidos = [t for p, t in pont if p > -999 and (todos or p >= 0)][:n]
    if not escolhidos:
        print("Nada encontrado na Wikimon para", nome, "- confira a grafia (ex.: 'MetalGreymon').")
        return
    info = _urls(escolhidos)
    salvos = []
    for t in escolhidos:
        ii = info.get(t)
        if not ii:
            continue
        arq = os.path.join(pasta, _seguro(t.split(":", 1)[1]))
        if not os.path.exists(arq):
            try:
                with open(arq, "wb") as f:
                    f.write(_get(ii["url"], binario=True))
            except Exception as e:
                print("  falhou:", t, e)
                continue
        salvos.append(arq)
        print(f"  {os.path.basename(arq)}  ({ii.get('width')}x{ii.get('height')})")
    c = folha_de_contato(salvos, os.path.join(pasta, "_contato.png"))
    with open(os.path.join(pasta, "_fonte.txt"), "w", encoding="utf-8") as f:
        f.write("Imagens de https://wikimon.net (Category:Images_of_%s). Uso: referência pessoal.\n" % nome)
    print("Folha de contato:", c)
    print("Pasta:", pasta)


# ---------------------------------------------------------------------------------------- Cobblemon
def _arvore(caminho):
    itens, pagina = [], 1
    while True:
        q = urllib.parse.urlencode({"path": caminho, "per_page": 100, "page": pagina, "ref": "main"})
        d = _get(f"{GITLAB}/tree?{q}")
        itens += d
        if len(d) < 100:
            return itens
        pagina += 1


def _indice():
    cam = os.path.join(BASE, "cobblemon", "_indice.json")
    if os.path.exists(cam):
        with open(cam, encoding="utf-8") as f:
            return json.load(f)
    pastas = [x["name"] for x in _arvore(f"{RAIZ_COBBLE}/bedrock/pokemon/models") if x["type"] == "tree"]
    os.makedirs(os.path.dirname(cam), exist_ok=True)
    with open(cam, "w", encoding="utf-8") as f:
        json.dump(pastas, f)
    return pastas


def _bruto(caminho):
    return _get(f"{GITLAB}/files/{urllib.parse.quote(caminho, safe='')}/raw?ref=main", binario=True)


def estudo(geo_path, png_path):
    """Números que descrevem o estilo de um modelo pronto (para comparar com o nosso)."""
    import numpy as np
    with open(geo_path, encoding="utf-8") as f:
        g = json.load(f)
    geo = g["minecraft:geometry"][0]
    desc = geo["description"]
    ossos = geo.get("bones", [])
    cubos = [c for o in ossos for c in o.get("cubes", [])]
    rot = sum(1 for c in cubos if any(abs(v) > 1e-6 for v in c.get("rotation", [0, 0, 0])))
    infl = sum(1 for c in cubos if c.get("inflate"))
    ys = [c["origin"][1] + c["size"][1] for c in cubos] + [c["origin"][1] for c in cubos]
    xs = [c["origin"][0] for c in cubos] + [c["origin"][0] + c["size"][0] for c in cubos]
    zs = [c["origin"][2] for c in cubos] + [c["origin"][2] + c["size"][2] for c in cubos]
    tamanhos = sorted(max(c["size"]) for c in cubos)
    planos = sum(1 for c in cubos if min(c["size"]) == 0)
    im = np.array(Image.open(png_path).convert("RGBA"))
    opaco = im[..., 3] > 0
    cores = len({tuple(p) for p in im[opaco][:, :3]})
    tw, th = desc.get("texture_width"), desc.get("texture_height")
    # densidade: texels por unidade, estimada pelas faces do maior cubo com UV por face
    dens = "1 (box UV)" if any(isinstance(c.get("uv"), list) for c in cubos) else "UV por face"
    linhas = [
        f"modelo: {desc.get('identifier')}",
        f"textura: {tw}x{th}, {cores} cores, {opaco.mean() * 100:.0f}% ocupada; UV: {dens}",
        f"ossos: {len(ossos)}   cubos: {len(cubos)}   rotacionados: {rot}   inflate: {infl}   planos (espessura 0): {planos}",
        f"caixa: x {min(xs):.1f}..{max(xs):.1f}  y {min(ys):.1f}..{max(ys):.1f}  z {min(zs):.1f}..{max(zs):.1f}",
        f"tamanho do maior lado dos cubos: menor {tamanhos[0]}, mediana {tamanhos[len(tamanhos) // 2]}, maior {tamanhos[-1]}",
        "ossos: " + ", ".join(o["name"] for o in ossos),
    ]
    return "\n".join(linhas)


def cobblemon(nome, vistas=True):
    nome_l = nome.lower()
    pastas = _indice()
    alvo = [p for p in pastas if p.split("_", 1)[-1] == nome_l] or [p for p in pastas if nome_l in p]
    if not alvo:
        print("Não achei", nome, "no Cobblemon. Use: referencias.py lista-cobblemon", nome_l[:4])
        return None
    pasta_r = alvo[0]
    destino = os.path.join(BASE, "cobblemon", pasta_r)
    os.makedirs(destino, exist_ok=True)
    especie = pasta_r.split("_", 1)[-1]
    baixados = {}
    for sub, chave in ((f"bedrock/pokemon/models/{pasta_r}", "geo"),
                       (f"bedrock/pokemon/animations/{pasta_r}", "anim"),
                       (f"textures/pokemon/{pasta_r}", "tex")):
        try:
            itens = _arvore(f"{RAIZ_COBBLE}/{sub}")
        except Exception:
            itens = []
        for it in itens:
            if it["type"] != "blob":
                continue
            nm = it["name"]
            if chave == "tex" and nm != f"{especie}.png":
                continue      # só a textura principal (sem shiny/emissivo/quadros de chama)
            if chave == "geo" and not (nm.endswith(".geo.json") or nm == "license"):
                continue
            arq = os.path.join(destino, "LICENSE.txt" if nm == "license" else nm)
            if not os.path.exists(arq):
                with open(arq, "wb") as f:
                    f.write(_bruto(it["path"]))
            baixados.setdefault(chave, []).append(arq)
    geos = [g for g in baixados.get("geo", []) if g.endswith(".geo.json")]
    tex = baixados.get("tex", [])
    print("Baixado em", destino)
    for v in baixados.values():
        for a in v:
            print("  ", os.path.basename(a))
    if geos and tex:
        principal = min(geos, key=len)
        txt = estudo(principal, tex[0])
        with open(os.path.join(destino, "_estudo.txt"), "w", encoding="utf-8") as f:
            f.write(txt + "\n")
        print(txt)
        if vistas:
            from mcmodel import render
            from mcmodel.animacao import pose_em
            pose = None
            for an in baixados.get("anim", []):      # a pose de repouso do Cobblemon é em T; usa o idle
                try:
                    with open(an, encoding="utf-8") as f:
                        anims = json.load(f)["animations"]
                    chave = next((k for k in anims if k.endswith("ground_idle")), None) or \
                        next((k for k in anims if "idle" in k), None)
                    if chave:
                        pose = pose_em(anims[chave], 0.0)
                except Exception as e:
                    print("  (não consegui aplicar a pose idle:", e, ")")
            p = os.path.join(destino, "_vistas.png")
            render.folha(principal, tex[0], ["frente", "3/4", "esquerda", "tras", "3/4 tras"], extra=pose,
                         altura_alvo=360, titulo=f"Cobblemon: {especie} (estudo, CC BY-NC-SA)").save(p)
            p2 = os.path.join(destino, "_atlas.png")
            render.atlas(principal, tex[0]).save(p2)
            print("Vistas:", p)
            print("Atlas:", p2)
    return destino


def url(endereco, nome):
    pasta = os.path.join(BASE, "outras")
    os.makedirs(pasta, exist_ok=True)
    ext = os.path.splitext(urllib.parse.urlparse(endereco).path)[1] or ".png"
    arq = os.path.join(pasta, _seguro(nome) + ext)
    dados = _get(endereco, binario=True)
    Image.open(io.BytesIO(dados))      # garante que é imagem antes de salvar
    with open(arq, "wb") as f:
        f.write(dados)
    print(arq)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("digimon")
    a1.add_argument("nome")
    a1.add_argument("--n", type=int, default=10)
    a1.add_argument("--todos", action="store_true", help="inclui imagens de pontuação baixa")
    a2 = sub.add_parser("cobblemon")
    a2.add_argument("nome", nargs="+")
    a2.add_argument("--sem-vistas", action="store_true")
    a3 = sub.add_parser("url")
    a3.add_argument("endereco")
    a3.add_argument("nome")
    a4 = sub.add_parser("lista-cobblemon")
    a4.add_argument("filtro", nargs="?", default="")
    a = ap.parse_args()
    if a.cmd == "digimon":
        digimon(a.nome, a.n, a.todos)
    elif a.cmd == "cobblemon":
        for n in a.nome:
            cobblemon(n, not a.sem_vistas)
    elif a.cmd == "url":
        url(a.endereco, a.nome)
    else:
        print("\n".join(p for p in _indice() if a.filtro.lower() in p))


if __name__ == "__main__":
    main()
