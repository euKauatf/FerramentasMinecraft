"""
Cores: conversão, rampas de sombreamento com desvio de matiz (hue shift) e utilidades.

Uma "rampa" é uma lista de cores do mais escuro para o mais claro. Pixel art boa usa poucas
cores por material (4 a 7) e, em vez de só escurecer/clarear, gira a matiz: sombras puxam para
azul/roxo e luzes para amarelo. Tudo aqui é feito no espaço OKLab/OKLCh, que é perceptual
(passos de luminosidade iguais parecem iguais ao olho).
"""
import math

# ----------------------------------------------------------------- conversões


def rgba(cor):
    """Aceita '#RRGGBB', '#RRGGBBAA', (r,g,b) ou (r,g,b,a). Devolve (r,g,b,a) inteiros."""
    if isinstance(cor, str):
        h = cor.lstrip("#")
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        vals = [int(h[i:i + 2], 16) for i in range(0, len(h), 2)]
        return tuple(vals[:3]) + ((vals[3],) if len(vals) > 3 else (255,))
    cor = tuple(int(round(c)) for c in cor)
    return cor[:3] + ((cor[3],) if len(cor) > 3 else (255,))


def hexa(cor):
    r, g, b, a = rgba(cor)
    return f"#{r:02X}{g:02X}{b:02X}" + (f"{a:02X}" if a != 255 else "")


def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _srgb(c):
    c = 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return max(0, min(255, round(c * 255)))


def para_oklab(cor):
    r, g, b, _ = rgba(cor)
    r, g, b = _lin(r), _lin(g), _lin(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def de_oklab(L, a, b, alfa=255):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return (_srgb(r), _srgb(g), _srgb(bb), alfa)


def para_oklch(cor):
    L, a, b = para_oklab(cor)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def de_oklch(L, C, H, alfa=255):
    # reduz o croma até caber no sRGB (evita cores "estouradas")
    for _ in range(30):
        a, b = C * math.cos(math.radians(H)), C * math.sin(math.radians(H))
        lab = de_oklab(L, a, b, alfa)
        r2 = para_oklab(lab)
        if abs(r2[0] - L) < 0.02 or C < 0.005:
            return lab
        C *= 0.9
    return de_oklab(L, 0, 0, alfa)


def luminancia(cor):
    return para_oklab(cor)[0]


def misturar(c1, c2, t):
    """Mistura perceptual (em OKLab). t=0 -> c1, t=1 -> c2."""
    a, b = para_oklab(c1), para_oklab(c2)
    return de_oklab(*(x + (y - x) * t for x, y in zip(a, b)), rgba(c1)[3])


def tom(cor, passos):
    """Clareia (passos>0) ou escurece (passos<0) uma cor seguindo a mesma lógica das rampas."""
    return rampa(cor, n=9, base=4)[max(0, min(8, 4 + int(round(passos))))]


# ---------------------------------------------------------------------- rampas

_MATIZ_SOMBRA = 285.0   # azul-violeta
_MATIZ_LUZ = 85.0       # amarelo quente


def _girar(h, alvo, f):
    d = (alvo - h + 540) % 360 - 180
    return (h + d * f) % 360


class Rampa(list):
    """Lista de cores (escura -> clara) que lembra qual índice é a cor original (`base`)."""

    def __init__(self, cores, base=None):
        super().__init__(cores)
        self.base = len(self) // 2 if base is None else base


def rampa(cor, n=6, base=None, contraste=1.0, desvio=1.0, saturar_sombras=1.0,
          luz_max=None, sombra_min=None):
    """
    Gera uma rampa de n cores (escura -> clara) ao redor da cor base.

    base: posição (índice) da cor original na rampa (padrão: o meio).
    contraste: 1.0 = passos padrão; >1 mais dramático, <1 mais suave (materiais foscos).
    desvio: intensidade do hue shift (0 = sem giro de matiz; 1 = padrão; 1.5 = estilizado).
    saturar_sombras: >1 deixa as sombras mais saturadas (bom para pele/pelo quente).
    """
    base_idx = n // 2 if base is None else base
    L0, C0, H0 = para_oklch(cor)
    passo = 0.062 * contraste
    neutra = C0 < 0.025
    cores = []
    for k in range(n):
        d = k - base_idx
        L = L0 + d * passo * (1.0 if d > 0 else 1.15)
        if luz_max is not None:
            L = min(L, luz_max)
        if sombra_min is not None:
            L = max(L, sombra_min)
        L = max(0.1, min(0.97, L))
        if neutra:
            # cinzas e brancos: sombra levemente azulada, luz levemente quente (fica "vivo", não chapado)
            H = _MATIZ_SOMBRA if d < 0 else _MATIZ_LUZ
            C = C0 + 0.005 * abs(d) * desvio
        elif d < 0:
            H = _girar(H0, _MATIZ_SOMBRA, min(0.45, 0.06 * -d * desvio))
            C = C0 * (1 + 0.05 * -d * (saturar_sombras - 0.2))
            C *= max(0.55, 1 - 0.05 * -d)
        elif d > 0:
            # cores escuras (couro, pelo preto) giram pouco nas luzes, senão viram verde-oliva
            H = _girar(H0, _MATIZ_LUZ, min(0.4, 0.06 * d * desvio) * min(1.0, L0 / 0.55) ** 2)
            C = C0 * max(0.35, 1 - 0.12 * d)
        else:
            H, C = H0, C0
        cores.append(de_oklch(L, C, H) if k != base_idx else rgba(cor))
    return Rampa(cores, base_idx)


def rampa_manual(*cores, base=None):
    """
    Rampa escrita à mão (escura -> clara), ex. com as cores que paleta.py tirou da referência:
        rampa_manual("#945D1C", "#B87621", "#D78827", "#EE9B2E", "#FCAE36", "#FFD04F", base=4)
    base: índice da cor "normal" do material (padrão: o meio).
    """
    return Rampa([rgba(c) for c in cores], base)


def amostra_rampas(rampas, tamanho=24):
    """Imagem com as rampas lado a lado (para conferir a paleta)."""
    from PIL import Image, ImageDraw
    nomes = list(rampas)
    largura = max(len(r) for r in rampas.values()) * tamanho + 140
    img = Image.new("RGBA", (largura, len(nomes) * tamanho), (40, 40, 44, 255))
    d = ImageDraw.Draw(img)
    for y, nome in enumerate(nomes):
        d.text((4, y * tamanho + 6), nome[:18], fill=(230, 230, 230, 255))
        for x, c in enumerate(rampas[nome]):
            d.rectangle([140 + x * tamanho, y * tamanho, 140 + (x + 1) * tamanho - 1, (y + 1) * tamanho - 1], fill=rgba(c))
    return img
