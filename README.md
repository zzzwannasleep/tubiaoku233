# 📦 PicStoreJson（Zzzの二改Ver.）

<p align="center">
  <a href="https://round.greentea520.xyz/"><b>🚀 在线体验</b></a>　
  <a href="https://github.com/Zzzwannasleep/tubiaoku233"><b>📦 GitHub 仓库</b></a>　
  <a href="https://github.com/huangxd-/PicStoreJson"><b>🧩 原项目</b></a>
</p>

<p align="center">
  <sub>
    1️⃣ 不要肆意上传 ｜ 2️⃣ 禁止广告 ｜ 3️⃣ 请勿上传无关内容 ｜ 4️⃣ 请规范命名（重名会自动加后缀）
  </sub>
</p>

---

## ✨ 项目简介

**PicStoreJson** 是一个基于 **Python + Flask** 的轻量级 Web 应用：

- 📤 图片自助上传 → 图床（PicGo / ImgURL / PICUI）
- 🧾 自动写入 GitHub Gist 的 `icons.json`（不覆盖历史，只追加）
- 🧩 内置 **图标在线编辑器**（裁剪 / 手动抠图 / 一键上传）
- 🤖 支持 **AI 抠图**：默认双通道（Clipdrop + remove.bg）自动均衡；可选「自定义AI（密码解锁）」模式

---

## ✅ 功能清单

### 上传页
- 单张上传（手动命名）
- 批量上传（自动使用文件名作为名称）
- 自动重名处理：`name` → `name1 / name2 / ...`

### 编辑页（/editor）
- 裁剪（固定 1:1，拖动裁剪框，框住哪里裁哪里）
- 手动抠图（橡皮擦擦背景，透明导出）
- 导出：方形 PNG / 圆形 PNG（透明圆形遮罩）
- 一键上传到图标库（走同一个 `/api/upload`）
- 背景：点击空白背景切换下一张（随机二次元背景）

### AI 抠图
- **默认AI（无需密码）**：Clipdrop + remove.bg 自动均衡负载，失败自动切换另一家
- **自定义AI（可选，模式2）**：需要先输入密码解锁（后端下发 HttpOnly Cookie，防止前端盗 key）

---

## 📄 JSON 数据结构示例

```json
{
  "name": "Forward icon self-service upload",
  "description": "by huangxd-，图标自助上传",
  "icons": [
    { "name": "TVB", "url": "https://img.picgo.net/2025/07/12/example.png" }
  ]
}
```

---

## 📂 项目结构

```bash
project/
├── api/
│   └── index.py
├── static/
│   ├── css/
│   │   ├── style.css
│   │   └── editor.css
│   ├── js/
│   │   ├── script.js
│   │   └── editor.js
│   └── favicon.png
├── templates/
│   ├── index.html
│   └── editor.html
├── requirements.txt
└── vercel.json
```

---

## 🚀 一键部署（Vercel）

1) Fork 本项目到你的 GitHub  
2) 点击下面按钮创建 Vercel 项目并填环境变量  

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/Zzzwannasleep/tubiaoku233&env=GIST_ID,GITHUB_USER,GITHUB_TOKEN,UPLOAD_SERVICE,PICGO_API_KEY,IMGURL_API_UID,IMGURL_API_TOKEN,IMGURL_ALBUM_ID,PICUI_TOKEN,PICUI_PERMISSION,PICUI_STRATEGY_ID,PICUI_ALBUM_ID,PICUI_EXPIRED_AT,CLIPDROP_API_KEY,REMOVEBG_API_KEY,FLASK_SECRET_KEY,CUSTOM_AI_ENABLED,CUSTOM_AI_PASSWORD,CUSTOM_AI_URL,CUSTOM_AI_FILE_FIELD,CUSTOM_AI_API_KEY,CUSTOM_AI_AUTH_HEADER,CUSTOM_AI_AUTH_PREFIX&envDescription=API%20Keys%20and%20GitHub%20Gist%20config&project-name=tubiaoku233&repo-name=tubiaoku233)

> 说明：Deploy 按钮只能「预设变量名」，不能预设变量值；值需要你在 Vercel 里自己填写。

---

## 🧰 环境变量说明

### GitHub Gist（必填）
| 变量名 | 说明 |
| --- | --- |
| `GIST_ID` | 你的 Gist ID（URL 最后一串） |
| `GITHUB_USER` | GitHub 用户名 |
| `GITHUB_TOKEN` | GitHub Token（classic，勾选 `gist` 权限） |

### 上传服务（选填）
| 变量名 | 说明 |
| --- | --- |
| `UPLOAD_SERVICE` | `PICGO` / `IMGURL` / `PICUI`（推荐 PICUI） |
| `PICGO_API_KEY` | PicGo API Key |
| `IMGURL_API_UID` | ImgURL UID |
| `IMGURL_API_TOKEN` | ImgURL Token |
| `IMGURL_ALBUM_ID` | ImgURL 相册 ID（可选） |
| `PICUI_TOKEN` | PICUI Token（启用 PICUI 必填） |
| `PICUI_PERMISSION` | `0` 私有 / `1` 公开（可选，默认 0） |
| `PICUI_STRATEGY_ID` `PICUI_ALBUM_ID` `PICUI_EXPIRED_AT` | PICUI 进阶参数（可选） |

### 默认 AI 抠图（可选）
| 变量名 | 说明 |
| --- | --- |
| `CLIPDROP_API_KEY` | Clipdrop key（有就填） |
| `REMOVEBG_API_KEY` | remove.bg key（有就填） |

> 两个都填会自动均衡使用；只填一个就只用那一个。

### 自定义 AI 抠图（可选，模式2：密码解锁）
| 变量名 | 说明 |
| --- | --- |
| `CUSTOM_AI_ENABLED` | `1` 开启 / 其他为关闭 |
| `CUSTOM_AI_PASSWORD` | 解锁密码（前端弹窗输入） |
| `CUSTOM_AI_URL` | 你的自定义抠图接口（需要返回透明 PNG 二进制） |
| `CUSTOM_AI_FILE_FIELD` | 上传图片字段名（默认 `image`） |
| `CUSTOM_AI_API_KEY` | 可选：自定义接口鉴权 key |
| `CUSTOM_AI_AUTH_HEADER` | 可选：鉴权 header（默认 `Authorization`） |
| `CUSTOM_AI_AUTH_PREFIX` | 可选：前缀（如 `Bearer `） |
| `FLASK_SECRET_KEY` | （必填） 用于签名 cookie（建议随机长字符串） |

---

## 🧭 使用指南

### 1) 单张上传（精确命名）
1. 在「图片名称」输入框填写名称  
2. 选择 **1 张图片**  
3. 点击「单张上传」

### 2) 批量上传（自动用文件名）
1. 选择 **多张图片**  
2. 点击「批量上传」  
3. 名称会自动取文件名（去扩展名）

### 3) 编辑器（裁剪 / 抠图 / 一键上传）
1. 打开：`/editor`  
2. 导入图片  
3. 裁剪模式：拖动裁剪框（固定 1:1）  
4. 手动抠图：用橡皮擦擦背景（透明）  
5. 导出或一键上传到图标库

### 4) AI 抠图（默认 / 自定义）
- 默认AI：点击「默认AI抠图」即可  
- 自定义AI：先点「解锁自定义AI」输入密码 → 再点「自定义AI抠图」

---

## 🔒 安全说明
- 不存储用户图片
- 不记录用户信息
- 图片直传图床
- 仅修改你自己的 Gist JSON
- 自定义AI采用「密码解锁 + HttpOnly cookie」，前端 JS 读不到 cookie 内容，降低被盗刷风险

---

## 🐛 常见问题

### 1) JSON 没更新？
Gist 在本地/浏览器可能有缓存：请清缓存或稍等再刷新。

### 2) 上传失败？
- 检查 Vercel 环境变量是否正确
- GitHub Token 是否勾选 `gist`
- 你选的图床服务（PicGo/ImgURL/PICUI）Key/Token 是否有效
- 打开 Vercel Logs 看报错信息

### 3) AI 抠图按钮报错？
- 默认AI：确认填了 `CLIPDROP_API_KEY` 或 `REMOVEBG_API_KEY`
- 自定义AI：确认 `CUSTOM_AI_ENABLED=1`，并配置 `CUSTOM_AI_PASSWORD`、`CUSTOM_AI_URL`

---

## 🙏 致谢
- [PicGo](https://www.picgo.net/) / [ImgURL](https://www.imgurl.org) / [PICUI](https://picui.cn/) 提供图床服务
- [CropperJS](https://github.com/fengyuanchen/cropperjs) 提供裁剪能力
