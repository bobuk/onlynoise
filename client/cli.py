import os
import json
import httpx
from sseclient import SSEClient
from rich.console import Console
from rich.table import Table

con = Console()

URL = "http://localhost:8080/v1/"

class Config:
    def __init__(self, path=".client.json"):
        self.path = path
        try:
            with open(path) as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {}

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        with open(self.path, 'w') as f:
            json.dump(self.config, f)

C = Config()

def wait_messages():
    con.print("Messages", style="bold blue")
    try:
        for msg in SSEClient(URL + f"realtime/accounts/{C.get('account_id')}/messages"):
            con.print(msg.data)
    except KeyboardInterrupt:
        con.print("... stopped", style="bold red")


def list_postboxes():
    con.print("list of boxes:", style="bold blue")
    req = httpx.get(URL + f"accounts/{C.get('account_id')}/postboxes").json()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("id", justify="left", style="green")
    table.add_column("date", justify="right", style="")
    for box in req["postboxes"]:
        table.add_row(str(box["postbox_id"]), str(box["created_at"]))
    con.print(table)

def messages_table():
    req = httpx.get(URL + f"accounts/{C.get('account_id')}/messages").json()
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("id", justify="left", style="green")
    table.add_column("subject", justify="left", style="green")
    table.add_column("body", justify="right", style="")
    table.add_column("postbox", justify="right", style="blue")

    print(req["messages"])
    for msg in req["messages"]:
        table.add_row(msg['id'], msg["subject"], msg["body"], msg["postbox_id"])
    con.print(table)

def main():
    if not C.get("account_id"):
        con.print("Setting up client...", style="bold red")
        req = httpx.post(URL + "accounts/").json()
        C.set("account_id", req["account_id"])
        con.print(f"Account ID: {req['account_id']}", style="bold green")
    con.print("Client ready", style="bold green")
    while True:
        try:
            cmd = input(">> ")
        except KeyboardInterrupt:
            cmd = "exit"
        except EOFError:
            cmd = "exit"
        if cmd == "exit":
            con.print("Bye!", style="bold red")
            break
        elif cmd.startswith("M"):
            wait_messages()
        elif cmd.startswith("m"):
            messages_table()
        elif cmd.startswith("boxes"):
            list_postboxes()
        elif cmd.startswith("create box"):
            req = httpx.post(URL + f"accounts/{C.get('account_id')}/postboxes").json()
            con.print(f"Created box {req['postbox_id']}", style="bold green")
        elif cmd.startswith("create subscription"):
            cmd = cmd.strip().split(" ")
            if len(cmd) == 2:
                req = httpx.post(URL + f"subscriptions/", json={"account_id": C.get('account_id')})
            else:
                req = httpx.post(URL + f"subscriptions/", json={"account_id": C.get('account_id'), "unique_id": cmd[2]})
            if req.status_code < 300:
                req = req.json()
                con.print(f"Created subscription {req['subscription_id']} with id: {req['unique_id']}", style="bold green")
            else:
                con.print(f"Error: {req.json()}", style="bold red")
        elif cmd.startswith("subscribe "):
            cmd = cmd.strip().split(" ", 4)[1:]
            if len(cmd) != 3 or cmd[1] not in ["to", ">"]:
                con.print("Usage: subscribe <postbox_id> to <unique_id>", style="bold red")
                continue
            req = httpx.post(URL + f"subscriptions/{cmd[2]}", json={"postbox_id": cmd[0]})
            if 300 > req.status_code >= 200:
                con.print("Subscribed", style="bold green")
            else:
                con.print("Error", style="bold red")
                con.print(req.json())
        elif cmd.startswith("delete box"):
            box_id = cmd.split(" ")[2].strip()
            req = httpx.delete(URL + f"postboxes/{box_id}")
            if req.status_code == 200:
                con.print(f"Deleted box {box_id}", style="bold green")
            else:
                con.print(f"Error: {req.json()}", style="bold red")
        elif cmd.startswith("send to "):
            cmd = cmd.split(" ",3)[2:]
            if len(cmd) != 2:
                con.print("Usage: send to <box_id | @sub_id> <message>", style="bold red")
                continue
            box_id, message = cmd
            if box_id.startswith("@"):
                req = httpx.post(URL + f"subscriptions/{box_id[1:]}/messages", json={"body": message})
            else:
                req = httpx.post(URL + f"postboxes/{box_id}/messages", json={"body": message})
            if req.status_code in [200, 201, 202]:
                con.print(f"Sent to {box_id}", style="bold green")
            else:
                con.print(f"Error: {req.json()}", style="bold red")



if __name__ == "__main__":
    main()