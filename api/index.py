from flask import Flask, request, jsonify, render_template, Response
import requests
import os
import json
import random
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(__file__), '../static'),
            template_folder=os.path.join(os.path.dirname(__file__), '../templates'))

# ===== Custom AI (模式2：解锁后使用) =====
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_secret_change_me')
serializer = URLSafeTimedSerializer(app.secret_key)
CUSTOM_AI_ENABLED = os.getenv('CUSTOM_AI_ENABLED', '0').strip() == '1'
CUSTOM_AI_PASSWORD = os.getenv('CUSTOM_AI_PASSWORD', '').strip()

# PicGo API 配置
PICGO_API_URL = "https://www.picgo.net/api/1/upload"
PICGO_API_KEY = os.getenv("PICGO_API_KEY", "YOUR_API_KEY")

# ImgURL API 配置
IMGURL_API_URL = "https://www.imgurl.org/api/v2/upload"
IMGURL_API_UID = os.getenv("IMGURL_API_UID", "YOUR_IMGURL_UID")
IMGURL_API_TOKEN = os.getenv("IMGURL_API_TOKEN", "YOUR_IMGURL_TOKEN")

# PICUI API 配置
PICUI_UPLOAD_URL = "https://picui.cn/api/v1/upload"
PICUI_TOKEN = os.getenv("PICUI_TOKEN", "").strip()

# GitHub Gist 配置
GIST_ID = os.getenv("GIST_ID", "YOUR_GIST_ID")
GITHUB_USER = os.getenv("GITHUB_USER", "YOUR_GITHUB_USER")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")
GIST_FILE_NAME = "icons.json"

# 警告检查
if os.getenv("UPLOAD_SERVICE", "").upper() == "PICUI" and not PICUI_TOKEN:
    print("警告：UPLOAD_SERVICE=PICUI 但 PICUI_TOKEN 未配置，PICUI 上传将全部失败（强制 Token 模式）")

# ===== Gist 读取/更新工具函数 =====

def get_gist_data():
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    r = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers, timeout=30)
    r.raise_for_status()
    return r.json()

def update_gist_data(content):
    """更新 Gist 数据（替换整个 icons.json 文件内容）"""
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {"files": {GIST_FILE_NAME: {"content": json.dumps(content, indent=2)}}}
    response = requests.patch(f"https://api.github.com/gists/{GIST_ID}", json=data, headers=headers, timeout=30)
    if response.status_code != 200:
        raise Exception(f"更新 Gist 失败：{response.text}")
    return response.json()

def get_unique_name(name, json_content):
    """名称去重逻辑"""
    icons = json_content.get("icons", [])
    if not any(icon["name"] == name for icon in icons):
        return name

    base_name = name
    counter = 1
    while any(icon["name"] == f"{base_name}{counter}" for icon in icons):
        counter += 1
    return f"{base_name}{counter}"

def batch_append_to_gist(new_items):
    """
    核心辅助函数：一次性将 new_items 列表追加到 Gist
    new_items: [{"name": "raw_name", "url": "http..."}]
    Return: 更新后的 items (包含去重后的最终名称)
    """
    try:
        # 1. 获取最新数据
        gist = get_gist_data()
        icons_raw = gist.get("files", {}).get(GIST_FILE_NAME, {}).get("content", "{}")
        content = json.loads(icons_raw) if isinstance(icons_raw, str) else icons_raw
        
        saved_chunk = []
        
        # 2. 处理去重并追加
        for item in new_items:
            final_name = get_unique_name(item["name"], content)
            content.setdefault("icons", []).append({
                "name": final_name, 
                "url": item["url"]
            })
            # 记录最终保存的信息
            saved_chunk.append({"name": final_name, "url": item["url"]})
            
        # 3. 推送更新
        update_gist_data(content)
        return saved_chunk
    except Exception as e:
        print(f"Gist 批量更新失败: {e}")
        raise e

# ===== 图片上传实现 =====

def upload_to_picgo(img):
    headers = {"X-API-Key": PICGO_API_KEY}
    files = {"source": (img.filename, img.stream, img.mimetype)}
    r = requests.post(PICGO_API_URL, files=files, headers=headers, timeout=30)
    r.raise_for_status()
    j = r.json()
    return (j.get("image") or {}).get("url", None)

def upload_to_imgurl(img):
    form = {"uid": IMGURL_API_UID, "token": IMGURL_API_TOKEN}
    files = {"file": (img.filename, img.stream, img.mimetype)}
    r = requests.post(IMGURL_API_URL, data=form, files=files, timeout=30)
    r.raise_for_status()
    j = r.json()
    if "data" in j and "url" in j["data"]:
        return j["data"]["url"]
    if "url" in j:
        return j["url"]
    return None

def upload_to_picui(image):
    token = os.getenv("PICUI_TOKEN", "").strip()
    if not token:
        raise Exception("PICUI_TOKEN 为空：已启用强制 Token 上传模式")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    files = {"file": (image.filename, image.stream, image.mimetype)}
    data = {}

    permission = os.getenv("PICUI_PERMISSION", "0").strip()
    if permission: data["permission"] = permission
    strategy_id = os.getenv("PICUI_STRATEGY_ID", "").strip()
    if strategy_id: data["strategy_id"] = strategy_id
    album_id = os.getenv("PICUI_ALBUM_ID", "").strip()
    if album_id: data["album_id"] = album_id
    expired_at = os.getenv("PICUI_EXPIRED_AT", "").strip()
    if expired_at: data["expired_at"] = expired_at

    try:
        r = requests.post(PICUI_UPLOAD_URL, headers=headers, data=data, files=files, timeout=30)
        if r.status_code != 200:
            print("PICUI 上传失败：", r.status_code, r.text)
            return None
        j = r.json()
        if not j.get("status"):
            return None
        return j["data"]["links"]["url"]
    except Exception as e:
        print("PICUI 异常：", e)
        return None

# ===================== 路由逻辑 =====================

@app.route("/")
def home():
    return render_template("index.html", github_user=GITHUB_USER, gist_id=GIST_ID)

@app.route("/editor")
def editor():
    return render_template("editor.html", custom_ai_enabled=CUSTOM_AI_ENABLED)

@app.route("/api/upload", methods=["POST"])
def upload_image():
    """
    修改后的上传接口：
    1. 单图上传：立即更新 Gist。
    2. 批量上传：每积攒 10 张图的链接，更新一次 Gist（流控）。
    3. 剩余不足 10 张：最后统一更新。
    """
    try:
        images = request.files.getlist("source")
        if not images:
            return jsonify({"error": "缺少图片"}), 400

        raw_name = (request.form.get("name") or "").strip()
        upload_service = os.getenv("UPLOAD_SERVICE", "PICGO").upper()

        final_results = []   # 最终返回给前端的所有结果
        pending_batch = []   # 待写入 Gist 的缓冲区
        
        BATCH_SIZE = 10      # 流控阈值：每10个更新一次

        for image in images:
            if not image or not getattr(image, "filename", ""):
                continue

            auto_name = os.path.splitext(image.filename)[0]
            name = raw_name or auto_name # 如果是批量，通常用 auto_name，除非前端逻辑特殊

            # --- 1. 上传图片到图床 ---
            upload_err = None
            image_url = None
            
            try:
                if upload_service == "IMGURL":
                    image_url = upload_to_imgurl(image)
                elif upload_service == "PICUI":
                    if not os.getenv("PICUI_TOKEN", "").strip():
                        upload_err = "PICUI_TOKEN 未配置"
                    else:
                        image_url = upload_to_picui(image)
                else:
                    image_url = upload_to_picgo(image)
            except Exception as e:
                upload_err = str(e)

            # --- 2. 处理上传结果 ---
            if not image_url:
                # 上传图床失败
                final_results.append({
                    "ok": False, 
                    "name": name, 
                    "error": upload_err or f"图片上传失败（{upload_service}）"
                })
            else:
                # 上传成功，加入待更新队列
                pending_batch.append({"name": name, "url": image_url})

            # --- 3. 流控检查：如果缓冲区达到 10 个，立即同步到 Gist ---
            if len(pending_batch) >= BATCH_SIZE:
                try:
                    saved_items = batch_append_to_gist(pending_batch)
                    # 将成功的项加入最终结果
                    for item in saved_items:
                        final_results.append({"ok": True, "name": item["name"], "url": item["url"]})
                    # 清空缓冲区
                    pending_batch = [] 
                except Exception as e:
                    # Gist 更新这一批失败了（网络波动等），记录警告但不中断后续上传
                    # 注意：图床已经上传成功了，只是没存到 Gist
                    for item in pending_batch:
                        final_results.append({
                            "ok": True, 
                            "name": item["name"], 
                            "url": item["url"], 
                            "warning": f"图片已上传但 Gist 阶段同步失败: {str(e)}"
                        })
                    pending_batch = []

        # --- 4. 循环结束，处理剩余不足 10 个的图片 ---
        if pending_batch:
            try:
                saved_items = batch_append_to_gist(pending_batch)
                for item in saved_items:
                    final_results.append({"ok": True, "name": item["name"], "url": item["url"]})
            except Exception as e:
                for item in pending_batch:
                    final_results.append({
                        "ok": True, 
                        "name": item["name"], 
                        "url": item["url"], 
                        "warning": f"图片已上传但 Gist 最后同步失败: {str(e)}"
                    })

        # --- 5. 返回响应 ---
        if not final_results:
             return jsonify({"error": "没有处理任何文件"}), 400

        # 兼容单文件上传的旧响应格式 (可选，也可以统一返回 list)
        if len(images) == 1 and len(final_results) == 1:
            r = final_results[0]
            if r.get("ok"):
                return jsonify({"success": True, "name": r.get("name"), "url": r.get("url")}), 200
            else:
                return jsonify({"error": r.get("error")}), 400

        return jsonify({"success": True, "results": final_results}), 200

    except Exception as e:
        return jsonify({"error": "服务器内部错误", "details": str(e)}), 500


@app.route("/api/finalize_batch", methods=["POST"])
def api_finalize_batch():
    """保留接口以防万一，但现在的逻辑已经在 upload 中自动 finalize 了"""
    return jsonify({"success": True, "message": "Batch is now handled automatically in upload"}), 200

# ===================== AI 抠图相关 (保持不变) =====================

def call_clipdrop_remove_bg(image):
    api_key = os.getenv("CLIPDROP_API_KEY", "").strip()
    if not api_key: raise Exception("CLIPDROP_API_KEY 未配置")
    url = "https://clipdrop-api.co/remove-background/v1"
    headers = {"x-api-key": api_key}
    files = {"image_file": (image.filename, image.stream, image.mimetype)}
    r = requests.post(url, headers=headers, files=files, timeout=60)
    if r.status_code != 200: raise Exception(f"Clipdrop error: {r.status_code}")
    return r.content

def call_removebg_remove_bg(image):
    api_key = os.getenv("REMOVEBG_API_KEY", "").strip()
    if not api_key: raise Exception("REMOVEBG_API_KEY 未配置")
    url = "https://api.remove.bg/v1.0/removebg"
    headers = {"X-Api-Key": api_key}
    files = {"image_file": (image.filename, image.stream, image.mimetype)}
    data = {"size": "auto"}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if r.status_code != 200: raise Exception(f"Removebg error: {r.status_code}")
    return r.content

def call_custom_remove_bg(image):
    custom_url = os.getenv("CUSTOM_AI_URL", "").strip()
    if not custom_url: raise Exception("CUSTOM_AI_URL 未配置")
    file_field = os.getenv("CUSTOM_AI_FILE_FIELD", "image").strip() or "image"
    auth_header = os.getenv("CUSTOM_AI_AUTH_HEADER", "Authorization").strip() or "Authorization"
    auth_prefix = os.getenv("CUSTOM_AI_AUTH_PREFIX", "").strip()
    api_key = os.getenv("CUSTOM_AI_API_KEY", "").strip()
    headers = {}
    if api_key: headers[auth_header] = f"{auth_prefix}{api_key}"
    files = {file_field: (image.filename, image.stream, image.mimetype)}
    r = requests.post(custom_url, headers=headers, files=files, timeout=90)
    if r.status_code != 200: raise Exception(f"Custom AI error: {r.status_code}")
    return r.content

@app.route("/api/ai_cutout", methods=["POST"])
def api_ai_cutout_default():
    try:
        image = request.files.get("image")
        if not image: return jsonify({"error": "缺少图片"}), 400
        candidates = []
        if os.getenv("CLIPDROP_API_KEY", "").strip(): candidates.append(call_clipdrop_remove_bg)
        if os.getenv("REMOVEBG_API_KEY", "").strip(): candidates.append(call_removebg_remove_bg)
        if not candidates: return jsonify({"error": "默认AI未配置"}), 500
        random.shuffle(candidates)
        last_err = None
        for fn in candidates:
            try:
                return Response(fn(image), mimetype="image/png")
            except Exception as e:
                last_err = str(e)
                continue
        return jsonify({"error": "AI抠图全失败", "details": last_err}), 500
    except Exception as e:
        return jsonify({"error": "AI抠图失败", "details": str(e)}), 500

@app.route("/api/ai/custom/auth", methods=["POST"])
def api_custom_ai_auth():
    if not CUSTOM_AI_ENABLED: return jsonify({"error": "未启用"}), 403
    data = request.get_json(silent=True) or {}
    if (data.get("password") or "").strip() != CUSTOM_AI_PASSWORD: return jsonify({"error": "密码错误"}), 403
    resp = jsonify({"success": True})
    token = serializer.dumps({"ok": 1})
    resp.set_cookie("custom_ai_auth", token, max_age=86400, httponly=True, samesite="Lax", secure=True)
    return resp

def _check_custom_ai_cookie():
    raw = request.cookies.get("custom_ai_auth", "")
    try:
        serializer.loads(raw, max_age=86400)
        return True
    except: return False

@app.route("/api/ai_cutout_custom", methods=["POST"])
def api_ai_cutout_custom():
    try:
        if not CUSTOM_AI_ENABLED: return jsonify({"error": "未启用"}), 403
        if not _check_custom_ai_cookie(): return jsonify({"error": "未解锁"}), 403
        image = request.files.get("image")
        if not image: return jsonify({"error": "缺少图片"}), 400
        return Response(call_custom_remove_bg(image), mimetype="image/png")
    except Exception as e:
        return jsonify({"error": "自定义AI失败", "details": str(e)}), 500

if __name__ == "__main__":
    app.run()
