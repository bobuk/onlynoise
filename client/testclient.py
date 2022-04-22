from onlyclient import OnlyClient
from rich.console import Console

console = Console()

clients = []


def create_test_clients():
    global clients
    for i in range(0, 3):
        client = OnlyClient(path='-').create_account()
        clients.append(client)
        console.log(f"Subscriber {i} created")


def create_channels():
    global clients
    client = OnlyClient(path='-').create_account()
    console.log("Subscriber created")
    console.log("Client ID: ", client.get("account_id"))
    console.log("Client account: ", client.get_account())
    console.log("Create subscription test: ", client.create_subscription("test"))
    chan1 = client

    client = OnlyClient(path='-').create_account()
    console.log("Subscriber created")
    console.log("Client ID: ", client.get("account_id"))
    console.log("Client account: ", client.get_account())
    test = client.create_subscription("test")
    if "error" not in test:
        raise "what? test is exists already!"
    console.log("Create subscription rss ", client.create_subscription("rss"))
    console.log("Create subscription rss2 ", client.create_subscription("rss2"))
    chan2 = client
    console.log(f"RSS client: {chan2.get_account()}")
    create_test_clients()

    clients[0].subscribe_to("test")
    clients[1].subscribe_to("test")
    clients[1].subscribe_to("rss")
    res = clients[1].subscribe_to("rss")
    if "error" not in res:
        print(res)
        raise Exception("what? rss is subscribed already!")
    clients[2].subscribe_to("rss")

    console.log("clients subscribed to test channels")
    console.log(f"RSS client: {chan2.get_account()}")

    console.log(chan1.publish_message("test", body="test message"))
    console.log(chan1.publish_message("rss", body="rss message"))
    console.log(chan2.publish_message("rss", body="rss message"))
    console.log(chan2.publish_message("rss2", body="2ss message"))

    mess = clients[1].get_messages()["messages"]
    console.log(mess)
    assert mess[0]["body"] == "test message"
    assert mess[1]["body"] == "rss message"

    mess = clients[2].get_messages()["messages"]
    console.log(mess)
    assert mess[0]["body"] == "rss message"



if __name__ == "__main__":
    create_channels()
