from conftest import create_user,auth_client,csrf

def test_privacy_request_visibility_and_no_automatic_deletion(app):
    owner=create_user("privacy-owner@kats.test","OWNER")
    alice=create_user("privacy-alice@kats.test","TENANT")
    bob=create_user("privacy-bob@kats.test","TENANT")
    ac=auth_client(app,alice)
    bc=auth_client(app,bob)
    oc=auth_client(app,owner)
    payload={"kind":"ERASURE","details":"Please review any old identification records"}
    submitted=ac.post("/api/v1/privacy/requests",headers=csrf(ac),json=payload)
    assert submitted.status_code==201,submitted.json
    record_id=submitted.json["request"]["id"]
    assert len(ac.get("/api/v1/privacy/requests").json["items"])==1
    assert len(bc.get("/api/v1/privacy/requests").json["items"])==0
    assert bc.post("/api/v1/privacy/requests/"+record_id+"/review",
                   headers=csrf(bc),json={"status":"COMPLETED","decision_notes":"No"}).status_code==403
    reject=oc.post("/api/v1/privacy/requests/"+record_id+"/review",headers=csrf(oc),
        json={"status":"COMPLETED","decision_notes":"Reviewed"})
    assert reject.status_code==409
    reviewed=oc.post("/api/v1/privacy/requests/"+record_id+"/review",headers=csrf(oc),
        json={"status":"IN_REVIEW","decision_notes":"Awaiting lawful retention review"})
    assert reviewed.status_code==200
    assert ac.get("/api/v1/privacy/my-data").status_code==200
