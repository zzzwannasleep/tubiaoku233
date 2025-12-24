async function uploadImage() {
  const nameInput = document.getElementById("name");
  const imageInput = document.getElementById("image");
  const messageDiv = document.getElementById("message");

  if (!nameInput.value || !imageInput.files[0]) {
    messageDiv.textContent = "请输入名称并选择图片！";
    return;
  }

  const formData = new FormData();
  formData.append("source", imageInput.files[0]);
  formData.append("name", nameInput.value);

  messageDiv.textContent = "正在上传...";
  try {
    const response = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });

    const data = await response.json();
    if (response.ok) {
      messageDiv.textContent = `上传成功！名称: ${data.name}`;
      nameInput.value = "";
      imageInput.value = "";
    } else {
      messageDiv.textContent = `错误：${data.error}`;
    }
  } catch (error) {
    messageDiv.textContent = `上传失败：${error.message}`;
  }
}
/* ===== 随机背景（接口版）===== */
(function () {

  // 👇👇👇 把你的「随机图片 URL」填在这里
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
