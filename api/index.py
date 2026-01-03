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
PICGO_API_KEY = os.getenv("PICGO_API_KEY", "YOUR_API_KEY")  # 替换为你的 PicGo API 密钥

# ImgURL API 配置
IMGURL_API_URL = "https://www.imgurl.org/api/v2/upload"  # 默认为 imgurl.org，可替换为其他服务商
IMGURL_API_UID = os.getenv("IMGURL_API_UID", "YOUR_API_UID")  # 从环境变量获取 ImgURL UID
IMGURL_API_TOKEN = os.getenv("IMGURL_API_TOKEN", "YOUR_API_TOKEN")  # 从环境变量获取 ImgURL TOKEN

# PICUI API 配置（强制 Token 模式）
PICUI_UPLOAD_URL = "https://picui.cn/api/v1/upload"
PICUI_TOKEN = os.getenv("PICUI_TOKEN", "").strip()

# GitHub Gist 配置
GIST_ID = os.getenv("GIST_ID", "YOUR_GIST_ID")  # 替换为你的 Gist ID
GITHUB_USER = os.getenv("GITHUB_USER", "YOUR_GITHUB_USER")  # 替换为你的 GITHUB USER
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "YOUR_GITHUB_TOKEN")  # 替换为你的 GitHub Token
GIST_FILE_NAME = "icons.json"

# 如果选择 PICUI 作为上传服务，则强制要求配置 Token
if os.getenv("UPLOAD_SERVICE", "").upper() == "PICUI" and not PICUI_TOKEN:
    print("警告：UPLOAD_SERVICE=PICUI 但 PICUI_TOKEN 未配置，PICUI 上传将全部失败（强制 Token 模式）")


@app.route("/")
def home():
    return render_template("index.html", github_user=GITHUB_USER, gist_id=GIST_ID)
@app.route("/editor")
def editor():
    return render_template("editor.html", custom_ai_enabled=CUSTOM_AI_ENABLED)


@app.route("/api/upload", methods=["POST"])
def upload_image():
    try:
        # ✅ 兼容单图 & 多图：前端字段名仍然用 source
        images = request.files.getlist("source")
        if not images:
            return jsonify({"error": "缺少图片"}), 400

        # name：单张上传时可以从表单拿；批量时可为空（用文件名）
        raw_name = (request.form.get("name") or "").strip()

        upload_service = os.getenv("UPLOAD_SERVICE", "PICGO").upper()

        results = []
        for image in images:
            # 跳过空项（有些浏览器会塞空文件）
            if not image or not getattr(image, "filename", ""):
                continue

            # ✅ 自动读取文件名作为 name（去扩展名）
            auto_name = os.path.splitext(image.filename)[0]
            name = raw_name or auto_name

            # 根据环境变量决定使用哪个上传接口
            if upload_service == "IMGURL":
                image_url = upload_to_imgurl(image)

            elif upload_service == "PICUI":
                if not os.getenv("PICUI_TOKEN", "").strip():
                    results.append({
                        "ok": False,
                        "name": name,
                        "error": "PICUI_TOKEN 未配置，已启用强制 Token 上传模式"
                    })
                    continue
                image_url = upload_to_picui(image)

            else:
                image_url = upload_to_picgo(image)

            if not image_url:
                results.append({
                    "ok": False,
                    "name": name,
                    "error": f"图片上传失败（{upload_service}）"
                })
                continue

            gist_result = update_gist(name, image_url)
            if not gist_result["success"]:
                results.append({
                    "ok": False,
                    "name": name,
                    "error": gist_result["error"]
                })
                continue

            results.append({
                "ok": True,
                "name": gist_result["name"],  # 这里可能被 get_unique_name 改名
                "url": image_url
            })

        if not results:
            return jsonify({"error": "没有可用的图片文件"}), 400

        # ✅ 保持你原来的单图返回格式，避免前端兼容问题
        if len(results) == 1:
            r = results[0]
            if r["ok"]:
                return jsonify({"success": True, "name": r["name"]}), 200
            return jsonify({"error": r["error"]}), 400

        # ✅ 批量返回
        return jsonify({"success": True, "results": results}), 200

    except Exception as e:
        return jsonify({"error": "服务器错误", "details": str(e)}), 500

        # 更新 Gist
        gist_result = update_gist(name, image_url)
        if not gist_result["success"]:
            return jsonify({"error": gist_result["error"]}), 400

        return jsonify({"success": True, "name": gist_result["name"]}), 200

    except Exception as e:
        return jsonify({"error": "服务器错误", "details": str(e)}), 500


def upload_to_picgo(image):
    """使用 PicGo API 上传图片"""
    form_data = {"source": (image.filename, image.stream, image.mimetype)}
    headers = {"X-API-Key": PICGO_API_KEY}
    upload_response = requests.post(PICGO_API_URL, files=form_data, headers=headers)

    if upload_response.status_code != 200:
        if upload_response.headers.get('Content-Type', '').startswith('application/json'):
            try:
                err = upload_response.json()
                print(f"PicGo 上传失败: {err}")
            except:
                print(f"PicGo 上传失败: {upload_response.text}")
        else:
            print(f"PicGo 上传失败: {upload_response.text}")
        return None

    upload_data = upload_response.json()

    # 更稳的写法：避免 image 为 None 导致 .get 报错
    img = upload_data.get("image") or {}
    return img.get("url")


def upload_to_imgurl(image):
    """使用 ImgURL API 上传图片"""
    # 准备表单数据
    form_data = {
        'uid': IMGURL_API_UID,
        'token': IMGURL_API_TOKEN
    }

    # 如果设置了相册ID，也添加进去
    album_id = os.getenv("IMGURL_ALBUM_ID")
    if album_id and str(album_id).strip():
        form_data['album_id'] = album_id

    files = {
        'file': (image.filename, image.stream, image.mimetype)
    }

    print(f"准备上传数据: uid={IMGURL_API_UID}, token={'*' * len(IMGURL_API_TOKEN)}, album_id={album_id}")

    try:
        upload_response = requests.post(IMGURL_API_URL, data=form_data, files=files)

        print(f"HTTP状态码: {upload_response.status_code}")
        print(f"响应内容: {upload_response.text}")

        if upload_response.status_code != 200:
            print(f"ImgURL 上传失败，HTTP状态码: {upload_response.status_code}, 响应: {upload_response.text}")
            return None

        try:
            upload_data = upload_response.json()

            if isinstance(upload_data, dict) and 'code' in upload_data:
                if upload_data['code'] != 200:
                    print(f"ImgURL API 返回错误: {upload_data}")
                    return None

            if 'data' in upload_data and 'url' in upload_data['data']:
                return upload_data['data']['url']
            elif 'url' in upload_data:
                return upload_data['url']
            else:
                print(f"ImgURL 响应格式异常: {upload_data}")
                return None

        except ValueError:
            print(f"ImgURL 响应不是有效的 JSON: {upload_response.text}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"请求异常: {str(e)}")
        return None


def upload_to_picui(image):
    """
    使用 PICUI API 上传图片（强制 Token 模式）
    - 必须带 Authorization: Bearer <token>
    - 上传接口: POST https://picui.cn/api/v1/upload
    - 文件字段名: file
    - 返回: data.links.url
    """
    token = os.getenv("PICUI_TOKEN", "").strip()
    if not token:
        # 理论上外层已经拦截，这里再加一次保险
        raise Exception("PICUI_TOKEN 为空：已启用强制 Token 上传模式，无法游客上传")

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }

    files = {
        "file": (image.filename, image.stream, image.mimetype)
    }

    # 可选参数：默认私有 permission=0（你也可在环境变量设置为1公开）
    data = {}

    permission = os.getenv("PICUI_PERMISSION", "0").strip()
    if permission:
        data["permission"] = permission

    strategy_id = os.getenv("PICUI_STRATEGY_ID", "").strip()
    if strategy_id:
        data["strategy_id"] = strategy_id

    album_id = os.getenv("PICUI_ALBUM_ID", "").strip()
    if album_id:
        data["album_id"] = album_id

    expired_at = os.getenv("PICUI_EXPIRED_AT", "").strip()
    if expired_at:
        data["expired_at"] = expired_at

    try:
        r = requests.post(PICUI_UPLOAD_URL, headers=headers, data=data, files=files, timeout=30)

        if r.status_code in (401, 403):
            print("PICUI token 无效或权限不足：", r.status_code, r.text)
            return None

        if r.status_code != 200:
            print("PICUI 上传失败：", r.status_code, r.text)
            return None

        j = r.json()

        # PICUI 成功一般 status=True
        if not j.get("status"):
            print("PICUI 业务错误：", j)
            return None

        # 正确解析图片 URL：data.links.url
        return j["data"]["links"]["url"]

    except Exception as e:
        print("PICUI 异常：", e)
        return None


def get_unique_name(name, json_content):
    """
    检查 json_content["icons"] 中是否已有名称为 name 的图标，
    如果存在重复，则在名称后缀添加递增数字，直到不重复。
    返回唯一名称。
    """
    icons = json_content.get("icons", [])
    if not any(icon["name"] == name for icon in icons):
        return name

    base_name = name
    counter = 1
    while any(icon["name"] == f"{base_name}{counter}" for icon in icons):
        counter += 1
    return f"{base_name}{counter}"


def update_gist(name, url):
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # 获取当前 Gist 内容
    gist_response = requests.get(f"https://api.github.com/gists/{GIST_ID}", headers=headers)
    if gist_response.status_code != 200:
        return {"success": False, "error": "无法获取 Gist"}

    gist_data = gist_response.json()
    try:
        json_content = json.loads(gist_data["files"][GIST_FILE_NAME]["content"])
    except:
        json_content = {"name": "Forward", "description": "", "icons": []}

    name = get_unique_name(name, json_content)

    # 添加新图标
    json_content["icons"].append({"name": name, "url": url})

    # 更新 Gist
    update_response = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers=headers,
        json={"files": {GIST_FILE_NAME: {"content": json.dumps(json_content, indent=2)}}},
    )

    if update_response.status_code != 200:
        return {"success": False, "error": "无法更新 Gist"}

    return {"success": True, "name": name}



# ===================== AI 抠图（默认双通道负载 + 自定义模式2） =====================

def call_clipdrop_remove_bg(image):
    api_key = os.getenv("CLIPDROP_API_KEY", "").strip()
    if not api_key:
        raise Exception("CLIPDROP_API_KEY 未配置")

    url = "https://clipdrop-api.co/remove-background/v1"
    headers = {"x-api-key": api_key}
    files = {"image_file": (image.filename, image.stream, image.mimetype)}
    r = requests.post(url, headers=headers, files=files, timeout=60)
    if r.status_code != 200:
        raise Exception(f"Clipdrop 抠图失败: HTTP {r.status_code} {r.text[:200]}")
    return r.content  # png bytes


def call_removebg_remove_bg(image):
    api_key = os.getenv("REMOVEBG_API_KEY", "").strip()
    if not api_key:
        raise Exception("REMOVEBG_API_KEY 未配置")

    url = "https://api.remove.bg/v1.0/removebg"
    headers = {"X-Api-Key": api_key}
    files = {"image_file": (image.filename, image.stream, image.mimetype)}
    data = {"size": "auto"}
    r = requests.post(url, headers=headers, files=files, data=data, timeout=60)
    if r.status_code != 200:
        raise Exception(f"remove.bg 抠图失败: HTTP {r.status_code} {r.text[:200]}")
    return r.content  # png bytes


def call_custom_remove_bg(image):
    """
    自定义AI转发（模式2：必须先解锁）：
    约定：CUSTOM_AI_URL 返回透明 PNG（二进制，Content-Type: image/png）。
    如果你的自定义服务返回 JSON(url)，需要改这里的解析逻辑。
    """
    custom_url = os.getenv("CUSTOM_AI_URL", "").strip()
    if not custom_url:
        raise Exception("CUSTOM_AI_URL 未配置")

    file_field = os.getenv("CUSTOM_AI_FILE_FIELD", "image").strip() or "image"
    auth_header = os.getenv("CUSTOM_AI_AUTH_HEADER", "Authorization").strip() or "Authorization"
    auth_prefix = os.getenv("CUSTOM_AI_AUTH_PREFIX", "").strip()
    api_key = os.getenv("CUSTOM_AI_API_KEY", "").strip()

    headers = {}
    if api_key:
        headers[auth_header] = f"{auth_prefix}{api_key}"

    files = {file_field: (image.filename, image.stream, image.mimetype)}
    r = requests.post(custom_url, headers=headers, files=files, timeout=90)
    if r.status_code != 200:
        raise Exception(f"自定义AI抠图失败: HTTP {r.status_code} {r.text[:200]}")
    return r.content


@app.route("/api/ai_cutout", methods=["POST"])
def api_ai_cutout_default():
    """
    默认AI抠图：Clipdrop + remove.bg 负载均衡（随机优先）+ 失败自动降级
    """
    try:
        image = request.files.get("image")
        if not image:
            return jsonify({"error": "缺少图片字段 image"}), 400

        candidates = []
        if os.getenv("CLIPDROP_API_KEY", "").strip():
            candidates.append(("clipdrop", call_clipdrop_remove_bg))
        if os.getenv("REMOVEBG_API_KEY", "").strip():
            candidates.append(("removebg", call_removebg_remove_bg))

        if not candidates:
            return jsonify({"error": "默认AI未配置：请设置 CLIPDROP_API_KEY 或 REMOVEBG_API_KEY"}), 500

        random.shuffle(candidates)

        last_err = None
        for name, fn in candidates:
            try:
                png_bytes = fn(image)
                return Response(png_bytes, mimetype="image/png")
            except Exception as e:
                last_err = f"{name}: {str(e)}"
                continue

        return jsonify({"error": "默认AI抠图失败", "details": last_err}), 500

    except Exception as e:
        return jsonify({"error": "默认AI抠图失败", "details": str(e)}), 500


@app.route("/api/ai/custom/auth", methods=["POST"])
def api_custom_ai_auth():
    """模式2：输入密码 -> 下发 HttpOnly Cookie，解锁自定义AI抠图"""
    if not CUSTOM_AI_ENABLED:
        return jsonify({"error": "自定义AI未启用（CUSTOM_AI_ENABLED!=1）"}), 403

    if not CUSTOM_AI_PASSWORD:
        return jsonify({"error": "CUSTOM_AI_PASSWORD 未配置"}), 500

    data = request.get_json(silent=True) or {}
    pwd = (data.get("password") or "").strip()

    if pwd != CUSTOM_AI_PASSWORD:
        return jsonify({"error": "密码错误"}), 403

    token = serializer.dumps({"ok": 1})
    resp = jsonify({"success": True})
    # 1天有效；HttpOnly 防止 JS 读取；secure=True 适配 https
    resp.set_cookie("custom_ai_auth", token, max_age=86400, httponly=True, samesite="Lax", secure=True)
    return resp


def _check_custom_ai_cookie():
    raw = request.cookies.get("custom_ai_auth", "")
    if not raw:
        return False
    try:
        serializer.loads(raw, max_age=86400)
        return True
    except (BadSignature, SignatureExpired):
        return False


@app.route("/api/ai_cutout_custom", methods=["POST"])
def api_ai_cutout_custom():
    """自定义AI抠图：必须先 /api/ai/custom/auth 解锁"""
    try:
        if not CUSTOM_AI_ENABLED:
            return jsonify({"error": "自定义AI未启用（CUSTOM_AI_ENABLED!=1）"}), 403

        if not _check_custom_ai_cookie():
            return jsonify({"error": "未解锁自定义AI：请先输入密码解锁"}), 403

        image = request.files.get("image")
        if not image:
            return jsonify({"error": "缺少图片字段 image"}), 400

        png_bytes = call_custom_remove_bg(image)
        return Response(png_bytes, mimetype="image/png")

    except Exception as e:
        return jsonify({"error": "自定义AI抠图失败", "details": str(e)}), 500


if __name__ == "__main__":
    app.run()
