"""Exhaustively reject unauthenticated API reads and mutations."""
import re

PUBLIC={
 ("GET","/api/v1/public/landing-content"),
 ("GET","/api/v1/public/legal/<slug>"),
 ("POST","/api/v1/auth/login"),
 ("POST","/api/v1/auth/register"),
 ("POST","/api/v1/auth/recover"),
 ("POST","/api/v1/auth/complete-token"),
 ("POST","/api/v1/public/contact-requests"),
}

def test_protected_api_methods_fail_closed_for_anonymous(app):
    client=app.test_client()
    checked=[]
    for rule in app.url_map.iter_rules():
        if not rule.rule.startswith("/api/v1/"):
            continue
        path=re.sub(r"<(?:[^:>]+:)?[^>]+>", "00000000-0000-4000-8000-000000000000",rule.rule)
        for method in sorted(rule.methods & {"GET","POST","PUT","PATCH","DELETE"}):
            if (method,rule.rule) in PUBLIC:
                continue
            response=client.open(path,method=method)
            assert response.status_code==401,(method,rule.rule,response.status_code,response.get_json(silent=True))
            checked.append((method,rule.rule))
    assert len(checked)>=65
