"""
Animações no formato Bedrock/GeckoLib (.animation.json, format_version 1.8.0) e um avaliador
simples para as prévias (subconjunto de Molang: math.sin/cos/abs/clamp/lerp, query.anim_time).

Valores de canal aceitos:
  [x, y, z]                         constante (números ou expressões Molang em texto)
  {"0.0": [..], "0.5": [..]}        quadros-chave (interpolação linear)
  {"0.0": {"post": [..], "lerp_mode": "catmullrom"}, ...}   quadros suaves

Convenções (graus, conferidas no Blockbench): rotation X positivo abaixa o que aponta para a
frente (cabeça olha para o chão), levanta o que aponta para trás (cauda sobe) e joga para TRÁS o
que está pendurado (perna, braço). Y positivo vira o focinho para a DIREITA da criatura
(-X). Z positivo gira no sentido horário visto de frente (braço esquerdo +X desce, direito sobe).
"""
import math
import re


def onda(amplitude, periodo, fase=0.0, eixo=0, base=(0, 0, 0), deslocamento=0.0):
    """Oscilação senoidal num eixo: base + deslocamento + sin(t/periodo*360 + fase) * amplitude."""
    vals = [str(v) for v in base]
    vals[eixo] = (f"{base[eixo] + deslocamento} + math.sin(query.anim_time / {periodo} * 360 + {fase}) * {amplitude}")
    return vals


def chaves(quadros, suave=False):
    """quadros: {tempo: [x, y, z]} -> dicionário de quadros-chave do Bedrock."""
    saida = {}
    for t in sorted(quadros):
        v = [float(x) if not isinstance(x, str) else x for x in quadros[t]]
        saida[f"{float(t):.4g}" if "." in f"{float(t):.4g}" else f"{float(t):.1f}"] = (
            {"post": v, "lerp_mode": "catmullrom"} if suave else v)
    return saida


# --------------------------------------------------------- receitas prontas

def bipede(nomes=None, peso=1.0, passo=0.9, balanco=1.0):
    """
    Parado / andando / atacando para bípedes. nomes: troca nomes de ossos padrão, ex.
    {"body": "torso"}. Ossos padrão: body, head, arm_left, arm_right, leg_left, leg_right, tail.
    peso > 1 deixa tudo mais lento e pesado.
    """
    n = {"body": "body", "head": "head", "arm_left": "arm_left", "arm_right": "arm_right",
         "leg_left": "leg_left", "leg_right": "leg_right", "tail": "tail"}
    n.update(nomes or {})
    a = 30 * balanco / peso ** 0.5
    p = passo * peso
    return {
        "idle": {"loop": True, "animation_length": 2.4 * peso, "bones": {
            n["body"]: {"position": onda(0.25, 2.4 * peso, eixo=1)},
            n["head"]: {"rotation": onda(2.5, 2.4 * peso, fase=90)},
            n["arm_left"]: {"rotation": onda(3, 2.4 * peso, eixo=2, deslocamento=-2)},
            n["arm_right"]: {"rotation": onda(3, 2.4 * peso, eixo=2, fase=180, deslocamento=2)},
            n["tail"]: {"rotation": onda(8, 2.4 * peso, eixo=1)},
        }},
        "walk": {"loop": True, "animation_length": p, "bones": {
            n["body"]: {"position": [0, f"math.abs(math.sin(query.anim_time / {p} * 360)) * 0.6", 0],
                        "rotation": onda(3, p, eixo=1)},
            n["head"]: {"rotation": onda(3, p / 2, fase=180)},
            n["leg_left"]: {"rotation": onda(a, p)},
            n["leg_right"]: {"rotation": onda(a, p, fase=180)},
            n["arm_left"]: {"rotation": onda(a * 0.8, p, fase=180)},
            n["arm_right"]: {"rotation": onda(a * 0.8, p)},
            n["tail"]: {"rotation": onda(12, p, eixo=1, fase=90)},
        }},
        "attack": {"loop": False, "animation_length": 0.5 * peso, "bones": {
            n["body"]: {"rotation": chaves({0: [0, 0, 0], 0.15 * peso: [0, -15, 0], 0.3 * peso: [8, 20, 0], 0.5 * peso: [0, 0, 0]}, True)},
            n["arm_right"]: {"rotation": chaves({0: [0, 0, 0], 0.15 * peso: [-110, 0, 10], 0.3 * peso: [-20, 0, 0], 0.5 * peso: [0, 0, 0]}, True)},
            n["head"]: {"rotation": chaves({0: [0, 0, 0], 0.2 * peso: [-10, 0, 0], 0.5 * peso: [0, 0, 0]}, True)},
        }},
    }


def quadrupede(nomes=None, peso=1.0, passo=0.8):
    """Ossos padrão: body, head, leg_front_left, leg_front_right, leg_back_left, leg_back_right, tail."""
    n = {"body": "body", "head": "head", "leg_front_left": "leg_front_left", "leg_front_right": "leg_front_right",
         "leg_back_left": "leg_back_left", "leg_back_right": "leg_back_right", "tail": "tail"}
    n.update(nomes or {})
    a = 28 / peso ** 0.5
    p = passo * peso
    return {
        "idle": {"loop": True, "animation_length": 2.6 * peso, "bones": {
            n["body"]: {"position": onda(0.2, 2.6 * peso, eixo=1)},
            n["head"]: {"rotation": onda(3, 2.6 * peso, fase=60)},
            n["tail"]: {"rotation": onda(10, 1.3 * peso, eixo=1)},
        }},
        "walk": {"loop": True, "animation_length": p, "bones": {
            n["body"]: {"position": [0, f"math.abs(math.sin(query.anim_time / {p} * 360)) * 0.4", 0]},
            n["head"]: {"rotation": onda(4, p / 2)},
            n["leg_front_left"]: {"rotation": onda(a, p)},
            n["leg_back_right"]: {"rotation": onda(a, p)},
            n["leg_front_right"]: {"rotation": onda(a, p, fase=180)},
            n["leg_back_left"]: {"rotation": onda(a, p, fase=180)},
            n["tail"]: {"rotation": onda(14, p, eixo=1)},
        }},
        "attack": {"loop": False, "animation_length": 0.5 * peso, "bones": {
            n["body"]: {"rotation": chaves({0: [0, 0, 0], 0.15 * peso: [-12, 0, 0], 0.3 * peso: [10, 0, 0], 0.5 * peso: [0, 0, 0]}, True)},
            n["head"]: {"rotation": chaves({0: [0, 0, 0], 0.15 * peso: [-25, 0, 0], 0.3 * peso: [20, 0, 0], 0.5 * peso: [0, 0, 0]}, True)},
            n["leg_front_left"]: {"rotation": chaves({0: [0, 0, 0], 0.15 * peso: [-40, 0, 0], 0.4 * peso: [0, 0, 0]}, True)},
            n["leg_front_right"]: {"rotation": chaves({0: [0, 0, 0], 0.15 * peso: [-40, 0, 0], 0.4 * peso: [0, 0, 0]}, True)},
        }},
    }


def voador(nomes=None, batida=0.6):
    """Ossos padrão: body, head, wing_left, wing_right, tail. Asas batem no eixo Z."""
    n = {"body": "body", "head": "head", "wing_left": "wing_left", "wing_right": "wing_right", "tail": "tail"}
    n.update(nomes or {})
    return {
        "idle": {"loop": True, "animation_length": batida * 2, "bones": {
            n["body"]: {"position": onda(1.0, batida * 2, eixo=1)},
            n["wing_left"]: {"rotation": onda(25, batida * 2, eixo=2, deslocamento=-10)},
            n["wing_right"]: {"rotation": onda(25, batida * 2, eixo=2, fase=180, deslocamento=10)},
            n["tail"]: {"rotation": onda(6, batida * 2)},
        }},
        "walk": {"loop": True, "animation_length": batida, "bones": {
            n["body"]: {"position": onda(1.5, batida, eixo=1, fase=90), "rotation": [10, 0, 0]},
            n["wing_left"]: {"rotation": onda(45, batida, eixo=2, deslocamento=-5)},
            n["wing_right"]: {"rotation": onda(45, batida, eixo=2, fase=180, deslocamento=5)},
            n["head"]: {"rotation": [-10, 0, 0]},
        }},
        "attack": {"loop": False, "animation_length": 0.5, "bones": {
            n["body"]: {"rotation": chaves({0: [0, 0, 0], 0.15: [-20, 0, 0], 0.3: [25, 0, 0], 0.5: [0, 0, 0]}, True)},
            n["head"]: {"rotation": chaves({0: [0, 0, 0], 0.2: [20, 0, 0], 0.5: [0, 0, 0]}, True)},
        }},
    }


def bolinha(nomes=None):
    """Criaturas redondas que pulam (slimes, bebês). Ossos: body (e opcional eyes/ears)."""
    n = {"body": "body"}
    n.update(nomes or {})
    return {
        "idle": {"loop": True, "animation_length": 1.6, "bones": {
            n["body"]: {"scale": ["1 + math.sin(query.anim_time / 1.6 * 360) * 0.04",
                                  "1 - math.sin(query.anim_time / 1.6 * 360) * 0.05",
                                  "1 + math.sin(query.anim_time / 1.6 * 360) * 0.04"]},
        }},
        "walk": {"loop": True, "animation_length": 0.6, "bones": {
            n["body"]: {"position": [0, "math.abs(math.sin(query.anim_time / 0.6 * 180)) * 3", 0],
                        "scale": ["1", "1 + math.sin(query.anim_time / 0.6 * 360) * 0.08", "1"]},
        }},
        "attack": {"loop": False, "animation_length": 0.4, "bones": {
            n["body"]: {"scale": chaves({0: [1, 1, 1], 0.12: [1.2, 0.8, 1.2], 0.25: [0.9, 1.15, 0.9], 0.4: [1, 1, 1]}),
                        "position": chaves({0: [0, 0, 0], 0.12: [0, 0, -2], 0.25: [0, 2, -3], 0.4: [0, 0, 0]})},
        }},
    }


# ----------------------------------------------------------------- avaliador

_MOLANG = [
    (r"math\.sin\(", "_sin("), (r"math\.cos\(", "_cos("), (r"math\.abs\(", "abs("),
    (r"math\.clamp\(", "_clamp("), (r"math\.lerp\(", "_lerp("), (r"math\.pi", "3.141592653589793"),
    (r"math\.sqrt\(", "_sqrt("), (r"math\.min\(", "min("), (r"math\.max\(", "max("),
    (r"query\.anim_time", "_t"), (r"q\.anim_time", "_t"), (r"query\.life_time", "_t"),
    (r"query\.ground_speed", "4"), (r"query\.modified_distance_moved", "(_t*4)"),
]
_AMB = {"_sin": lambda g: math.sin(math.radians(g)), "_cos": lambda g: math.cos(math.radians(g)),
        "_clamp": lambda v, a, b: max(a, min(b, v)), "_lerp": lambda a, b, t: a + (b - a) * t,
        "_sqrt": math.sqrt, "abs": abs, "min": min, "max": max}


def _expr(v, t):
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v)
    for a, b in _MOLANG:
        s = re.sub(a, b, s)
    try:
        return float(eval(s, {"__builtins__": {}}, dict(_AMB, _t=t)))
    except Exception:
        return 0.0


def _vetor(v, t):
    if isinstance(v, dict) and "post" in v:
        v = v["post"]
    if isinstance(v, dict) and "vector" in v:
        v = v["vector"]
    if not isinstance(v, (list, tuple)):
        v = [v, v, v]
    return [_expr(x, t) for x in v]


def avaliar_canal(canal, t):
    if isinstance(canal, dict) and not ("post" in canal or "vector" in canal):
        tempos = sorted(canal, key=float)
        ts = [float(x) for x in tempos]
        if t <= ts[0]:
            return _vetor(canal[tempos[0]], t)
        if t >= ts[-1]:
            return _vetor(canal[tempos[-1]], t)
        for k in range(len(ts) - 1):
            if ts[k] <= t <= ts[k + 1]:
                a, b = _vetor(canal[tempos[k]], t), _vetor(canal[tempos[k + 1]], t)
                f = (t - ts[k]) / (ts[k + 1] - ts[k])
                suave = isinstance(canal[tempos[k + 1]], dict) or isinstance(canal[tempos[k]], dict)
                if suave:
                    f = f * f * (3 - 2 * f)
                return [x + (y - x) * f for x, y in zip(a, b)]
    return _vetor(canal, t)


def pose_em(animacao, t):
    """{osso: {"rotation": [..], "position": [..], "scale": [..]}} no instante t (segundos)."""
    extra = {}
    duracao = float(animacao.get("animation_length", 1.0) or 1.0)
    if animacao.get("loop") in (True, "true") and duracao > 0:
        t = t % duracao
    for osso, canais in animacao.get("bones", {}).items():
        extra[osso] = {k: avaliar_canal(v, t) for k, v in canais.items() if k in ("rotation", "position", "scale")}
    return extra
