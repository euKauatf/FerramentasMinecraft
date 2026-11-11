"""
Cores e "textura de pele" do Minecraft de verdade (mobs vanilla), para o modelo não parecer plástico.

    python vanilla.py extrair            acha o .jar do jogo do usuário (cache do Gradle do mod ou
                                         .minecraft/versions) e copia textures/entity para
                                         D:\\FerramentasMinecraft\\referencias\\minecraft (só leitura/estudo)
    python vanilla.py pool               junta os pixels de todos os mobs num arquivo de cores (_pool.npz)
    python vanilla.py rampa #FF8C24 [n]  rampa feita SÓ de cores que existem nos mobs do jogo, perto
                                         daquela cor (imprime a linha rampa_manual(...) pronta)
    python vanilla.py comparar X.png     mede saturação, brilho e granulado da textura contra a média
                                         dos mobs vanilla e diz o que ajustar

O que os mobs vanilla têm em comum (medido em fox, strider, piglin, hoglin, horse, camel, sniffer,
iron golem...): saturação mediana 0,5–0,8 (não 0,9), brilho mediano 0,5–0,8, 40–60% dos pixels
diferentes do vizinho (granulado de 2–3 tons próximos, nunca chapado), passos entre tons pequenos,
sombra mais escura embaixo e quase nenhuma "borda clara" desenhada.
"""
import glob
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

_RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
BASE = os.path.join(_RAIZ, "referencias", "minecraft")
ENT = os.path.join(BASE, "assets", "minecraft", "textures", "entity")
POOL = os.path.join(BASE, "_pool.npz")
# texturas que atrapalham a média (ruído artificial, efeitos, objetos)
IGNORAR = ("creeper", "end_portal", "beacon", "enchant", "experience", "banner", "shield", "chest", "bed",
           "sign", "decorated_pot", "equipment", "player", "conduit", "end_crystal", "fishing", "projectiles",
           "trident", "minecart", "boat", "lead_knot", "bell", "armorstand", "cushion")


def achar_jar():
    candidatos = []
    for raiz in (r"D:\DigimonMod\.tmp\gradle-home", os.path.expanduser(r"~\.gradle")):
        candidatos += glob.glob(os.path.join(raiz, "caches", "**", "*minecraft*client*.jar"), recursive=True)
    candidatos += glob.glob(os.path.join(os.environ.get("APPDATA", ""), ".minecraft", "versions", "*", "*.jar"))
    candidatos = [c for c in candidatos if os.path.getsize(c) > 5_000_000]
    return sorted(candidatos, key=os.path.getmtime, reverse=True)


def extrair():
    jars = achar_jar()
    if not jars:
        raise SystemExit("não achei o .jar do Minecraft (rode o jogo ou compile o mod uma vez)")
    n = 0
    with zipfile.ZipFile(jars[0]) as z:
        for f in z.namelist():
            if f.startswith("assets/minecraft/textures/entity/") and f.endswith(".png"):
                z.extract(f, BASE)
                n += 1
    print(f"{n} texturas de {jars[0]} -> {ENT}")


def _oklab(rgb):
    from mcmodel.cores import para_oklch  # noqa: F401
    import mcmodel.cores as c
    return np.array([c.para_oklch(tuple(int(v) for v in p)) for p in rgb])


def pool():
    if not os.path.isdir(ENT):
        extrair()
    pix = []
    for f in glob.glob(os.path.join(ENT, "**", "*.png"), recursive=True):
        if any(k in f.replace("\\", "/").lower() for k in IGNORAR):
            continue
        a = np.array(Image.open(f).convert("RGBA"))
        px = a[a[..., 3] == 255][:, :3]
        if len(px):
            pix.append(px)
    pix = np.concatenate(pix)
    cores, contagem = np.unique(pix, axis=0, return_counts=True)
    lch = _oklab(cores)
    np.savez_compressed(POOL, rgb=cores, n=contagem, lch=lch)
    print(f"{len(cores)} cores únicas ({contagem.sum()} pixels) -> {POOL}")


def carregar_pool():
    if not os.path.exists(POOL):
        pool()
    d = np.load(POOL)
    return d["rgb"], d["n"], d["lch"]


def _lab(lch):
    L, C, H = lch[..., 0], lch[..., 1], np.radians(lch[..., 2])
    return np.stack([L, C * np.cos(H), C * np.sin(H)], -1)


def rampa_vanilla(cor, n=6, base=None, croma=0.88, desvio=0.6, contraste=0.85, trava_matiz=7):
    """
    Rampa no jeito dos mobs do jogo: parte da cor pedida, tira um pouco de saturação (os mobs
    vanilla são mais "terrosos"), passos de tom menores, e encaixa cada tom na cor REAL mais próxima
    que aparece nas texturas do Minecraft (quando existe uma bem perto; senão fica a calculada).
    Devolve (Rampa, lista_hex, base).
    """
    from mcmodel.cores import Rampa, para_oklch, de_oklch, rgba, rampa
    rgb, cont, lch = carregar_pool()
    lab_pool = _lab(lch)
    L0, C0, H0 = para_oklch(rgba(cor)[:3])
    alvo = de_oklch(L0, C0 * croma, H0)
    b = n // 2 if base is None else base
    calc = rampa(alvo, n=n, base=b, desvio=desvio, contraste=contraste)
    saida = []
    for c in calc:
        l = np.array(para_oklch(tuple(c[:3])))
        d = np.linalg.norm(lab_pool - _lab(l[None])[0], axis=1)
        if l[1] > 0.03:                                        # cor com matiz: não deixa o laranja virar rosa
            dh = np.abs((lch[:, 2] - l[2] + 180) % 360 - 180)
            d = np.where(dh <= trava_matiz, d, 9.0)
        i = int(np.argmin(d - 0.003 * np.log1p(cont)))        # perto e comum ganha
        escolhido = rgb[i] if d[i] < 0.04 else np.array(c[:3])
        saida.append("#%02X%02X%02X" % tuple(int(v) for v in escolhido))
    # mantém ordem escura -> clara e sem repetição
    unicos = []
    for c in saida:
        if c not in unicos:
            unicos.append(c)
    unicos.sort(key=lambda h: para_oklch(rgba(h)[:3])[0])
    Lr = [para_oklch(rgba(h)[:3])[0] for h in unicos]
    Lb = para_oklch(tuple(calc[b][:3]))[0]
    base_final = int(np.argmin([abs(v - Lb) for v in Lr]))
    return Rampa([rgba(h) for h in unicos], base_final), unicos, base_final


def medir(caminho):
    import colorsys
    a = np.array(Image.open(caminho).convert("RGBA")).astype(float)
    m = a[..., 3] > 0
    px = a[m][:, :3] / 255
    amostra = px[:: max(1, len(px) // 5000)]
    hsv = np.array([colorsys.rgb_to_hsv(*c) for c in amostra])
    rgb = a[..., :3]
    dh = np.abs(np.diff(rgb, axis=1)).sum(-1)[m[:, 1:] & m[:, :-1]]
    dv = np.abs(np.diff(rgb, axis=0)).sum(-1)[m[1:] & m[:-1]]
    viz = np.concatenate([dh, dv])
    sat_ok = hsv[:, 1] > 0.25
    matiz = float(np.median(hsv[sat_ok, 0]) * 360) if sat_ok.any() else -1
    return {"matiz": matiz, "sat": float(np.median(hsv[:, 1])), "val": float(np.median(hsv[:, 2])),
            "granulado": float((viz > 0).mean()), "salto": float(np.median(viz[viz > 0])) if (viz > 0).any() else 0}


def comparar(caminho):
    todos = []
    for f in glob.glob(os.path.join(ENT, "**", "*.png"), recursive=True):
        if any(k in f.replace("\\", "/").lower() for k in IGNORAR) or "baby" in f:
            continue
        try:
            todos.append((os.path.basename(f), medir(f)))
        except Exception:
            pass
    alvo = medir(caminho)
    # compara com mobs da MESMA cor dominante (um bicho laranja com a raposa, não com o lobo cinza)
    parecidos = [(n, r) for n, r in todos if r["matiz"] >= 0 and alvo["matiz"] >= 0 and r["sat"] > 0.3
                 and abs((r["matiz"] - alvo["matiz"] + 180) % 360 - 180) < 25]
    ref = [r for _, r in (parecidos if len(parecidos) >= 3 else todos)]
    print("comparando com:", ", ".join(n for n, _ in (parecidos if len(parecidos) >= 3 else todos)[:10]))
    med = {k: float(np.median([r[k] for r in ref])) for k in alvo}
    print(f"{'':12s}{'sua textura':>12s}{'mobs vanilla':>14s}")
    for k, nome in (("matiz", "matiz"), ("sat", "saturação"), ("val", "brilho"), ("granulado", "granulado"),
                    ("salto", "salto de tom")):
        print(f"{nome:12s}{alvo[k]:12.2f}{med[k]:14.2f}")
    dicas = []
    if alvo["sat"] > med["sat"] + 0.12:
        dicas.append("saturada demais: use rampa_vanilla() ou tire saturação das cores base")
    if alvo["val"] > med["val"] + 0.12:
        dicas.append("clara demais: desça a base da rampa um tom")
    if alvo["granulado"] < med["granulado"] - 0.15:
        dicas.append("lisa demais (cara de plástico): use estilo=\"vanilla\" (granulado de 2-3 tons próximos)")
    if alvo["granulado"] > med["granulado"] + 0.2:
        dicas.append("ruidosa demais: baixe `ruido`")
    print("\n".join("-> " + d for d in dicas) or "-> parecida com o jogo")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "extrair":
        extrair()
    elif cmd == "pool":
        pool()
    elif cmd == "rampa":
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 6
        _, cores, base = rampa_vanilla(sys.argv[2], n)
        print(f'rampa_manual({", ".join(repr(c).replace(chr(39), chr(34)) for c in cores)}, base={base})')
    elif cmd == "comparar":
        comparar(sys.argv[2])
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
