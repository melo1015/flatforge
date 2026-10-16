# FlatForge: guía de integración y uso

**Estado:** guía de integración para el prototipo actual.  
**Requisitos:** Python 3.11 o superior; Blender 3.6 o superior solo para la integración Blender.  
**Objetivo:** ejecutar el worker de geometría, conectarlo con clientes Python/MCP o Blender y probar cinco escenarios reproducibles.

> FlatForge es un prototipo de geometría, no un sistema CAD/CAM certificado. Los resultados deben inspeccionarse en la aplicación CAD/CAM de destino y validarse antes de fabricar piezas. No se debe usar para decisiones críticas de seguridad o resistencia estructural.

## 1. Componentes y flujo de datos

- `flatforge_proto`: validación y errores del protocolo JSON-RPC.
- `flatforge_worker`: servidor TCP local que recibe solicitudes JSON-RPC delimitadas por salto de línea.
- `flatforge_worker/engines`: algoritmos de desplegado de mallas, anidado 2D y extracción de secciones de malla.
- `flatforge_mcp`: puente que expone herramientas MCP para asistentes compatibles.
- `flatforge_worker/addon`: complemento Blender para comprobar conexión y desplegar la malla seleccionada.
- `flatforge_maker`: interfaz web local para anidar piezas rectangulares o contornos poligonales simples y exportar SVG.

El worker escucha por defecto en `127.0.0.1:8765`; Maker utiliza `127.0.0.1:8787`. Son dos servicios independientes. Ejecutar el worker no inicia Maker automáticamente.

## 2. Instalación desde un clon limpio

Clona el repositorio y entra en su carpeta:

```bash
git clone https://github.com/melo1015/flatforge.git
cd flatforge
python --version
```

Se recomienda Python 3.11 o superior. Crea un entorno virtual:

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
```

Instala el puente MCP y las herramientas de prueba:

```bash
python -m pip install --upgrade pip
python -m pip install -e ./flatforge_mcp
python -m pip install pytest
```

Ejecuta las pruebas automatizadas:

```bash
PYTHONPATH=. python -m pytest -q
```

En Windows PowerShell, si `PYTHONPATH=.` no funciona como asignación de entorno, usa:

```powershell
$env:PYTHONPATH = "."
python -m pytest -q
```

## 3. Iniciar los servicios

### Worker de geometría

En la primera terminal, desde la raíz del repositorio:

```bash
python -m flatforge_worker.server
```

Salida esperada: un mensaje que indica que escucha en `127.0.0.1:8765`. Mantén esta terminal abierta.

### Interfaz FlatForge Maker

En otra terminal, desde la raíz:

```bash
python -m flatforge_maker.server
```

Abre [http://127.0.0.1:8787](http://127.0.0.1:8787). Para detener cada servicio, pulsa Ctrl+C en su terminal.

### Puente MCP

Con el worker en ejecución, inicia el puente desde otra terminal con el mismo entorno virtual:

```bash
flatforge-mcp
```

Alternativamente, desde la raíz del proyecto:

```bash
python -m flatforge_mcp.bridge
```

El puente MCP no es una interfaz de usuario independiente: debe configurarse como servidor MCP en el cliente compatible que se vaya a utilizar. Los detalles exactos de registro dependen de ese cliente.

## 4. Configuración del worker

Variables de entorno reconocidas:

| Variable | Predeterminado | Propósito |
|---|---:|---|
| `FLATFORGE_HOST` | `127.0.0.1` | Dirección de escucha del worker |
| `FLATFORGE_PORT` | `8765` | Puerto TCP |
| `FLATFORGE_READ_TIMEOUT` | `10` segundos | Tiempo máximo de espera de lectura |
| `FLATFORGE_MAX_CONNECTIONS` | `32` | Conexiones concurrentes máximas |
| `FLATFORGE_TOKEN` | vacío | Activa autenticación por token compartido si tiene valor |
| `FLATFORGE_TIMEOUT` | depende del cliente | Tiempo de espera del cliente MCP |

Si se configura `FLATFORGE_TOKEN`, el cliente MCP y el complemento Blender deben heredar el mismo valor en sus respectivos procesos. Un token vacío desactiva la autenticación. El protocolo TCP no cifra el tráfico: no expongas el puerto directamente a Internet. Para acceso remoto, utiliza una red privada o túnel seguro y una capa TLS adecuada.

Ejemplo en Linux/macOS:

```bash
export FLATFORGE_TOKEN='reemplaza-por-un-secreto-largo'
python -m flatforge_worker.server
```

En PowerShell:

```powershell
$env:FLATFORGE_TOKEN = "reemplaza-por-un-secreto-largo"
python -m flatforge_worker.server
```

## 5. Protocolo JSON-RPC y prueba de conexión

El worker acepta mensajes JSON-RPC 2.0 codificados en UTF-8, uno por línea, por TCP. Cada petición debe terminar en salto de línea. Los métodos principales son:

- `system.ping`
- `geometry.nest`
- `geometry.unfold`
- `geometry.generate_ribs`

Prueba manual de conexión con Python:

```python
import json
import socket

HOST, PORT = "127.0.0.1", 8765
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "system.ping",
    "params": {},
}

with socket.create_connection((HOST, PORT), timeout=5) as sock:
    sock.sendall((json.dumps(request) + "\\n").encode("utf-8"))
    with sock.makefile("rb") as stream:
        response = json.loads(stream.readline().decode("utf-8"))

print(response)
assert response.get("result", {}).get("ok") is True
```

La respuesta correcta incluye `result.ok: true` y `result.service: "flatforge-worker"`. Si no conecta, verifica que el worker esté activo, el host/puerto coincidan y las variables de autenticación sean iguales.

## 6. Cinco casos de uso e implementación

Los ejemplos de protocolo de esta sección se pueden enviar con el cliente TCP anterior sustituyendo el objeto `request`. Para mantener las pruebas fáciles de repetir, cada ejemplo incluye datos pequeños. Las coordenadas y dimensiones están en las unidades de entrada; Maker exporta SVG con unidades milimétricas.

### Caso 1 — Distribuir piezas rectangulares para corte de una plancha

**Escenario real:** un taller de carpintería necesita distribuir piezas rectangulares de un mueble sobre una plancha de 2440 × 1220 mm, respetando un margen perimetral y una separación entre piezas.

**Petición JSON-RPC:**

```json
{
  "jsonrpc": "2.0",
  "id": 101,
  "method": "geometry.nest",
  "params": {
    "sheet_width": 2440,
    "sheet_height": 1220,
    "margin": 10,
    "gap": 4,
    "allow_rotation": true,
    "parts": [
      {"id": "lateral_A", "width": 720, "height": 560},
      {"id": "lateral_B", "width": 720, "height": 560},
      {"id": "estante_1", "width": 680, "height": 300},
      {"id": "estante_2", "width": 680, "height": 300},
      {"id": "base", "width": 900, "height": 420}
    ]
  }
}
```

**Implementación:**
1. Inicia el worker.
2. Envía la petición al método `geometry.nest`.
3. Lee `result.placements`, `result.unplaced` y las métricas devueltas.
4. Si hay piezas en `unplaced`, revisa las dimensiones o prueba otra plancha; no las des por incluidas.
5. Confirma el resultado en Maker o en el programa CAM de la máquina antes de cortar.

**Qué esperar:** una distribución determinista de las piezas que el algoritmo consiga colocar. El motor rectangular usa una heurística MaxRects; no garantiza el mínimo desperdicio global. La utilización reportada es una estimación geométrica, no incorpora kerf, sujeciones, veta, pestañas ni restricciones específicas de la máquina.

### Caso 2 — Anidar contornos de piezas irregulares importados desde SVG

**Escenario real:** un fabricante de rótulos corta piezas planas con contornos poligonales, por ejemplo placas con esquinas recortadas. Tiene un SVG con contornos cerrados.

**Implementación mediante Maker:**
1. Inicia el worker y Maker en sus terminales respectivas.
2. Abre [http://127.0.0.1:8787](http://127.0.0.1:8787).
3. Introduce las dimensiones de la plancha, el margen y la separación.
4. Selecciona **Importar contornos SVG** y carga un SVG pequeño que contenga contornos admitidos.
5. Pulsa **Calcular distribución** y revisa el resultado visual, la utilización y las piezas no colocadas.
6. Exporta SVG solo después de revisar el resultado. Abre el archivo exportado en el software CAM y confirma escala, unidades, orientación y parámetros de corte.

**Ejemplo de petición poligonal equivalente para el worker:**

```json
{
  "jsonrpc": "2.0",
  "id": 102,
  "method": "geometry.nest",
  "params": {
    "sheet_width": 600,
    "sheet_height": 400,
    "margin": 8,
    "gap": 3,
    "allow_rotation": true,
    "parts": [
      {"id": "placa_chaflan", "points": [[0, 0], [120, 0], [100, 60], [0, 60]]},
      {"id": "placa_triangulo", "points": [[0, 0], [90, 0], [45, 55]]},
      {"id": "soporte_L", "points": [[0, 0], [80, 0], [80, 20], [20, 20], [20, 70], [0, 70]]}
    ]
  }
}
```

**Límites:** se admiten contornos poligonales simples, cerrados y sin agujeros. El importador SVG admite elementos `rect`, `polygon` y `polyline` explícitamente cerrados; no admite curvas, rutas SVG, transformaciones ni grupos anidados. El motor poligonal es heurístico, admite rotación de 90° y tiene límites de cantidad de piezas/vértices. No sustituye la simulación CAM. Si se exporta una distribución parcial, las piezas no colocadas no aparecen en el SVG.

### Caso 3 — Desplegar una malla 3D de Blender a coordenadas 2D

**Escenario real:** un diseñador necesita obtener una primera representación plana de una malla triangular para analizar superficies o preparar un proceso posterior de diseño.

**Preparación:**
1. Instala Blender 3.6 o superior.
2. Inicia el worker en la misma máquina.
3. Configura `FLATFORGE_TOKEN` en el entorno de Blender si también lo configuraste en el worker.
4. En Blender, instala/activa el complemento de FlatForge desde el código del repositorio según el flujo de instalación de complementos de tu versión.
5. Selecciona un objeto de tipo malla y ejecuta el operador de desplegado de FlatForge.

**Comprobación de integración automatizada:** desde la raíz del repositorio, con el worker activo, ejecuta:

```bash
blender --background --factory-startup --python scripts/blender_smoke_test.py
```

El script está diseñado para comprobar que Blender puede registrar el complemento, conectar con el worker y crear una malla plana a partir de un cubo de prueba. Requiere que el ejecutable `blender` esté disponible en PATH; en Windows puedes indicar la ruta completa a `blender.exe`.

**Petición directa equivalente:**

```json
{
  "jsonrpc": "2.0",
  "id": 103,
  "method": "geometry.unfold",
  "params": {
    "mesh": {
      "vertices": [
        [0, 0, 0],
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1]
      ],
      "faces": [
        [0, 2, 1],
        [0, 1, 3],
        [1, 2, 3],
        [2, 0, 3]
      ]
    }
  }
}
```

**Qué comprobar:** el resultado incluye coordenadas 2D y triángulos para el desplegado. El algoritmo triangula las caras poligonales mediante abanico y despliega a lo largo de un árbol de caras. No optimiza automáticamente los cortes ni detecta solapamientos 2D; las caras cóncavas deben triangularse de forma apropiada antes de enviarlas. Por tanto, el resultado es una base geométrica que debe inspeccionarse, no un patrón de fabricación certificado.

### Caso 4 — Extraer secciones para planificar costillas de una estructura

**Escenario real:** un diseñador de maquetas o prototipos quiere inspeccionar cortes transversales regulares de una malla para planificar dónde irían costillas o tabiques.

**Petición JSON-RPC:**

```json
{
  "jsonrpc": "2.0",
  "id": 104,
  "method": "geometry.generate_ribs",
  "params": {
    "axis": "z",
    "spacing": 25,
    "start": 0,
    "end": 100,
    "mesh": {
      "vertices": [
        [0, 0, 0],
        [100, 0, 0],
        [100, 60, 0],
        [0, 60, 0],
        [0, 0, 100],
        [100, 0, 100],
        [100, 60, 100],
        [0, 60, 100]
      ],
      "faces": [
        [0, 3, 2, 1],
        [4, 5, 6, 7],
        [0, 1, 5, 4],
        [1, 2, 6, 5],
        [2, 3, 7, 6],
        [3, 0, 4, 7]
      ]
    }
  }
}
```

**Implementación:**
1. Sustituye la malla de caja del ejemplo por los vértices y caras de tu modelo triangulado o poligonal.
2. Ajusta `axis` a `x`, `y` o `z`, `spacing` a la separación deseada y `start`/`end` al intervalo.
3. Revisa `result.planes`: cada plano contiene `offset`, `segments` y `segment_count`.
4. Exporta o procesa esos segmentos con una herramienta posterior para cerrar contornos y diseñar las costillas.

**Límite importante:** la función calcula segmentos de intersección; no cose automáticamente los segmentos en contornos cerrados ni genera sólidos de costillas con espesor. No es un análisis estructural ni valida resistencia.

### Caso 5 — Conectar un asistente compatible con MCP a las herramientas de FlatForge

**Escenario real:** un equipo técnico quiere pedir a un asistente compatible que compruebe el servicio, anide piezas o prepare datos de una malla sin escribir una conexión TCP propia para cada operación.

**Instalación y ejecución:**

```bash
python -m pip install -e ./flatforge_mcp
python -m flatforge_worker.server
```

En una segunda terminal, dentro del mismo entorno:

```bash
flatforge-mcp
```

Configura ese comando como servidor MCP en el cliente que utilices. La forma de registrar un servidor MCP varía según el cliente, así que usa el mecanismo oficial de configuración de esa aplicación. Si el worker tiene token, inicia también el proceso del puente con el mismo `FLATFORGE_TOKEN`.

**Herramientas expuestas por el puente:**
- `flatforge_ping()`: verifica que el worker responde.
- `nest_parts(parts, sheet_width, sheet_height)`: anida piezas rectangulares o polígonos simples compatibles.
- `unfold_mesh(mesh)`: devuelve el desplegado 2D de una malla.
- `generate_ribs(mesh)`: extrae segmentos de secciones de la malla.

**Ejemplo de petición que el asistente puede realizar mediante la herramienta de anidado:**

```json
{
  "parts": [
    {"id": "panel_A", "width": 400, "height": 250},
    {"id": "panel_B", "width": 300, "height": 200},
    {"id": "tapa", "width": 180, "height": 180}
  ],
  "sheet_width": 1000,
  "sheet_height": 600
}
```

Este ejemplo representa los argumentos de la herramienta MCP, no un mensaje JSON-RPC TCP completo. El resultado se debe revisar igual que en los demás casos: MCP facilita la integración con el asistente, pero no convierte el cálculo geométrico en un resultado certificado.

## 7. Diagnóstico de problemas

| Síntoma | Comprobaciones |
|---|---|
| Conexión rechazada en el puerto 8765 | Confirma que el worker sigue activo y escucha en el host/puerto esperado. |
| Error de autenticación | Comprueba que `FLATFORGE_TOKEN` esté definido de la misma forma en el worker y el cliente. |
| Error de parámetros | Comprueba que cada método recibe su objeto `params` y que las coordenadas/dimensiones son números finitos. |
| Algunas piezas no aparecen | Revisa la lista `unplaced`, las dimensiones de la plancha, el margen, el espacio y los límites del motor. |
| El SVG no conserva el diseño esperado | Comprueba que los contornos estén dentro del subconjunto SVG admitido y que no utilicen transformaciones, curvas ni grupos. |
| Blender no encuentra el worker | Ejecuta primero el worker; confirma host/puerto, token y entorno del proceso Blender. |
| El resultado 2D parece solapado | El desplegado no detecta solapamientos; inspecciona el resultado en una herramienta geométrica independiente. |
| CI pasa pero Blender falla | CI no equivale a una prueba de Blender real. Ejecuta el smoke test en una instalación de Blender compatible y conserva el log completo. |

## 8. Lista de verificación antes de usar resultados

- [ ] Las pruebas automatizadas pasan en el entorno instalado.
- [ ] El worker responde a `system.ping`.
- [ ] Las piezas que no caben se han revisado explícitamente.
- [ ] La geometría y las unidades corresponden a las dimensiones reales.
- [ ] Se ha considerado kerf, margen real de herramienta, sujeciones, orientación de material y restricciones CAM.
- [ ] Los SVG se abrieron en el software de destino y se verificó su escala.
- [ ] Las mallas desplegadas se inspeccionaron en busca de cortes y solapamientos.
- [ ] El worker no está expuesto directamente a Internet y el token, si se usa, se protege como secreto.

## 9. Referencias del repositorio

- [README principal](../README.md)
- [Documentación de Maker](../flatforge_maker/README.md)
- [Protocolo JSON-RPC](protocol.md)
- [Herramientas MCP](mcp_tools.md)
- [Despliegue](deployment.md)
- [Estado de implementación y limitaciones](implementation-status.md)
- [Auditoría de integración](integration-audit.md)
