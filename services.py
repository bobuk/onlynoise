class onlynoise:
    image = "docker.rubedo.cloud/onlynoise:latest"
    public = "onlynoise.rubedo.cloud @ 8080"
    watchtower = True
    envs = {"MONGO": "mongo"}


class onlynoisepush:
    image = "docker.rubedo.cloud/onlynoise-push:latest"
    envs = "MONGO=mongo"
    networks = ["public"]
    doppler = True
    watchtower = True


class mongo:
    image = "mongo:latest"
    command = "mongod --quiet"
    volumes = [
        "./db:/data/db",
        "./data/docker-entrypoint-initdb.d:/docker-entrypoint-initdb.d"]

    class envs:
        MONGO_INITDB_DATABASE = "ondb"

    networks = ["public"]
    watchtower = True
