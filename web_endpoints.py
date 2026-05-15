# ── Auth Gate API ──────────────────────────────────────────────

@app.post("/api/auth/register")
async def register(req: Request):
    import auth as auth_mod
    body = await req.json()
    username = (body.get("username") or "").strip().lower()
    password = body.get("password") or ""

    if not username or len(username) > 8:
        return JSONResponse({"error": "用户名不超过8个字符"}, status_code=400)
    if not re.match(r"^[a-zA-Z0-9]+$", username):
        return JSONResponse({"error": "用户名只能包含字母和数字"}, status_code=400)
    if len(password) < 8:
        return JSONResponse({"error": "密码不少于8个字符"}, status_code=400)

    if not getattr(req.app.state, "db_ok", False):
        return JSONResponse({"error": "数据库不可用"}, status_code=503)

    pw_hash = auth_mod.hash_password(password)
    user = await db.create_user(username, pw_hash)
    if not user:
        return JSONResponse({"error": "该用户名已被注册"}, status_code=409)

    return {"ok": True, "username": user["username"]}


@app.post("/api/auth/login")
async def login(req: Request):
    import auth as auth_mod
    body = await req.json()
    username = (body.get("username") or "").strip().lower()
    password = body.get("password") or ""

    if not username or not password:
        return JSONResponse({"error": "请输入用户名和密码"}, status_code=400)

    user = await db.get_user_by_username(username)
    if not user:
        return JSONResponse({"error": "未检索到该账号，请注册"}, status_code=404)

    if not auth_mod.check_password(password, user["password_hash"]):
        return JSONResponse({"error": "密码错误"}, status_code=401)

    # Generate session token, store hash in DB, invalidating any other session
    raw_token, token_hash = auth_mod.generate_session_token()
    await db.set_user_token(username, token_hash)

    return {"ok": True, "username": user["username"], "token": raw_token}


@app.post("/api/auth/captcha")
async def get_captcha():
    import auth as auth_mod
    question, answer = auth_mod.generate_math_captcha()
    return JSONResponse({"question": question, "answer": answer})


@app.post("/api/auth/verify")
async def verify_token(req: Request):
    body = await req.json()
    raw_token = (body.get("token") or "").strip()
    username = (body.get("username") or "").strip().lower()

    if not raw_token or not username:
        return {"valid": False}

    stored_hash = await db.get_user_token_hash(username)
    if not stored_hash:
        return {"valid": False}

    import hashlib
    given_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    return {"valid": given_hash == stored_hash}
