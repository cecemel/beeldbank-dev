import os, shutil, time

CWD = os.getcwd()
MIGRATIONS_FOLDER = "db-migrations"
ALEMBIC_FILE = "alembic-custom.ini"
DOCKER_FILE = "Dockerfile-migration"

DOCKER_REPO = "beeldbank-dev"
DATABASE_IMAGE = "beeldbank-dev/postgres:latest"
DATABASE_CONTAINER_NAME = "beeldbank-migration-db"

DATABASE_DATA = "{}/data/postgres".format(CWD)
DATABASE_DUMP = "db.dump"
POSTGRES_USER = "postgres"
POSTGRES_PASSWORD = "postgres"


def start_db():
    # make sure it starts clean
    try:
        stop_and_clean_db_container()
    except:
        print("issue cleaning docker images, let's proceed and see...")

    _exec_command("docker run -p 5432:5432 --name {} -v {}:/var/lib/postgresql/data {} &".format(DATABASE_CONTAINER_NAME,
                                                                        DATABASE_DATA,
                                                                        DATABASE_IMAGE))
    print("wait for migration db to boot (10 secs)")
    time.sleep(10)
    _exec_command("docker run --link {}:postgres beeldbank-dev/postgres-checker:latest".format(DATABASE_CONTAINER_NAME))


def run_migrations():
    try:
        start_db()

        current_path = os.path.dirname(os.path.realpath(__file__))
        migrations_dir = os.path.join(current_path, MIGRATIONS_FOLDER)

        assert os.path.isdir(migrations_dir), "Expected a db-migrations dir..."

        migrations_folders = _listdir_not_hidden(migrations_dir)

        for folder in migrations_folders:
            docker_files_root_dir = os.path.join(migrations_dir, folder)
            sub_docker_files_folders = _listdir_not_hidden(docker_files_root_dir)

            if not sub_docker_files_folders:
                _build_and_run_migration(current_path, folder)
                continue

            for sub_folder in sub_docker_files_folders:
                _build_and_run_migration(current_path, os.path.join(folder, sub_folder))
                os.chdir(current_path)

    finally:
        stop_and_clean_db_container()


def _build_and_run_migration(current_path, folder):
    target_folder = os.path.join(current_path, folder)
    alembic_file = os.path.join(current_path, MIGRATIONS_FOLDER, folder, ALEMBIC_FILE)


    print("copy file {} to {}".format(alembic_file, target_folder))
    shutil.copy(alembic_file, target_folder)

    docker_file = os.path.join(current_path, MIGRATIONS_FOLDER, folder, DOCKER_FILE)

    print("copy docker file ")
    shutil.copy(docker_file, target_folder)

    print("changing dir to {}".format(target_folder))
    os.chdir(target_folder)

    try:
        print("starting migration")
        print("building image")
        docker_image_repo = "{}/{}-migration:latest".format(DOCKER_REPO, folder)
        _exec_command("docker build -f {} -t {} .".format(DOCKER_FILE, docker_image_repo))

        print("fire container and run migration")
        print("RUNNING {}".format(docker_image_repo))
        _exec_command("docker run --link {}:postgres {}".format(DATABASE_CONTAINER_NAME, docker_image_repo))
        print('done')

    finally:
        # clean up
        print("changing dir back to {}".format(current_path))
        os.remove(os.path.join(target_folder, ALEMBIC_FILE))
        os.remove(os.path.join(target_folder, DOCKER_FILE))
        os.chdir(current_path)


def stop_and_clean_db_container():
    _exec_command("docker stop {}; docker rm {}".format(DATABASE_CONTAINER_NAME, DATABASE_CONTAINER_NAME))


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
    run_migrations()
