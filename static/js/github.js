function el(id) {
  return document.getElementById(id);
}

function addResult(ok, name, urlOrErr) {
  const list = el("resultList");
  if (!list) return;
  const li = document.createElement("li");

  if (ok) {
    const url = urlOrErr || "";
    li.innerHTML = url
      ? `✅ <b>${name}</b> → <a href="${url}" target="_blank">${url}</a>`
      : `✅ <b>${name}</b>`;
  } else {
    li.innerHTML = `❌ <b>${name}</b> → ${urlOrErr || "失败"}`;
  }

  list.appendChild(li);
}

let currentFolder = "square";

function setFolder(folder) {
  currentFolder = folder || "square";

  document.querySelectorAll(".folder-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.folder === currentFolder);
  });

  const current = el("folderCurrent");
  if (current) {
    const base = (current.dataset.base || "").trim() || "images";
    current.textContent = `当前：${base}/${currentFolder}`;
  }
}

async function uploadToGithub() {
  const message = el("message");
  const nameInput = el("name");
  const imageInput = el("image");
  const list = el("resultList");

  if (list) list.innerHTML = "";

  const files = Array.from(imageInput?.files || []);
  if (!files.length) {
    if (message) message.textContent = "请选择图片（支持多选）";
    return;
  }

  const manualName = (nameInput?.value || "").trim();

  const fd = new FormData();
  for (const f of files) fd.append("source", f);

  // 后端 name 是“全局字段”，多选时让后端自动用文件名
  if (files.length === 1 && manualName) {
    fd.append("name", manualName);
  } else {
    fd.append("name", "");
  }

  fd.append("github_folder", currentFolder);

  if (message) message.textContent = "正在上传到 GitHub...";

  try {
    const res = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await res.json().catch(() => ({}));

    if (!res.ok || !data.success) {
      if (message) message.textContent = `错误：${data.error || `HTTP ${res.status}`}`;
      return;
    }

    const results = Array.isArray(data.results) ? data.results : null;
    if (results) {
      for (const r of results) {
        addResult(!!r.ok, r.name || "-", r.ok ? (r.url || "") : (r.error || "失败"));
      }
      if (message) message.textContent = `上传完成：${results.filter((x) => x && x.ok).length}/${results.length}`;
    } else {
      addResult(true, data.name || manualName || "-", data.url || "");
      if (message) message.textContent = "上传成功";
    }

    if (nameInput) nameInput.value = "";
    if (imageInput) imageInput.value = "";
  } catch (e) {
    if (message) message.textContent = `上传失败：${e.message}`;
  }
}

// 二次元随机背景（接口版）
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

window.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".folder-btn").forEach((btn) => {
    btn.addEventListener("click", () => setFolder(btn.dataset.folder));
  });
  el("btnUpload")?.addEventListener("click", uploadToGithub);
});
