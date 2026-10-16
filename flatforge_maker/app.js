(() => {
  "use strict";

  const $ = (selector) => document.querySelector(selector);
  const partsList = $("#partsList");
  const form = $("#nestForm");
  const calculateButton = $("#calculateButton");
  const exportButton = $("#exportButton");
  const sheetSvg = $("#sheetSvg");
  const emptyState = $("#emptyState");
  const notice = $("#notice");
  const SVG_NS = "http://www.w3.org/2000/svg";
  const palette = ["#3567e8", "#27856f", "#9566cf", "#d08035", "#287ea3", "#c25b75"];

  let lastResult = null;
  let lastRequest = null;
  let partSequence = 0;

  const sampleParts = [
    { id: "Panel A", width: 180, height: 120 },
    { id: "Panel B", width: 150, height: 90 },
    { id: "Soporte 1", width: 80, height: 140 },
    { id: "Soporte 2", width: 80, height: 140 }
  ];

  function showNotice(message, type = "error") {
    notice.textContent = message;
    notice.className = type === "success" ? "notice success" : "notice";
    notice.hidden = false;
  }

  function hideNotice() {
    notice.hidden = true;
    notice.textContent = "";
  }

  function makeSvgElement(name, attributes = {}) {
    const element = document.createElementNS(SVG_NS, name);
    Object.entries(attributes).forEach(([key, value]) => element.setAttribute(key, String(value)));
    return element;
  }

  function createPartRow(part = {}) {
    partSequence += 1;
    const row = document.createElement("div");
    row.className = "part-row";
    row.dataset.partRow = "true";

    const name = document.createElement("input");
    name.className = "part-name";
    name.type = "text";
    name.maxLength = 60;
    name.value = String(part.id ?? `Pieza ${partSequence}`);
    name.setAttribute("aria-label", "Nombre de la pieza");
    name.required = true;

    const width = document.createElement("input");
    width.type = "number";
    width.min = "0.1";
    width.max = "100000";
    width.step = "0.1";
    width.value = String(part.width ?? 100);
    width.setAttribute("aria-label", "Ancho de la pieza en milímetros");
    width.required = true;

    const height = document.createElement("input");
    height.type = "number";
    height.min = "0.1";
    height.max = "100000";
    height.step = "0.1";
    height.value = String(part.height ?? 100);
    height.setAttribute("aria-label", "Alto de la pieza en milímetros");
    height.required = true;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "remove-part";
    remove.textContent = "×";
    remove.setAttribute("aria-label", "Eliminar pieza");
    remove.addEventListener("click", () => {
      row.remove();
      updatePartCount();
      invalidateLayout();
    });

    [name, width, height].forEach((input) => {
      input.addEventListener("input", () => {
        updatePartCount();
        invalidateLayout();
      });
    });

    row.append(name, width, height, remove);
    partsList.appendChild(row);
    updatePartCount();
  }

  function updatePartCount() {
    const count = partsList.querySelectorAll("[data-part-row]").length;
    $("#partCount").textContent = `${count} ${count === 1 ? "pieza" : "piezas"}`;
  }

  function invalidateLayout() {
    if (!lastResult) return;
    lastResult = null;
    exportButton.disabled = true;
    $("#layoutStatus").textContent = "Pendiente de cálculo";
    $("#layoutStatus").className = "status-pill status-idle";
    showNotice("Cambiaste la configuración. Vuelve a calcular para actualizar la vista y el archivo exportable.");
  }

  function readNumber(id, label, min, max) {
    const input = $(id);
    const value = Number(input.value);
    if (!input.value.trim() || !Number.isFinite(value) || value < min || value > max) {
      input.focus();
      throw new Error(`${label}: introduce un valor entre ${min} y ${max} mm.`);
    }
    return value;
  }

  function readRequest() {
    const sheetWidth = readNumber("#sheetWidth", "Ancho de la lámina", 1, 100000);
    const sheetHeight = readNumber("#sheetHeight", "Alto de la lámina", 1, 100000);
    const margin = readNumber("#margin", "Margen", 0, 10000);
    const gap = readNumber("#gap", "Separación", 0, 10000);
    if (margin * 2 >= sheetWidth || margin * 2 >= sheetHeight) {
      throw new Error("El margen debe dejar un área útil mayor que cero.");
    }

    const rows = [...partsList.querySelectorAll("[data-part-row]")];
    if (!rows.length) throw new Error("Añade al menos una pieza antes de calcular.");
    if (rows.length > 500) throw new Error("El prototipo admite como máximo 500 piezas por cálculo.");

    const seen = new Set();
    const parts = rows.map((row, index) => {
      const inputs = row.querySelectorAll("input");
      const id = inputs[0].value.trim();
      const width = Number(inputs[1].value);
      const height = Number(inputs[2].value);
      if (!id) throw new Error(`La pieza ${index + 1} necesita un nombre.`);
      if (seen.has(id.toLocaleLowerCase())) throw new Error(`El nombre "${id}" está repetido. Usa nombres únicos.`);
      seen.add(id.toLocaleLowerCase());
      if (!Number.isFinite(width) || width <= 0 || width > 100000 ||
          !Number.isFinite(height) || height <= 0 || height > 100000) {
        throw new Error(`Revisa el ancho y el alto de "${id}". Deben ser valores positivos.`);
      }
      return { id, width, height };
    });

    return {
      parts,
      sheet_width: sheetWidth,
      sheet_height: sheetHeight,
      margin,
      gap,
      allow_rotation: $("#allowRotation").checked
    };
  }

  function formatNumber(value, decimals = 1) {
    return Number(value).toLocaleString("es-ES", { maximumFractionDigits: decimals });
  }

  function renderLayout(result, request) {
    const sheetWidth = request.sheet_width;
    const sheetHeight = request.sheet_height;
    sheetSvg.replaceChildren();
    sheetSvg.setAttribute("viewBox", `0 0 ${sheetWidth} ${sheetHeight}`);
    sheetSvg.setAttribute("width", `${sheetWidth}mm`);
    sheetSvg.setAttribute("height", `${sheetHeight}mm`);
    sheetSvg.setAttribute("preserveAspectRatio", "xMidYMid meet");

    sheetSvg.appendChild(makeSvgElement("rect", {
      x: 0, y: 0, width: sheetWidth, height: sheetHeight,
      fill: "#ffffff", stroke: "#9aa8bc", "stroke-width": Math.max(sheetWidth, sheetHeight) / 1000,
      "data-guide": "true"
    }));

    if (request.margin > 0) {
      sheetSvg.appendChild(makeSvgElement("rect", {
        x: request.margin, y: request.margin,
        width: sheetWidth - request.margin * 2,
        height: sheetHeight - request.margin * 2,
        fill: "#f7f9fc", stroke: "#bdc9db",
        "stroke-width": Math.max(sheetWidth, sheetHeight) / 1400,
        "stroke-dasharray": `${Math.max(sheetWidth, sheetHeight) / 100} ${Math.max(sheetWidth, sheetHeight) / 65}`,
        "data-guide": "true"
      }));
    }

    const names = new Map(request.parts.map((part) => [String(part.id), part.id]));
    (result.placements || []).forEach((placement, index) => {
      const x = Number(placement.x);
      const y = Number(placement.y);
      const width = Number(placement.width);
      const height = Number(placement.height);
      const strokeWidth = Math.max(Math.min(sheetWidth, sheetHeight) / 900, 0.15);
      const group = makeSvgElement("g", { "data-part": String(placement.id) });
      group.appendChild(makeSvgElement("rect", {
        x, y, width, height,
        fill: palette[index % palette.length],
        "fill-opacity": "0.20",
        stroke: palette[index % palette.length],
        "stroke-width": strokeWidth,
        "vector-effect": "non-scaling-stroke",
        "data-cut-line": "true"
      }));

      if (width > Math.min(sheetWidth, sheetHeight) * 0.07 &&
          height > Math.min(sheetWidth, sheetHeight) * 0.045) {
        const label = makeSvgElement("text", {
          x: x + width / 2,
          y: y + height / 2,
          fill: "#253b5a",
          "font-size": Math.max(Math.min(sheetWidth, sheetHeight) / 36, 3),
          "text-anchor": "middle",
          "dominant-baseline": "middle",
          "pointer-events": "none",
          "data-preview-only": "true"
        });
        label.textContent = String(names.get(String(placement.id)) ?? placement.id);
        group.appendChild(label);
      }
      sheetSvg.appendChild(group);
    });

    emptyState.hidden = true;
    sheetSvg.hidden = false;

    const placed = result.placements?.length ?? 0;
    const total = result.part_count ?? request.parts.length;
    const utilization = Number(result.utilization || 0);
    const usedArea = (result.placements || []).reduce((sum, part) => sum + Number(part.width) * Number(part.height), 0);
    const totalArea = sheetWidth * sheetHeight;
    const waste = Math.max(0, totalArea - usedArea);

    $("#utilizationValue").textContent = `${formatNumber(utilization * 100, 2)}%`;
    $("#placedValue").textContent = `${placed}/${total}`;
    $("#placedDetail").textContent = result.unplaced?.length ? `${result.unplaced.length} pendiente(s)` : "Todas las piezas colocadas";
    $("#wasteValue").textContent = `${formatNumber(waste / 1000000, 3)} m²`;

    const unplacedPanel = $("#unplacedPanel");
    const unplacedList = $("#unplacedList");
    unplacedList.replaceChildren();
    (result.unplaced || []).forEach((id) => {
      const li = document.createElement("li");
      li.textContent = String(id);
      unplacedList.appendChild(li);
    });
    unplacedPanel.hidden = !(result.unplaced && result.unplaced.length);

    const status = $("#layoutStatus");
    if (result.unplaced?.length) {
      status.textContent = "Distribución parcial";
      status.className = "status-pill status-warning";
    } else {
      status.textContent = "Distribución calculada";
      status.className = "status-pill status-ok";
    }
    exportButton.disabled = placed === 0;
  }

  async function calculate(request) {
    calculateButton.disabled = true;
    calculateButton.innerHTML = '<span aria-hidden="true">◌</span> Calculando… <span aria-hidden="true">→</span>';
    hideNotice();
    try {
      const response = await fetch("/api/nest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request)
      });
      const result = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(result.error || `El servidor respondió con código ${response.status}.`);
      lastRequest = request;
      lastResult = result;
      renderLayout(result, request);
      if (result.unplaced?.length) {
        showNotice(`Distribución parcial: ${result.unplaced.length} pieza(s) no caben. Ajusta la lámina o las dimensiones de las piezas.`);
      } else {
        showNotice("Distribución calculada. Revisa el patrón y verifica la escala antes de fabricar.", "success");
      }
    } catch (error) {
      showNotice(error instanceof TypeError
        ? "No se pudo conectar con el motor local. Inicia FlatForge Maker con «python -m flatforge_maker.server»."
        : error.message || "Ocurrió un error al calcular la distribución.");
    } finally {
      calculateButton.disabled = false;
      calculateButton.innerHTML = '<span aria-hidden="true">✳</span> Calcular distribución <span aria-hidden="true">→</span>';
    }
  }

  function exportSvg() {
    if (!lastResult || !lastRequest || !lastResult.placements?.length) return;
    const exported = sheetSvg.cloneNode(true);
    exported.querySelectorAll('[data-guide="true"], [data-preview-only="true"]').forEach((element) => element.remove());
    exported.setAttribute("xmlns", SVG_NS);
    exported.setAttribute("width", `${lastRequest.sheet_width}mm`);
    exported.setAttribute("height", `${lastRequest.sheet_height}mm`);
    exported.setAttribute("viewBox", `0 0 ${lastRequest.sheet_width} ${lastRequest.sheet_height}`);
    exported.setAttribute("version", "1.1");
    exported.setAttribute("aria-label", "FlatForge Maker cutting pattern in millimeters");

    const source = '<?xml version="1.0" encoding="UTF-8"?>\n' + new XMLSerializer().serializeToString(exported);
    const blob = new Blob([source], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "flatforge-patron.svg";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showNotice("SVG exportado en milímetros. Abre el archivo en tu software de corte y confirma las dimensiones antes de enviar el trabajo.", "success");
  }

  function loadSamples() {
    partsList.replaceChildren();
    partSequence = 0;
    sampleParts.forEach(createPartRow);
    $("#sheetWidth").value = "600";
    $("#sheetHeight").value = "400";
    $("#margin").value = "8";
    $("#gap").value = "3";
    $("#allowRotation").checked = true;
    lastResult = null;
    lastRequest = null;
    exportButton.disabled = true;
    sheetSvg.hidden = true;
    emptyState.hidden = false;
    $("#layoutStatus").textContent = "Pendiente de cálculo";
    $("#layoutStatus").className = "status-pill status-idle";
    $("#utilizationValue").textContent = "—";
    $("#placedValue").textContent = "—";
    $("#placedDetail").textContent = "Calcula para ver detalles";
    $("#wasteValue").textContent = "—";
    $("#unplacedPanel").hidden = true;
    hideNotice();
  }

  $("#addPartButton").addEventListener("click", () => {
    if (partsList.querySelectorAll("[data-part-row]").length >= 500) {
      showNotice("El prototipo admite como máximo 500 piezas por cálculo.");
      return;
    }
    createPartRow({ id: `Pieza ${partSequence + 1}`, width: 100, height: 100 });
    invalidateLayout();
  });

  $("#sampleButton").addEventListener("click", () => {
    if (!partsList.children.length) loadSamples();
    readAndCalculate();
  });

  $("#resetButton").addEventListener("click", loadSamples);
  exportButton.addEventListener("click", exportSvg);

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    readAndCalculate();
  });

  async function readAndCalculate() {
    try {
      const request = readRequest();
      await calculate(request);
    } catch (error) {
      showNotice(error.message || "Revisa los valores introducidos.");
    }
  }

  ["#sheetWidth", "#sheetHeight", "#margin", "#gap", "#allowRotation"].forEach((selector) => {
    $(selector).addEventListener("input", invalidateLayout);
    $(selector).addEventListener("change", invalidateLayout);
  });

  loadSamples();
  fetch("/api/health")
    .then((response) => {
      if (!response.ok) throw new Error("Health check failed");
      return response.json();
    })
    .then((data) => {
      if (data.ok) {
        document.querySelector(".local-status").setAttribute("title", `Conectado a ${data.service} ${data.version}`);
      }
    })
    .catch(() => {
      showNotice("El motor local no está disponible. Inicia la aplicación desde el repositorio para calcular distribuciones.");
    });
})();
