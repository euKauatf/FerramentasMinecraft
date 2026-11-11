"""
Exemplo completo: raposa quadrúpede em densidade 2 (HD).
Mostra materiais com rampa, padrões 3D contínuos, sprites de olhos, oclusão automática e animação.

    D:\\FerramentasMinecraft\\venv\\Scripts\\python.exe raposa.py [pasta_de_saida]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from mcmodel import *  # noqa: E402,F403

m = Modelo("raposa", densidade=2)

# ---- paleta: uma rampa por material (escuro -> claro), base = índice da cor "normal"
m.material("pelo", rampa("#D8742E", n=7, base=4), ruido=0.3)
m.material("creme", rampa("#F3E2C7", n=5, base=3), ruido=0.2, volume=0.5)
m.material("escuro", rampa("#3A2A2A", n=4, base=2), ruido=0.15, aresta_clara=0.3)
m.material("nariz", rampa("#2A2026", n=3, base=1), ruido=0, volume=0.3)

OLHO = """
kkk
kwa
kaa
"""
cores_olho = {"k": "#1C1418", "w": "#FFFFFF", "a": "#E0A030"}

# ---- corpo
corpo = m.osso("body", pivo=[0, 10, 0])
corpo.cubo([-3.5, 7, -6], [7, 6, 13], [
    base("pelo"),
    onde(e_(abaixo(9), faces("down", "east", "west", "north")), mat="creme"),  # barriga clara
    onde(e_(acima(12.5), listras(2, 3.0, 1.0, ondulacao=0.6, eixo_onda=0)), somar_luz=-1.0),  # dorso marcado
])

# ---- cabeça (filha do corpo)
cabeca = m.osso("head", pivo=[0, 12, -6], pai="body")
cabeca.cubo([-3.5, 10, -11], [7, 6, 5], [
    base("pelo"),
    onde(e_(abaixo(12.5), ou_(faces("north"), local(2, 0, 0.5))), mat="creme"),  # bochechas e queixo
], faces={"north": [par_de_sprites(OLHO, cores_olho, centro_esq=(0.27, 0.36), centro_dir=(0.73, 0.36))]})
cabeca.cubo([-1.5, 10, -14], [3, 2.5, 3], [
    base("creme"),
    onde(acima(11.5), mat="pelo"),
], faces={"north": [retangulo(2, 0, 2, 2, "nariz")]})
for lado, x in (("esq", 1.5), ("dir", -3.5)):
    cabeca.cubo([x, 16, -9], [2, 3, 1], [
        base("pelo"),
        onde(acima(18), mat="escuro"),
    ], faces={"north": [onde(e_(abaixo(18), regiao(0.25, 0.0, 0.75, 1)), mat="escuro", luz=1)]})

# ---- pernas (padrão do quadrupede(): leg_front_left etc.; +X é o lado ESQUERDO da criatura)
for nome, x, z in (("leg_front_left", 1.5, -4.5), ("leg_front_right", -3.5, -4.5),
                   ("leg_back_left", 1.5, 3.5), ("leg_back_right", -3.5, 3.5)):
    perna = m.osso(nome, pivo=[x + 1, 7, z + 1], pai="body")
    perna.cubo([x, 0, z], [2, 7, 2], [base("pelo"), onde(abaixo(2.5), mat="escuro")])

# ---- cauda: fofa, com ponta branca
cauda = m.osso("tail", pivo=[0, 11.5, 7], pai="body", rotacao=[-35, 0, 0])
cauda.cubo([-2, 9, 7], [4, 4, 9], [
    base("pelo"),
    onde(entre(2, 13, 17), mat="creme"),
    onde(entre(2, 12, 13), somar_luz=-0.8),
])

for nome, an in quadrupede(peso=0.9).items():
    m.animacao(nome, an["animation_length"], an["bones"], an["loop"])

if __name__ == "__main__":
    saida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "saida")
    m.salvar(saida)
