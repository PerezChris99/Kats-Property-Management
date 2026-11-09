"""Abuse-resistance and scope regression tests aligned with OWASP API risks."""
import json
import re
from app import create_app
from app.extensions import db
from conftest import auth_client, create_user, csrf

PUBLIC_GET={
    "/api/v1/public/landing-content",
    "/api/v1/public/legal/<slug>",
}
PUBLIC_POST={
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/recover",
    "/api/v1/auth/complete-token",
    "/api/v1/public/contact-requests",
}

def test_protected_get_endpoints_require_authentication(app):
    client=app.test_client()
    inspected=0
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/") or "GET" not in rule.methods:
            continue
        if rule.rule in PUBLIC_GET:
            continue
        path=re.sub(r"<(?:[^:>]+:)?[^>]+>", "00000000-0000-4000-8000-000000000000",rule.rule)
        response=client.get(path)
        assert response.status_code==401,(rule.rule,response.status_code,response.json)
        inspected+=1
    assert inspected>=25

def test_protected_mutation_endpoints_require_authentication(app):
    client=app.test_client()
    inspected=0
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/"):
            continue
        path=re.sub(r"<(?:[^:>]+:)?[^>]+>",
                    "00000000-0000-4000-8000-000000000000",rule.rule)
        for method in ("POST","PUT","PATCH","DELETE"):
            if method not in rule.methods:
                continue
            if method=="POST" and rule.rule in PUBLIC_POST:
                continue
            response=client.open(path,method=method,json={})
            assert response.status_code==401,(rule.rule,method,response.status_code,response.json)
            inspected+=1
    assert inspected>=30


def test_api_rejects_invalid_origin_media_type_and_oversized_json(app):
    client=app.test_client()
    hostile=client.post("/api/v1/auth/login",json={"email":"test@kats.test","password":"a"},
                       headers={"Origin":"https://attacker.example"})
    assert hostile.status_code==403
    assert "Access-Control-Allow-Origin" not in hostile.headers
    wrong_type=client.post("/api/v1/auth/login",data="email=a&password=b",
                           content_type="application/x-www-form-urlencoded")
    assert wrong_type.status_code==415
    too_large=client.post("/api/v1/auth/login",
        data=json.dumps({"email":"x@kats.test","password":"a"*270000}),
        content_type="application/json")
    assert too_large.status_code==413
    result=client.get("/api/v1/auth/me")
    assert result.status_code==401
    assert result.headers["Cache-Control"]=="no-store"
    assert result.headers["X-Content-Type-Options"]=="nosniff"
    assert result.headers["X-Frame-Options"]=="DENY"
    assert result.headers["Cross-Origin-Resource-Policy"]=="same-origin"
    assert "default-src 'none'" in result.headers["Content-Security-Policy"]
    assert "X-Request-ID" in result.headers
    assert "SECRET_KEY" not in result.get_data(as_text=True)

def test_text_controls_pagination_and_json_not_executable_html(app):
    owner=create_user("edge-owner@kats.test","OWNER")
    client=auth_client(app,owner)
    for name in ("Injected\x00text","Abc\u202ehttp://malicious"):
        response=client.post("/api/v1/properties",headers=csrf(client),
            json={"name":name,"address":"Kampala","district":"Kampala"})
        assert response.status_code==400
    good=client.post("/api/v1/properties",headers=csrf(client),
        json={"name":"<script>alert(1)</script>","address":"Kampala","district":"Kampala"})
    assert good.status_code==201
    result=client.get("/api/v1/properties")
    assert result.status_code==200
    assert result.is_json
    assert "text/html" not in result.content_type
    assert result.json["items"][0]["name"]=="<script>alert(1)</script>"
    for suffix in ("?page=0","?page=201","?page_size=101","?page=abc","?page=200&page_size=100"):
        page=client.get("/api/v1/properties"+suffix)
        assert page.status_code==400,(suffix,page.status_code,page.json)
    no_count=client.get("/api/v1/properties?include_total=0&page=1&page_size=10")
    assert no_count.status_code==200
    assert no_count.json["total"] is None

def test_login_limit_blocks_repeated_guessing():
    app=create_app({
        "TESTING":True,"SQLALCHEMY_DATABASE_URI":"sqlite:///:memory:",
        "JWT_COOKIE_SECURE":False,"RATELIMIT_ENABLED":True,
        "RATELIMIT_STORAGE_URI":"memory://","RATELIMIT_HEADERS_ENABLED":True,
    })
    with app.app_context():
        db.create_all()
        client=app.test_client()
        statuses=[]
        for _ in range(12):
            r=client.post("/api/v1/auth/login",json={
                "email":"invalid@kats.test","password":"InvalidPassword123!"})
            statuses.append(r.status_code)
        assert 429 in statuses, statuses
        db.session.remove()
        db.drop_all()
