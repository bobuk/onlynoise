import json
import os

import httpx

URL = "https://onlynoise.rubedo.cloud/v1/" if os.environ.get("RELEASE") else "http://localhost:8080/v1/"


def request(method: str, appendix: str, **kwargs) -> dict:
    res = httpx.request(method, URL + appendix, **kwargs, follow_redirects=True)
    if res.status_code > 399:
        try:
            js = res.json()
        except json.decoder.JSONDecodeError:
            js = res.text
        return {"error": res.status_code, "message": js}
    return res.json()


def GET(appendix: str, **kwargs):
    return request(method="GET", appendix=appendix, **kwargs)


def POST(appendix: str, **kwargs):
    return request(method="POST", appendix=appendix, json=kwargs)


class OnlyClient:
    def __init__(self, path=".client.json"):
        self.path = path
        self.config = {}
        self.load_config()

    def create_account(self):
        res = POST("accounts")
        self.set("account_id", res["account_id"])
        return self

    def get_account(self, account_id=None):
        if account_id is None:
            account_id = self.get("account_id")
        req = GET(f"accounts/{account_id}")
        return req

    def create_subscription(self, unique_id, meta=None):
        account_id = self.get("account_id")
        req = POST("subscriptions/", account_id=account_id, unique_id=unique_id, meta=meta if meta else {})
        return req

    def subscribe_to(self, unique_id):
        account_id = self.get("account_id")
        req = POST(f"accounts/{account_id}/subscriptions", unique_id=unique_id)
        return req

    def publish_message(self, unique_id, **kwargs):
        account_id = self.get("account_id")
        req = POST(f"accounts/{account_id}/subscriptions/{unique_id}", **kwargs)
        return req

    def get_messages(self):
        account_id = self.get("account_id")
        req = GET(f"accounts/{account_id}/messages")
        return req

    def load_config(self):
        try:
            with open(self.path) as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}
        return self

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        if self.path != '-':
            with open(self.path, 'w') as f:
                json.dump(self.config, f)
        return self


def main():
    from rich.console import Console
    console = Console()
    console.log("Client started")
    client = OnlyClient().load_config()
    # console.log(client.create_account())
    console.log("Client ID: ", client.get("account_id"))
    console.log("Client account: ", client.get_account())
    # console.log("Client subscription: ", client.create_subscription("test"))
    # console.log("Client subscription: ", client.subscribe_to("test"))


if __name__ == "__main__":
    main()
