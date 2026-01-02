/* ========== 工具函数 ========== */
function filenameToName(filename) {
  return filename.split(/[\\/]/).pop().replace(/\.[^.]+$/, "");
}

function prettySize(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  const kb = bytes / 1024;
  if (kb < 1024) return `${kb.toFixed(1)} KB`;
  return `${(kb / 1024).toFixed(1)} MB`;
}

function hidePreview() {
  const previewBox = document.getElementById("batchPreview");
  const previewList = document.getElementById("previewList");
  if (previewBox && previewList) {
    previewList.innerHTML = "";
    previewBox.style.display = "none";
  }
}

function hideProgress() {
  const progressWrap = document.getElementById("progressWrap");
  const progressFill = document.getElementById("progressFill");
  const progressText = document.getElementById("progressText");
  const progressFile = document.getElementById("progressFile");
  if (progressWrap) progressWrap.style.display = "none";
  if (progressFill) progressFill.style.width = "0%";
  if (progressText) progressText.textContent = "0/0";
  if (progressFile) progressFile.textContent = "";
}

/* ========== 单张上传 ========== */
async function uploadSingle() {
  const nameInput = document.getElementById("name");
  const imageInput = document.getElementById("image");
  const messageDiv = document.getElementById("message");
  const resultList = document.getElementById("resultList");

  if (!nameInput || !imageInput || !messageDiv) return;
  if (resultList) resultList.innerHTML = "";

  const name = nameInput.value.trim();
  const file = imageInput.files[0];

  if (!name || !file) {
    messageDiv.textContent = "请输入名称并选择图片！";
    return;
  }

  const formData = new FormData();
  formData.append("source", file);
  formData.append("name", name);

  messageDiv.textContent = "正在上传...";
  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json().catch(() => ({}));

    if (response.ok && data.success) {
      messageDiv.textContent = `上传成功！名称: ${data.name}`;
      if (resultList) resultList.innerHTML = `<li>✅ <b>${data.name}</b></li>`;
      nameInput.value = "";
      imageInput.value = "";
      hidePreview();
      hideProgress();
    } else {
      messageDiv.textContent = `错误：${data.error || `HTTP ${response.status}`}`;
    }
  } catch (error) {
    messageDiv.textContent = `上传失败：${error.message}`;
  }
}

/* ========== 批量上传（带进度条） ========== */
async function uploadBatch() {
  const imageInput = document.getElementById("image");
  const messageDiv = document.getElementById("message");
  const resultList = document.getElementById("resultList");

  // 进度条元素
  const progressWrap = document.getElementById("progressWrap");
  const progressText = document.getElementById("progressText");
  const progressFile = document.getElementById("progressFile");
  const progressFill = document.getElementById("progressFill");

  if (!imageInput || !messageDiv) return;
  if (resultList) resultList.innerHTML = "";

  const files = Array.from(imageInput.files || []);
  if (files.length === 0) {
    messageDiv.textContent = "请选择图片（可多选）！";
    return;
  }
  if (files.length === 1) {
    messageDiv.textContent = "批量上传请至少选择 2 张图片（或用单张上传）。";
    return;
  }

  function addResult(ok, name, info) {
    if (!resultList) return;
    const li = document.createElement("li");
    li.innerHTML = ok
      ? `✅ <b>${name}</b> ${info ? `→ <a href="${info}" target="_blank">${info}</a>` : ""}`
      : `❌ <b>${name}</b> → ${info || "失败"}`;
    resultList.appendChild(li);
  }

  // 显示进度条
  if (progressWrap) progressWrap.style.display = "block";
  if (progressFill) progressFill.style.width = "0%";
  if (progressText) progressText.textContent = `0/${files.length}`;
  if (progressFile) progressFile.textContent = "";

  try {
    for (let i = 0; i < files.length; i++) {
      const f = files[i];
      const name = filenameToName(f.name);

      // 更新进度（开始上传当前项）
      if (progressFile) progressFile.textContent = f.name;
      if (progressText) progressText.textContent = `${i}/${files.length}`;
      if (progressFill) progressFill.style.width = `${Math.round((i / files.length) * 100)}%`;

      const formData = new FormData();
      formData.append("source", f);
      formData.append("name", name);

      messageDiv.textContent = `批量上传中 ${i + 1}/${files.length}: ${f.name}`;

      const response = await fetch("/api/upload", {
        method: "POST",
        body: formData,
      });

      const data = await response.json().catch(() => ({}));

      if (response.ok && data.success) {
        addResult(true, data.name || name, data.url || "");
      } else {
        addResult(false, name, data.error || `HTTP ${response.status}`);
      }

      // 完成一项后更新进度
      const done = i + 1;
      if (progressText) progressText.textContent = `${done}/${files.length}`;
      if (progressFill) progressFill.style.width = `${Math.round((done / files.length) * 100)}%`;
    }

    messageDiv.textContent = `批量上传完成：${files.length}/${files.length}`;
    imageInput.value = "";

    // 上传结束：停留 1 秒再隐藏进度条
    setTimeout(() => hideProgress(), 1000);
    hidePreview();
  } catch (err) {
    messageDiv.textContent = `批量上传失败：${err.message}`;
    hideProgress();
  }
}

/* ========== 批量预览：选择多张时显示将使用的名称 ========== */
(function setupBatchPreview() {
  const imageInput = document.getElementById("image");
  const previewBox = document.getElementById("batchPreview");
  const previewList = document.getElementById("previewList");

  if (!imageInput || !previewBox || !previewList) return;

  imageInput.addEventListener("change", () => {
    const files = Array.from(imageInput.files || []);
    previewList.innerHTML = "";

    if (files.length <= 1) {
      previewBox.style.display = "none";
      return;
    }

    previewBox.style.display = "block";
    for (const f of files) {
      const name = filenameToName(f.name);
      const li = document.createElement("li");
      li.innerHTML = `
        <span>🖼️ <b>${name}</b></span>
        <span class="meta">${prettySize(f.size)}</span>
      `;
      previewList.appendChild(li);
    }
  });
})();

/* ========== 随机背景（接口版） ========== */
(function () {
  const randomImageURL = "https://www.loliapi.com/acg/";

  document.body.style.backgroundImage = `
    url(${randomImageURL}),
    radial-gradient(900px 600px at 12% 18%, rgba(255,107,214,.25), transparent 60%),
    radial-gradient(800px 520px at 85% 20%, rgba(57,213,255,.20), transparent 55%),
    radial-gradient(900px 650px at 55% 92%, rgba(124,107,255,.18), transparent 60%),
    linear-gradient(135deg, #ffe9f6, #e9f1ff, #eafff7)
  `;

  document.body.style.backgroundSize = "cover";
  document.body.style.backgroundPosition = "center";
  document.body.style.backgroundRepeat = "no-repeat";
  document.body.style.backgroundAttachment = "fixed";
})();
