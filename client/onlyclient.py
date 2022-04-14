import json
import os

import httpx

URL = "https://onlynoise.rubedo.cloud/v1/" if os.environ.get("RELEASE") else "http://localhost:8080/v1/"


class OnlyClient:
    def __init__(self, path=".client.json"):
        self.path = path
        self.config = {}
        self.load_config()

    def create_account(self):
        req = httpx.post(URL + "accounts").json()
        self.set("account_id", req["account_id"])
        return req

    def get_account(self, account_id=None):
        if account_id is None:
            account_id = self.get("account_id")
        req = httpx.get(URL + f"accounts/{account_id}").json()
        return req

    def create_subscription(self, unique_id):
        account_id = self.get("account_id")
        req = httpx.post(URL + f"subscriptions/", json={"account_id": account_id, "unique_id": unique_id}).json()
        return req

    def subscribe_to(self, unique_id):
        account_id = self.get("account_id")
        req = httpx.post(URL + f"accounts/{account_id}/subscriptions", json={"unique_id": unique_id}).json()
        return req

    def publish_message(self, unique_id, message):
        pass

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
        with open(self.path, 'w') as f:
            json.dump(self.config, f)


def main():
    from rich.console import Console
    console = Console()
    console.log("Client started")
    client = OnlyClient().load_config()
    # console.log(client.create_account())
    console.log("Client ID: ", client.get("account_id"))
    console.log("Client account: ", client.get_account())
    #console.log("Client subscription: ", client.create_subscription("test"))
    #console.log("Client subscription: ", client.subscribe_to("test"))


if __name__ == "__main__":
    main()
