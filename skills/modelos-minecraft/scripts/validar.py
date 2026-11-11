"""
Valida um modelo GeckoLib/Bedrock (.geo.json + .png [+ .animation.json]) e mede a qualidade da textura.

    python validar.py modelo.geo.json textura.png [arq.animation.json]

ERRO  = vai quebrar ou ficar visivelmente errado no jogo.
AVISO = funciona, mas provavelmente não é o que você quer.
NOTA  = métricas de arte, para decidir se precisa de mais um passe de pintura.
Sai com código 1 se houver ERRO.
"""
import json
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from mcmodel import geometria as g  # noqa: E402


def validar(caminho_geo, caminho_png, caminho_anim=None):
    erros, avisos, notas = [], [], []
    with open(caminho_geo, encoding="utf-8") as f:
        dados = json.load(f)
    if "minecraft:geometry" not in dados:
        return ["não é um .geo.json Bedrock (falta 'minecraft:geometry')"], [], []
    geo = dados["minecraft:geometry"][0]
    desc = geo.get("description", {})
    if not desc.get("identifier", "").startswith("geometry."):
        avisos.append("identifier deveria começar com 'geometry.'")
    img = Image.open(caminho_png).convert("RGBA")
    tex = np.array(img)
    tw, th = desc.get("texture_width"), desc.get("texture_height")
    if (tw, th) != img.size:
        if tw and th and img.size[0] / tw == img.size[1] / th:
            notas.append(f"textura {img.size} é múltiplo de {tw}x{th} (ok para GeckoLib)")
        else:
            erros.append(f"texture_width/height {tw}x{th} não bate com a imagem {img.size}")

    ossos = geo.get("bones", [])
    nomes = [o["name"] for o in ossos]
    for n, c in Counter(nomes).items():
        if c > 1:
            erros.append(f"osso '{n}' repetido")
    for o in ossos:
        if o.get("parent") and o["parent"] not in nomes:
            erros.append(f"osso '{o['name']}' tem pai inexistente '{o['parent']}'")
    # ciclos
    pais = {o["name"]: o.get("parent") for o in ossos}
    for n in nomes:
        vistos, a = set(), n
        while a:
            if a in vistos:
                erros.append(f"ciclo na hierarquia de ossos passando por '{n}'")
                break
            vistos.add(a)
            a = pais.get(a)

    ocupado = np.full((img.size[1], img.size[0]), -1, dtype=int)
    regioes = []
    dens = []
    for o in ossos:
        for k, c in enumerate(o.get("cubes", [])):
            rot = f"{o['name']}[{k}]"
            if any(v <= 0 for v in c["size"]) and sum(v == 0 for v in c["size"]) == 0:
                erros.append(f"{rot}: tamanho negativo {c['size']}")
            uvs = c.get("uv")
            if not isinstance(uvs, dict):
                notas.append(f"{rot}: usa box UV (formato antigo)")
                continue
            for f, r in uvs.items():
                if f not in g.FACES:
                    erros.append(f"{rot}: face desconhecida '{f}'")
                    continue
                (u, v), (su, sv) = r["uv"], r["uv_size"]
                x0, x1 = sorted((u, u + su))
                y0, y1 = sorted((v, v + sv))
                fw, fh = g.dimensoes_face(f, c["size"])
                if x0 < 0 or y0 < 0 or x1 > (tw or img.size[0]) or y1 > (th or img.size[1]):
                    erros.append(f"{rot}:{f} UV fora da textura ({x0},{y0})-({x1},{y1})")
                    continue
                if fw > 0 and fh > 0:
                    dens.append((abs(su) / fw, abs(sv) / fh, rot, f))
                esc = img.size[0] / (tw or img.size[0])
                ix0, iy0, ix1, iy1 = int(x0 * esc), int(y0 * esc), int(np.ceil(x1 * esc)), int(np.ceil(y1 * esc))
                regioes.append((rot, f, ix0, iy0, ix1, iy1))
                bloco = ocupado[iy0:iy1, ix0:ix1]
                if (bloco >= 0).any():
                    outro = regioes[bloco[bloco >= 0][0]]
                    avisos.append(f"{rot}:{f} divide UV com {outro[0]}:{outro[1]} (só ok se for de propósito, ex.: lados iguais)")
                ocupado[iy0:iy1, ix0:ix1] = len(regioes) - 1
                area = tex[iy0:iy1, ix0:ix1]
                if area.size and (area[..., 3] < 26).all():
                    avisos.append(f"{rot}:{f} é totalmente transparente (face invisível)")

    if dens:
        dx = Counter(round(d[0], 3) for d in dens) + Counter(round(d[1], 3) for d in dens)
        principal = dx.most_common(1)[0][0]
        fora = [d for d in dens if abs(d[0] - principal) > 0.01 or abs(d[1] - principal) > 0.01]
        notas.append(f"densidade principal: {principal:g} texel(s) por unidade")
        if fora:
            exemplos = ", ".join(f"{r}:{f} ({a:.2f}x{b:.2f})" for a, b, r, f in fora[:6])
            avisos.append(f"{len(fora)} faces com densidade diferente (pixels maiores/esticados): {exemplos}")

    # ------------------------------------------------------------ arte
    usados = tex[ocupado >= 0]
    opacos = usados[usados[..., 3] >= 26]
    meio_transp = ((usados[..., 3] > 0) & (usados[..., 3] < 255)).sum()
    if meio_transp:
        avisos.append(f"{meio_transp} texels semi-transparentes (em entity_cutout viram 0% ou 100%)")
    if len(opacos):
        cores = Counter(map(tuple, opacos[:, :3]))
        notas.append(f"{len(cores)} cores diferentes na textura")
        if len(cores) > 64:
            notas.append("muitas cores: pixel art costuma ficar mais limpa com menos (paletas por material)")
    orfaos, total = 0, 0
    for _, _, x0, y0, x1, y1 in regioes:
        a = tex[y0:y1, x0:x1, :3].astype(int)
        if a.shape[0] < 3 or a.shape[1] < 3:
            continue
        c = a[1:-1, 1:-1]
        viz = [a[:-2, 1:-1], a[2:, 1:-1], a[1:-1, :-2], a[1:-1, 2:]]
        dif = np.all([np.any(c != v, axis=-1) for v in viz], axis=0)
        orfaos += int(dif.sum())
        total += dif.size
    if total:
        pct = 100 * orfaos / total
        notas.append(f"pixels isolados (diferentes dos 4 vizinhos): {pct:.1f}%"
                     + ("  <- ruidoso; reduza 'ruido' ou 'pontilhado'" if pct > 12 else ""))

    # ---------------------------------------------------------- limites
    pose = g.Pose(ossos)
    caixas = []
    pts = []
    for o in ossos:
        for c in o.get("cubes", []):
            x0, y0, z0 = c["origin"]
            W, H, D = c["size"]
            cantos = np.array([[x, y, z] for x in (x0, x0 + W) for y in (y0, y0 + H) for z in (z0, z0 + D)])
            pp = pose.transformar(o["name"], g.girar_no_cubo(c, cantos))
            pts.append(pp)
            caixas.append((o["name"], pp.min(0), pp.max(0), min(c["size"]) == 0))
    # peças soltas: cubo que não encosta em nenhum outro (fica flutuando ou com fresta)
    soltos = []
    for i, (nome_i, mn_i, mx_i, plano_i) in enumerate(caixas):
        toca = False
        for j, (_, mn_j, mx_j, _) in enumerate(caixas):
            if i != j and np.all(mn_i <= mx_j + 0.3) and np.all(mn_j <= mx_i + 0.3):
                toca = True
                break
        if not toca:
            soltos.append(f"{nome_i}[{i}]")
    if soltos:
        avisos.append(f"{len(soltos)} peça(s) solta(s), sem encostar em nada: {', '.join(soltos[:8])}")
    solidos = sum(1 for cx in caixas if not cx[3])
    planos = len(caixas) - solidos
    notas.append(f"peças: {solidos} cubos + {planos} planos")
    if solidos > 60:
        avisos.append(f"{solidos} cubos sólidos: complexo demais para um mob (Cobblemon usa 30-60). "
                      "Junte peças, use menos cubos arredondados girados e corte detalhes que não aparecem.")
    if pts:
        pts = np.concatenate(pts)
        mn, mx = pts.min(0), pts.max(0)
        notas.append(f"tamanho: {mx[0]-mn[0]:.1f} x {mx[1]-mn[1]:.1f} x {mx[2]-mn[2]:.1f} unidades "
                     f"({(mx[0]-mn[0])/16:.2f} x {(mx[1]-mn[1])/16:.2f} x {(mx[2]-mn[2])/16:.2f} blocos)")
        if mn[1] < -0.01:
            avisos.append(f"parte do modelo abaixo do chão (y mínimo = {mn[1]:.2f}); os pés devem ficar em y=0")
        vw, vh = desc.get("visible_bounds_width"), desc.get("visible_bounds_height")
        if vw and vh and (max(abs(mn[0]), abs(mx[0]), abs(mn[2]), abs(mx[2])) > vw * 8 or mx[1] > (vh + desc.get("visible_bounds_offset", [0, 0, 0])[1]) * 16):
            avisos.append("modelo maior que visible_bounds (no Bedrock some antes de sair da tela)")

    # ---------------------------------------------------------- faces que piscam (z-fighting)
    try:
        from mcmodel import render as _r
        fs = _r._faces_do_modelo(geo)
        planos = {}
        for P0, P1, P3, n, _uv, _sz in fs:
            n = np.asarray(n, float)
            ax = int(np.argmax(np.abs(n)))
            if abs(n[ax]) < 0.9999:
                continue
            cs = np.array([P0, P1, P1 + P3 - P0, P3])
            chave = (ax, int(np.sign(n[ax])), round(float(cs[:, ax].mean()) * 20))
            planos.setdefault(chave, []).append(cs)
        brigas = 0
        for lst in planos.values():
            for i in range(len(lst)):
                for j in range(i + 1, len(lst)):
                    ax = next(iter(k for k in planos if planos[k] is lst))[0]
                    if abs(lst[i][:, ax].mean() - lst[j][:, ax].mean()) > 0.01:
                        continue        # planos separados (ex.: cubo inflado de propósito)
                    if g.sobreposicao_faces(lst[i], lst[j], ax)[0] > 1e-3:
                        brigas += 1
        if brigas:
            avisos.append(f"{brigas} par(es) de faces no mesmo plano uma sobre a outra: vão PISCAR no jogo "
                          "(z-fighting). Afaste/esconda uma delas.")
    except Exception as e:  # noqa: BLE001
        notas.append(f"não consegui checar faces que piscam: {e}")

    # ---------------------------------------------------------- animações
    if caminho_anim:
        with open(caminho_anim, encoding="utf-8") as f:
            an = json.load(f).get("animations", {})
        for nome, a in an.items():
            for osso in a.get("bones", {}):
                if osso not in nomes:
                    erros.append(f"animação {nome} mexe no osso '{osso}', que não existe")
            if not a.get("animation_length"):
                avisos.append(f"animação {nome} sem animation_length")
        curtos = {n.split(".")[-1] for n in an}
        faltam = {"idle", "walk"} - curtos
        if faltam:
            notas.append(f"animações sem: {', '.join(sorted(faltam))} (o código do mod pode esperar esses nomes)")
    return erros, avisos, notas


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    erros, avisos, notas = validar(*sys.argv[1:4])
    for e in erros:
        print("ERRO :", e)
    for a in avisos:
        print("AVISO:", a)
    for n in notas:
        print("NOTA :", n)
    if not erros and not avisos:
        print("OK: nenhum problema estrutural encontrado")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
