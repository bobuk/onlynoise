import pymongo


class MongoDB:
    def __init__(self, url: str = "mongodb://localhost:27017"):
        self.url = url
        self.client: pymongo.MongoClient = None

    def __enter__(self):
        if self.client is None:
            self.connect()
        return self.client.ondb

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # self.client.close()

    def connect(self):
        self.client = pymongo.MongoClient(self.url)


DB = MongoDB()
