import os, shutil, time, sys
import migrate_dbs

ELASTIC_INITS_FOLDER = "data-inits"
DOCKER_FILE = "Dockerfile-data-init"
DOCKER_REPO = "beeldbank-dev"
ELASTIC_IMAGE = "geosolutions/elasticsearch-plugins"
ELASTIC_CONTAINER_NAME = "beeldbank-elastic-init"
ELASTIC_DATA = "$(pwd)/data/elastic"
STORAGE_PROVIDER_IMAGE = "beeldbank-dev/storageprovider:latest"
STORAGE_PROVIDER_CONTAINER_NAME = "storageprovider-init"
STORAGE_PROVIDER_DATA = "$(pwd)/data/storageprovider"
STORAGE_PROVIDER_DATA_MAP = "{}:/beeldbank_store".format(STORAGE_PROVIDER_DATA)
REDIS_IMAGE = "redis"
REDIS_CONTAINER_NAME = "beeldbank-redis-init"


def start_redis():
    try:
        stop_and_clean_redis_container()
    except:
        print("issue cleaning docker images, let's proceed and see...")

    _exec_command("docker run -p '6379:6379' --name {} {} &".format(REDIS_CONTAINER_NAME, REDIS_IMAGE))

    print("wait for redis to boot (10 secs)")
    time.sleep(10)
    _exec_command("docker run "
                  "--link {}:redis "
                  "beeldbank-dev/redis-checker:latest"
                  .format(REDIS_CONTAINER_NAME))


def start_storage_provider():
    try:
        stop_and_clean_storage_provider_container()
    except:
        print("issue cleaning docker images, let's proceed and see...")

    _exec_command("mkdir -p {}".format(STORAGE_PROVIDER_DATA))
    _exec_command("docker run -p '6544:6544' --name {} -v {} {}&"
                  .format(STORAGE_PROVIDER_CONTAINER_NAME, STORAGE_PROVIDER_DATA_MAP, STORAGE_PROVIDER_IMAGE))

    print("wait for storage provider to boot (10 secs)")
    time.sleep(10)
    _exec_command("docker run "
                  "--link {}:storageprovider "
                  "beeldbank-dev/storageprovider-checker:latest"
                  .format(STORAGE_PROVIDER_CONTAINER_NAME))


def start_elastic():
    # make sure it starts clean
    try:
        stop_and_clean_elastic_container()
    except:
        print("issue cleaning docker images, let's proceed and see...")

    _exec_command("docker run -p '9200:9200' --name {} -v {}:/usr/share/elasticsearch/data {} &".format(ELASTIC_CONTAINER_NAME,
                                                                                ELASTIC_DATA,
                                                                                ELASTIC_IMAGE))

    print("wait for elastic to boot (10 secs)")
    time.sleep(10)
    _exec_command("docker run "
                  "--link {}:elastic "
                  "beeldbank-dev/elastic-checker:latest"
                  .format(ELASTIC_CONTAINER_NAME))


def run_data_init():
    try:
        start_storage_provider()
        start_elastic()
        start_redis()
        migrate_dbs.start_db()

        print('all services ready, moving on...')

        current_path = os.path.dirname(os.path.realpath(__file__))
        migrations_dir = os.path.join(current_path, ELASTIC_INITS_FOLDER)

        assert os.path.isdir(migrations_dir), "Expected a data-inits dir..."

        migrations_folders = _listdir_not_hidden(migrations_dir)

        for folder in migrations_folders:
            docker_files_root_dir = os.path.join(migrations_dir, folder)
            sub_docker_files_folders = _listdir_not_hidden(docker_files_root_dir)

            if not sub_docker_files_folders:
                _build_and_run_data_init(current_path, folder)
                continue

            for sub_folder in sub_docker_files_folders:
                _build_and_run_data_init(current_path, os.path.join(folder, sub_folder))
                os.chdir(current_path)

    finally:
        stop_and_clean_redis_container()
        stop_and_clean_elastic_container()
        stop_and_clean_storage_provider_container()
        migrate_dbs.stop_and_clean_db_container()

def _build_and_run_data_init(current_path, folder):
    target_folder = os.path.join(current_path, folder)
    docker_file = os.path.join(current_path, ELASTIC_INITS_FOLDER, folder, DOCKER_FILE)

    print("copy docker file ")
    shutil.copy(docker_file, target_folder)

    print("changing dir to {}".format(target_folder))
    os.chdir(target_folder)

    # do the docker build
    try:
        print("starting initialization")
        print("building image")
        docker_image_repo = "{}/{}-migration:latest".format(DOCKER_REPO, folder)
        command = "docker build " \
                  "-f {} " \
                  "-t {} .".format(DOCKER_FILE, docker_image_repo)
        _exec_command(command)

        print("fire container and run migration")
        run_command = "docker run " \
                      "--link {}:elastic " \
                      "--link {}:postgres  " \
                      "--link {}:storageprovider " \
                      "--link {}:redis "\
            .format(ELASTIC_CONTAINER_NAME,
                    migrate_dbs.DATABASE_CONTAINER_NAME,
                    STORAGE_PROVIDER_CONTAINER_NAME,
                    REDIS_CONTAINER_NAME)
        run_command += "{}".format(docker_image_repo)

        print("firing!")
        print(run_command)

        _exec_command(run_command)

    finally:
        # clean up
        print("changing dir back to {}".format(current_path))
        os.remove(os.path.join(target_folder, DOCKER_FILE))

        os.chdir(current_path)


def stop_and_clean_storage_provider_container():
    _exec_command("docker stop {}; docker rm {}".format(STORAGE_PROVIDER_CONTAINER_NAME,
                                                        STORAGE_PROVIDER_CONTAINER_NAME))


def stop_and_clean_elastic_container():
    _exec_command("docker stop {}; docker rm {}".format(ELASTIC_CONTAINER_NAME, ELASTIC_CONTAINER_NAME))


def stop_and_clean_redis_container():
    _exec_command("docker stop {}; docker rm {}".format(REDIS_CONTAINER_NAME, REDIS_CONTAINER_NAME))


def _exec_command(command):
    result = os.system(command)
    if not result == 0:
        raise Exception("Error while executing command {}".format(command))


def _listdir_not_hidden(path):
    folders  = []
    for f in os.listdir(path):
        if not f.startswith('.') and os.path.isdir(os.path.join(path, f)):
            folders.append(f)
    return folders


if __name__ == '__main__':
    run_data_init()
