# Formatos, pastas e ferramentas externas

## GeckoLib / Bedrock (.geo.json)

- `format_version` "1.12.0"; `minecraft:geometry[0].description.identifier` = `geometry.<nome>`.
- Ossos: `name`, `pivot`, `parent`, `rotation` (graus), `cubes`. Cubos: `origin` (canto mínimo,
  coordenadas absolutas), `size`, `uv` por face (`{"north": {"uv": [u, v], "uv_size": [w, h]}}`),
  `rotation` + `pivot` próprios, `inflate`.
- A face `down` é gravada com `uv_size` negativo em V (`uv: [u, v+h]`, `uv_size: [w, -h]`); assim
  o GeckoLib/Bedrock a mostra na mesma orientação da box UV. O mcmodel já faz isso.
- Textura: qualquer tamanho; `texture_width/height` devem bater com a imagem (ou ser divisores
  exatos dela). Transparência é recortada (alfa < ~10% some), não misturada.
- `visible_bounds_*` só importam no Bedrock (culling); o GeckoLib os ignora.

## Animações (.animation.json)

```json
{"format_version": "1.8.0", "animations": {
  "animation.raposa.walk": {"loop": true, "animation_length": 0.8, "bones": {
     "leg_front_left": {"rotation": ["math.sin(query.anim_time / 0.8 * 360) * 28", "0", "0"]},
     "body": {"position": {"0.0": [0, 0, 0], "0.4": {"post": [0, 0.5, 0], "lerp_mode": "catmullrom"}}}
  }}}}
```
Molang: `math.sin/cos` recebem **graus**. `query.anim_time` = segundos desde o início da animação.
`loop`: true, false ou "hold_on_last_frame".

## Onde os arquivos vão num mod (GeckoLib)

| GeckoLib | modelos | animações | texturas |
|---|---|---|---|
| 4.x e 5.x (MC 1.20.x em diante) | `assets/<modid>/geckolib/models/entity/` | `assets/<modid>/geckolib/animations/entity/` | `assets/<modid>/textures/entity/` |
| 3.x (MC 1.16–1.19) | `assets/<modid>/geo/` | `assets/<modid>/animations/` | `assets/<modid>/textures/entity/` |

Confira o projeto antes: procure arquivos `*.geo.json` existentes e copie o padrão de pastas. Os
nomes das animações que o código Java espera (ex. `animation.<nome>.idle`) precisam bater com o
que o modelo exporta — procure por `RawAnimation` ou `"animation.` no código.

## Bedrock (addon/resource pack)

Modelos em `models/entity/`, animações em `animations/`, texturas em `textures/entity/`, mais o
`entity/<nome>.entity.json` (client entity) que liga tudo. O formato do .geo.json é o mesmo.

## Java vanilla: modelos de bloco e item (.json)

Não usam ossos nem animação. Elementos com `from`/`to` em 0–16, faces com `uv` em 0–16 da textura
16×16 e `texture: "#nome"`, rotação só em um eixo (−45/−22.5/0/22.5/45). Para ícones de item
basta a textura 2D (`Textura2D`) e um `item/generated`:
```json
{"parent": "minecraft:item/generated", "textures": {"layer0": "<modid>:item/rubi"}}
```

## Blockbench (para o usuário ver e mexer)

- Portátil, sem instalação: `D:\FerramentasMinecraft\Blockbench\Blockbench_5.2.2_portable.exe`.
  Abra o `.geo.json` (Arquivo → Abrir) e depois arraste a textura `.png` para o painel de texturas.
  Animações: aba "Animar" → Arquivo → Importar animações.
- Versão web (sem instalar nada): https://web.blockbench.net
- Verificação automática pelo navegador embutido, se precisar tirar uma dúvida de orientação:
  em web.blockbench.net, `Codecs.bedrock.load(geoJson, {path: 'x.geo.json'})`, depois
  `new Texture({name:'t'}).fromDataURL(dataUrl).add()` e `Cube.all.forEach(c => c.applyTexture(tex, true))`.
  Câmeras: `Preview.selected.loadAnglePreset(DefaultCameraPresets.find(p => p.id === 'north'))`.


## Como o GeckoLib 5.5 desenha UV por face (lido no código: GeometryCube, VertexSet, GeometryQuadUvs)

- Inverte o X do arquivo: x_interno = -(x_arquivo), origem = -(origin.x + size.x).
- Sem `mirror`, troca u0/u1. Resultado em coordenadas do ARQUIVO (canto superior esquerdo da textura):
  north: lado z0, coluna esquerda em x0, linha de cima em y1 | south: z1, esquerda em x1
  up: topo em z1, esquerda em x0 | down (uv_size v negativo): topo em z1, esquerda em x0
  **"east": lado x0 (-X do arquivo), esquerda em z1 | "west": lado x1 (+X), esquerda em z0**
- Ou seja: a face que fica no +X do arquivo se chama "west" no .geo.json. A biblioteca grava assim
  (geometria.CHAVE_ARQUIVO) e o renderizador lê assim (geometria.FACE_DA_CHAVE).
- Faces coplanares viradas para o mesmo lado e sobrepostas piscam (render entityCutoutNoCull).
