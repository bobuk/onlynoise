import logging
import os, pymongo
from mongodb import DB
import tempfile, time
from pyapns_client import APNSClient, IOSPayloadAlert, IOSPayload, IOSNotification, APNSDeviceException, APNSServerException, APNSProgrammingException, UnregisteredException

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class DopplerFile:
    def __enter__(self):
        self.file = tempfile.NamedTemporaryFile()
        self.file.write(os.environ["APPLE_AUTH_KEY"].encode("utf-8"))
        self.file.seek(0)
        return self.file.name

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.file.close()

def create_client(key_file: str):
    return APNSClient(
        mode=APNSClient.MODE_PROD, #  if os.environ.get('DOPPLER_ENVIRONMENT') == 'prod' else APNSClient.MODE_DEV,
        root_cert_path=None, # '/path/to/root_cert.pem',
        auth_key_path=key_file,
        auth_key_id=os.environ["APPLE_KEY_ID"],
        team_id=os.environ["APPLE_TEAM_ID"])

def send_message(db: DB, message: dict, client: APNSClient):
    account = db.accounts.find_one({'postboxes.postbox_id': message['postbox_id']})
    if not account:
        logging.error(f"No devices found for postbox {message['postbox_id']} {message=}")
        return
    alert = {}
    if "sender" in message:
        alert["title"] = message["sender"]
        if "subject" in message:
            alert["subtitle"] = message["subject"]
        alert["body"] = message.get("body", None)
    else:
        alert["title"]=message.get("subject", None)
        alert["body"]=message.get("body", None)

    payload = IOSPayload(alert=IOSPayloadAlert(**alert))
    notification = IOSNotification(payload=payload, topic='com.isnifer.balalaika')

    for device in account['devices']:
        logging.info(f"Sending message {message=} to device {device=}")
        device_token = device['device_id'].split(':')[-1] if ":" in device['device_id'] else device['device_id']
        try:
            client.push(notification=notification, device_token=device_token)
        except UnregisteredException as e:
            logging.error(f"Device {device_token} not registered")
        except APNSDeviceException as e:
            logging.error(f"Device {device_token} error {e.args}")
        except APNSServerException as e:
            logging.error(f"Server error {e.args}")
        except APNSProgrammingException as e:
            logging.error(f"Programming error {e.args}")
        except Exception as e:
            logging.error(f"Unknown error {e.args}")
        finally:
            logging.info(f"Message sent to device {device_token=}")
    db.messages.update_one({'_id': message['_id']}, {'$set': {'is_sent': True}})


def main():
    logging.info("Starting")
    with DopplerFile() as key_file:
        client = create_client(key_file)
        logging.info("Created client")
        while True:
            with DB as db:
                logging.info("DB finding")
                cursor = db.messages.find({'is_sent': False, 'is_deleted': False},
                                          cursor_type=pymongo.CursorType.TAILABLE_AWAIT).limit(1)
                logging.info("messages found")
                while cursor.alive:
                    for message in cursor:
                        logging.info(f"message found {message=}")
                        send_message(db, message, client)
                        time.sleep(1)

if __name__ == "__main__":
    main()
