import httpx
import sys


def gen_message():
    return {
        "subject": httpx.get("https://jokesrv.rubedo.cloud").json()["content"],
        "body": httpx.get("https://jokesrv.rubedo.cloud/pirozhki").json()["content"],
    }


def main():
    if len(sys.argv) != 2:
        print("Usage: sendmessage.py <postbox_id>")
        sys.exit(1)
    msg = gen_message()
    postbox_id = sys.argv[1]
    print(httpx.post(f"http://localhost:8080/v1/postboxes/{postbox_id}/messages", json=msg))


if __name__ == '__main__':
    main()
