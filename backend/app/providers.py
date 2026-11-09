"""Backend-only MTN and Airtel collection clients.

No provider request can be triggered without explicit configuration. Production
provider profiles must be verified against the merchant's approved portal
contract; successful initiation is never payment confirmation.
"""
import base64
import os
from dataclasses import dataclass
from urllib.parse import urlparse
import httpx

ALLOWED_BASES = {
    "MTN_MOMO": {"sandbox.momodeveloper.mtn.com", "proxy.momoapi.mtn.com"},
    "AIRTEL_MONEY": {"openapiuat.airtel.africa", "openapi.airtel.africa"},
}

class ProviderError(RuntimeError):
    pass

@dataclass(frozen=True)
class VerifiedStatus:
    state: str
    transaction_id: str | None = None
    reason: str | None = None

class ProviderClient:
    name = ""
    def __init__(self):
        self.base = os.getenv(self.name + "_BASE_URL", "").rstrip("/")
        parsed = urlparse(self.base)
        if parsed.scheme != "https" or parsed.hostname not in ALLOWED_BASES[self.name] or parsed.username or parsed.password or parsed.port not in (None,443) or parsed.path not in ("","/"):
            raise ProviderError("Provider base URL must be an allowlisted HTTPS API host")
        self.client = httpx.Client(timeout=httpx.Timeout(12.0,connect=5.0),follow_redirects=False,trust_env=False)

    def request(self, method, path, *, headers=None, json=None, auth=None):
        try:
            resp = self.client.request(method, self.base + path, headers=headers, json=json, auth=auth)
        except httpx.RequestError as exc:
            raise ProviderError("Provider network request failed") from exc
        if resp.status_code in (401,403):
            raise ProviderError("Provider authentication rejected")
        if resp.status_code >= 500 or resp.status_code == 429:
            raise ProviderError("Provider temporarily unavailable")
        if resp.status_code not in (200,201,202):
            raise ProviderError("Provider rejected the request")
        if not resp.content:
            return {}
        try:
            result = resp.json()
        except ValueError as exc:
            raise ProviderError("Provider returned malformed JSON") from exc
        if not isinstance(result,dict):
            raise ProviderError("Provider returned invalid data")
        return result

class MTNClient(ProviderClient):
    name="MTN_MOMO"
    def __init__(self):
        super().__init__()
        self.api_user = os.environ.get("MTN_MOMO_API_USER")
        self.api_key = os.environ.get("MTN_MOMO_API_KEY")
        self.subscription = os.environ.get("MTN_MOMO_SUBSCRIPTION_KEY")
        self.environment = os.environ.get("MTN_MOMO_TARGET_ENVIRONMENT")
        if not all((self.api_user,self.api_key,self.subscription,self.environment)):
            raise ProviderError("MTN collection credentials not configured")

    def token(self):
        data=self.request("POST","/collection/token/",headers={
            "Ocp-Apim-Subscription-Key":self.subscription,
            "Authorization":"Basic "+base64.b64encode((self.api_user+":"+self.api_key).encode()).decode()
        })
        token=data.get("access_token")
        if not isinstance(token,str) or not token:
            raise ProviderError("MTN token missing")
        return token

    def headers(self):
        return {"Authorization":"Bearer "+self.token(),"Ocp-Apim-Subscription-Key":self.subscription,
                "X-Target-Environment":self.environment,"Content-Type":"application/json"}

    def initiate(self, reference, amount, msisdn, invoice_number):
        body={"amount":str(amount),"currency":"UGX","externalId":reference,
              "payer":{"partyIdType":"MSISDN","partyId":msisdn},
              "payerMessage":"Rent "+invoice_number,"payeeNote":"Kats rent collection"}
        headers=self.headers()
        headers["X-Reference-Id"]=reference
        self.request("POST","/collection/v1_0/requesttopay",headers=headers,json=body)

    def status(self, reference, amount):
        payload=self.request("GET","/collection/v1_0/requesttopay/"+reference,headers=self.headers())
        state=payload.get("status")
        if state=="SUCCESSFUL":
            if (str(payload.get("amount")) != str(amount)
                    or payload.get("currency") != "UGX"
                    or payload.get("externalId") != reference
                    or not isinstance(payload.get("financialTransactionId"),str)):
                return VerifiedStatus("UNVERIFIED",reason="MTN transaction fields failed reconciliation")
            return VerifiedStatus("SUCCESSFUL",transaction_id=payload["financialTransactionId"])
        if state=="FAILED":
            return VerifiedStatus("FAILED",reason="Provider marked transaction failed")
        if state=="PENDING":
            return VerifiedStatus("PENDING")
        return VerifiedStatus("UNVERIFIED",reason="Unknown MTN status")

class AirtelClient(ProviderClient):
    name="AIRTEL_MONEY"
    def __init__(self):
        super().__init__()
        self.client_id=os.environ.get("AIRTEL_MONEY_CLIENT_ID")
        self.client_secret=os.environ.get("AIRTEL_MONEY_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ProviderError("Airtel collection credentials not configured")

    def token(self):
        payload=self.request("POST","/auth/oauth2/token",json={
            "client_id":self.client_id,"client_secret":self.client_secret,
            "grant_type":"client_credentials"})
        token=payload.get("access_token")
        if not isinstance(token,str) or not token:
            raise ProviderError("Airtel token missing")
        return token

    def headers(self):
        return {"Authorization":"Bearer "+self.token(),"X-Country":"UG",
                "X-Currency":"UGX","Content-Type":"application/json"}

    def initiate(self, reference, amount, msisdn, invoice_number):
        payload={"reference":reference,"subscriber":{"country":"UG","currency":"UGX","msisdn":msisdn},
                 "transaction":{"amount":amount,"country":"UG","currency":"UGX","id":reference}}
        self.request("POST","/merchant/v1/payments/",headers=self.headers(),json=payload)

    def status(self, reference, amount):
        payload=self.request("GET","/standard/v1/payments/"+reference,headers=self.headers())
        data=payload.get("data")
        txn=data.get("transaction") if isinstance(data,dict) else None
        if not isinstance(txn,dict):
            return VerifiedStatus("UNVERIFIED",reason="Airtel status lacks transaction details")
        status=txn.get("status")
        if status in ("TIP","PENDING","TP"):
            return VerifiedStatus("PENDING")
        if status in ("TF","FAILED"):
            return VerifiedStatus("FAILED")
        if status in ("TS","SUCCESSFUL"):
            # Fail closed if amount/currency/reference are not echoed by the
            # merchant's verified Airtel profile. Never credit based on status alone.
            if str(txn.get("amount")) != str(amount) or txn.get("currency") != "UGX" or str(txn.get("id")) != reference:
                return VerifiedStatus("UNVERIFIED",reason="Airtel amount/currency/reference mismatch")
            provider_id=txn.get("airtel_money_id") or txn.get("transaction_id")
            if not isinstance(provider_id,str) or not provider_id:
                return VerifiedStatus("UNVERIFIED",reason="Missing Airtel settlement identifier")
            return VerifiedStatus("SUCCESSFUL",transaction_id=provider_id)
        return VerifiedStatus("UNVERIFIED",reason="Unknown Airtel status")

def provider(name):
    if name=="MTN_MOMO":
        return MTNClient()
    if name=="AIRTEL_MONEY":
        return AirtelClient()
    raise ProviderError("Unsupported provider")
