let currentImageURL = null;
let originalFilenameBase = "icon";

/* Cropper */
let cropper = null;

/* Cutout (native canvas erase) */
let cutCanvas = null;
let cutCtx = null;
let cutImg = null;              // Image()
let cutIsDrawing = false;
let cutBrushSize = 25;
let cutHistory = [];            // dataURL stack (max 30)

/* Utils */
const el = (id) => document.getElementById(id);

function showOnly(which) {
  el("emptyWrap").style.display = which === "empty" ? "flex" : "none";
  el("cropWrap").style.display = which === "crop" ? "flex" : "none";
  el("cutoutWrap").style.display = which === "cutout" ? "flex" : "none";
}

function setExportPreview(blob) {
  const url = URL.createObjectURL(blob);
  el("exportImg").src = url;
  el("exportWrap").style.display = "block";
}

function clearExportPreview() {
  el("exportWrap").style.display = "none";
  el("exportImg").src = "";
}

function filenameToName(filename) {
  return filename.split(/[\\/]/).pop().replace(/\.[^.]+$/, "");
}

/* ========== Cropper ========== */

function destroyCropper() {
  if (cropper) {
    cropper.destroy();
    cropper = null;
  }
}

function initCropper(imgEl) {
  destroyCropper();

  cropper = new Cropper(imgEl, {
    aspectRatio: 1,
    viewMode: 1,
    autoCrop: true,
    autoCropArea: 0.65,

    cropBoxMovable: true,
    cropBoxResizable: true,

    // 更像“框选裁剪”
    dragMode: "none",

    guides: true,
    center: true,
    highlight: true,
    background: false,

    zoomOnWheel: true,
    zoomable: true,

    rotatable: false,
    scalable: false,
    movable: true,
  });
}

/* 裁剪工具按钮 */
function cropBoxCenter() {
  if (!cropper) return;
  const data = cropper.getData(true);
  const imageData = cropper.getImageData();
  const newX = (imageData.naturalWidth - data.width) / 2;
  const newY = (imageData.naturalHeight - data.height) / 2;
  cropper.setData({ x: newX, y: newY, width: data.width, height: data.height });
}

function cropBoxMax() {
  if (!cropper) return;
  cropper.reset();
  cropper.setAspectRatio(1);
  // 让裁剪框大一点（会被 cropper 自动约束）
  cropper.setCropBoxData({ width: 420, height: 420 });
}

function zoomIn() {
  if (!cropper) return;
  cropper.zoom(0.08);
}

function zoomOut() {
  if (!cropper) return;
  cropper.zoom(-0.08);
}

function viewReset() {
  if (!cropper) return;
  cropper.reset();
}

/* ========== Native Cutout (Eraser) ========== */

function initCutoutCanvas(imgURL) {
  cutCanvas = el("cutoutCanvas");
  const wrap = el("cutoutWrap");

  const rect = wrap.getBoundingClientRect();
  const w = Math.max(320, Math.floor(rect.width || wrap.clientWidth || 320));
  const h = Math.max(420, Math.floor(rect.height || wrap.clientHeight || 420));

  cutCanvas.width = w;
  cutCanvas.height = h;

  cutCtx = cutCanvas.getContext("2d", { willReadFrequently: true });
  cutCtx.clearRect(0, 0, w, h);

  // 加载图片
  cutImg = new Image();
  cutImg.crossOrigin = "anonymous";
  cutImg.onload = () => {
    // 画到画布中心（contain）
    cutCtx.clearRect(0, 0, w, h);
    cutCtx.globalCompositeOperation = "source-over";

    const scale = Math.min(w / cutImg.width, h / cutImg.height);
    const dw = cutImg.width * scale;
    const dh = cutImg.height * scale;
    const dx = (w - dw) / 2;
    const dy = (h - dh) / 2;

    cutCtx.drawImage(cutImg, dx, dy, dw, dh);

    // 初始化历史（用于撤销）
    cutHistory = [cutCanvas.toDataURL("image/png")];
  };
  cutImg.src = imgURL;

  bindCutoutEvents();
}

function bindCutoutEvents() {
  if (!cutCanvas) return;

  // 防止重复绑定：先清理（用替换 handler 的方式）
  cutCanvas.onpointerdown = null;
  cutCanvas.onpointermove = null;
  window.onpointerup = null;

  cutCanvas.onpointerdown = (e) => {
    if (!cutCtx) return;
    cutIsDrawing = true;
    cutCanvas.setPointerCapture?.(e.pointerId);
    eraseAtEvent(e);
  };

  cutCanvas.onpointermove = (e) => {
    if (!cutIsDrawing) return;
    eraseAtEvent(e);
  };

  window.onpointerup = () => {
    if (!cutIsDrawing) return;
    cutIsDrawing = false;

    // 结束一次绘制，保存历史
    if (cutCanvas) {
      cutHistory.push(cutCanvas.toDataURL("image/png"));
      if (cutHistory.length > 30) cutHistory.shift();
    }
  };
}

function eraseAtEvent(e) {
  const rect = cutCanvas.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (cutCanvas.width / rect.width);
  const y = (e.clientY - rect.top) * (cutCanvas.height / rect.height);

  cutCtx.save();
  cutCtx.globalCompositeOperation = "destination-out"; // ✅ 擦除
  cutCtx.beginPath();
  cutCtx.arc(x, y, cutBrushSize / 2, 0, Math.PI * 2);
  cutCtx.fill();
  cutCtx.restore();
}

function updateBrushSizeUI() {
  const v = Number(el("brushSize").value || 25);
  el("brushSizeText").textContent = String(v);
  cutBrushSize = v;
}

function undoOneStep() {
  if (!cutCanvas || cutHistory.length <= 1) return;
  cutHistory.pop();
  const prev = cutHistory[cutHistory.length - 1];

  const img = new Image();
  img.onload = () => {
    cutCtx.clearRect(0, 0, cutCanvas.width, cutCanvas.height);
    cutCtx.globalCompositeOperation = "source-over";
    cutCtx.drawImage(img, 0, 0);
  };
  img.src = prev;
}

/* ========== Load File ========== */

function loadFile(file) {
  clearExportPreview();
  el("uploadMsg").textContent = "";

  originalFilenameBase = filenameToName(file.name) || "icon";

  if (currentImageURL) URL.revokeObjectURL(currentImageURL);
  currentImageURL = URL.createObjectURL(file);

  // 默认进入裁剪
  showOnly("crop");

  const cropImg = el("cropImage");
  cropImg.onload = () => initCropper(cropImg);
  cropImg.src = currentImageURL;
}

/* ========== Export (Square / Circle 512) ========== */

function getCropCanvas512() {
  if (!cropper) return null;
  return cropper.getCroppedCanvas({
    width: 512,
    height: 512,
    imageSmoothingEnabled: true,
    imageSmoothingQuality: "high",
  });
}

function dataURLToBlob(dataURL) {
  return fetch(dataURL).then(r => r.blob());
}

function squareCanvasToCircleBlob(squareCanvas) {
  return new Promise((resolve) => {
    const size = squareCanvas.width;
    const out = document.createElement("canvas");
    out.width = size;
    out.height = size;

    const ctx = out.getContext("2d");
    ctx.clearRect(0, 0, size, size);

    ctx.save();
    ctx.beginPath();
    ctx.arc(size / 2, size / 2, size / 2, 0, Math.PI * 2);
    ctx.closePath();
    ctx.clip();
    ctx.drawImage(squareCanvas, 0, 0);
    ctx.restore();

    out.toBlob((blob) => resolve(blob), "image/png");
  });
}

async function getSquareBlobFromCurrentMode() {
  // 抠图模式：从 cutoutCanvas 导出，再缩放进 512x512
  if (cutCanvas && el("cutoutWrap").style.display !== "none") {
    const dataURL = cutCanvas.toDataURL("image/png");
    const imgBlob = await dataURLToBlob(dataURL);

    const img = new Image();
    const url = URL.createObjectURL(imgBlob);

    return await new Promise((resolve) => {
      img.onload = () => {
        const size = 512;
        const square = document.createElement("canvas");
        square.width = size;
        square.height = size;
        const ctx = square.getContext("2d");
        ctx.clearRect(0, 0, size, size);

        const scale = Math.min(size / img.width, size / img.height);
        const w = img.width * scale;
        const h = img.height * scale;
        ctx.drawImage(img, (size - w) / 2, (size - h) / 2, w, h);

        square.toBlob((b) => resolve(b), "image/png");
        URL.revokeObjectURL(url);
      };
      img.src = url;
    });
  }

  // 裁剪模式
  const c = getCropCanvas512();
  if (!c) return null;
  return await new Promise((resolve) => c.toBlob((b) => resolve(b), "image/png"));
}

async function getCircleBlobFromCurrentMode() {
  const squareBlob = await getSquareBlobFromCurrentMode();
  if (!squareBlob) return null;

  const img = new Image();
  const url = URL.createObjectURL(squareBlob);

  return await new Promise((resolve) => {
    img.onload = async () => {
      const size = 512;
      const square = document.createElement("canvas");
      square.width = size;
      square.height = size;
      const ctx = square.getContext("2d");
      ctx.clearRect(0, 0, size, size);
      ctx.drawImage(img, 0, 0, size, size);

      const circleBlob = await squareCanvasToCircleBlob(square);
      URL.revokeObjectURL(url);
      resolve(circleBlob);
    };
    img.src = url;
  });
}

async function exportSquare() {
  const b = await getSquareBlobFromCurrentMode();
  if (!b) return alert("请先导入图片，并进行裁剪/抠图后再导出");
  setExportPreview(b);
}

async function exportCircle() {
  const b = await getCircleBlobFromCurrentMode();
  if (!b) return alert("请先导入图片，并进行裁剪/抠图后再导出");
  setExportPreview(b);
}

/* ========== Upload to Library ========== */

function getUploadName() {
  const manual = (el("uploadName").value || "").trim();
  return manual || originalFilenameBase || "icon";
}

async function uploadBlobToLibrary(blob, nameBase, suffix) {
  const uploadMsg = el("uploadMsg");
  uploadMsg.textContent = "正在上传到图标库...";

  const filename = `${nameBase}${suffix}.png`;
  const file = new File([blob], filename, { type: "image/png" });

  const fd = new FormData();
  fd.append("source", file);
  fd.append("name", nameBase);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));

    if (res.ok && data.success) {
      uploadMsg.innerHTML = `✅ 上传成功！最终名称：<b>${data.name}</b>`;
    } else {
      uploadMsg.textContent = `❌ 上传失败：${data.error || `HTTP ${res.status}`}`;
    }
  } catch (e) {
    uploadMsg.textContent = `❌ 上传失败：${e.message}`;
  }
}

async function uploadSquareToLibrary() {
  const b = await getSquareBlobFromCurrentMode();
  if (!b) return alert("请先导入图片，并进行裁剪/抠图后再上传");
  const name = getUploadName();
  await uploadBlobToLibrary(b, name, "");
}

async function uploadCircleToLibrary() {
  const b = await getCircleBlobFromCurrentMode();
  if (!b) return alert("请先导入图片，并进行裁剪/抠图后再上传");
  const name = getUploadName();
  await uploadBlobToLibrary(b, name, "_circle");
}

/* ========== Mode Switch ========== */

function switchToCropMode() {
  clearExportPreview();
  el("uploadMsg").textContent = "";
  showOnly("crop");

  if (el("cropImage").src) initCropper(el("cropImage"));
}

function switchToCutoutMode() {
  clearExportPreview();
  el("uploadMsg").textContent = "";
  showOnly("cutout");
  destroyCropper();

  if (!currentImageURL) {
    showOnly("empty");
    return alert("请先导入图片");
  }

  initCutoutCanvas(currentImageURL);
}

function resetAll() {
  clearExportPreview();
  el("uploadMsg").textContent = "";
  el("uploadName").value = "";

  destroyCropper();
  el("cropImage").src = "";

  cutCanvas = null;
  cutCtx = null;
  cutImg = null;
  cutIsDrawing = false;
  cutHistory = [];

  showOnly("empty");
}

/* ========== ✅ 编辑页随机背景 + 点击切换下一张 ========== */
(function () {
  const randomImageURL = "https://www.loliapi.com/acg/";
  const body = document.body;
  if (!body.classList.contains("editor-body")) return;

  function withCacheBuster(url) {
    const join = url.includes("?") ? "&" : "?";
    return `${url}${join}t=${Date.now()}`;
  }

  function applyRandomBg() {
    const bgUrl = withCacheBuster(randomImageURL);
    body.style.backgroundImage = `
      url(${bgUrl}),
      radial-gradient(900px 600px at 12% 18%, rgba(255,107,214,.25), transparent 60%),
      radial-gradient(800px 520px at 85% 20%, rgba(57,213,255,.20), transparent 55%),
      radial-gradient(900px 650px at 55% 92%, rgba(124,107,255,.18), transparent 60%),
      linear-gradient(135deg, #ffe9f6, #e9f1ff, #eafff7)
    `;
    body.style.backgroundSize = "cover";
    body.style.backgroundPosition = "center";
    body.style.backgroundRepeat = "no-repeat";
    body.style.backgroundAttachment = "fixed";
  }

  applyRandomBg();

  document.addEventListener("click", (e) => {
    const inTopbar = e.target.closest(".editor-topbar");
    const inLayout = e.target.closest(".editor-layout");
    const inPanel = e.target.closest(".editor-panel");
    const inStage = e.target.closest(".editor-stage");
    if (inTopbar || inLayout || inPanel || inStage) return;
    applyRandomBg();
  }, { passive: true });

  document.addEventListener("click", (e) => {
    if (!e.shiftKey) return;
    applyRandomBg();
  }, { passive: true });
})();

/* ========== Bind Events ========== */

window.addEventListener("DOMContentLoaded", () => {
  showOnly("empty");

  el("fileInput").addEventListener("change", (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    loadFile(file);
  });

  el("btnModeCrop").addEventListener("click", switchToCropMode);
  el("btnModeCutout").addEventListener("click", switchToCutoutMode);

  // 裁剪工具
  el("btnCropCenter").addEventListener("click", cropBoxCenter);
  el("btnCropMax").addEventListener("click", cropBoxMax);
  el("btnZoomIn").addEventListener("click", zoomIn);
  el("btnZoomOut").addEventListener("click", zoomOut);
  el("btnViewReset").addEventListener("click", viewReset);

  // 抠图画笔
  el("brushSize").addEventListener("input", updateBrushSizeUI);
  updateBrushSizeUI();
  el("btnUndo").addEventListener("click", undoOneStep);

  // 导出
  el("btnExportSquare").addEventListener("click", exportSquare);
  el("btnExportCircle").addEventListener("click", exportCircle);

  // 上传
  el("btnUploadSquare").addEventListener("click", uploadSquareToLibrary);
  el("btnUploadCircle").addEventListener("click", uploadCircleToLibrary);

  el("btnReset").addEventListener("click", resetAll);
});
