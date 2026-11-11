"""
mcmodel: modelos de entidade para Minecraft (GeckoLib / Bedrock) descritos em Python,
com texturas em pixel art pintadas texel a texel.

    from mcmodel import *
"""
import sys as _sys

if hasattr(_sys.stdout, "reconfigure"):
    try:
        _sys.stdout.reconfigure(encoding="utf-8")   # acentos certos no console do Windows
    except Exception:
        pass

from .cores import rgba, hexa, rampa, rampa_manual, misturar, tom, luminancia, amostra_rampas
from .modelo import Modelo
from .pintura import (base, onde, gradiente, so_faces, sprite, par_de_sprites, pixels, retangulo, linha, elipse,
                      acima, abaixo, entre, caixa, esfera, faces, local, regiao, borda_da_face, listras, manchas,
                      e_, ou_, nao, sempre, ruido3, fbm, afinar, decalque)
from .animacao import onda, chaves, bipede, quadrupede, voador, bolinha, pose_em
from .textura2d import Textura2D
from . import render


def rampa_vanilla(cor, n=6, base=None, **kw):
    """Rampa com cores do Minecraft de verdade (ver scripts/vanilla.py). Devolve a Rampa."""
    import os as _os
    import sys as _s
    _s.path.insert(0, _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    from vanilla import rampa_vanilla as _rv
    return _rv(cor, n=n, base=base, **kw)[0]

__all__ = [n for n in dir() if not n.startswith("_")]
