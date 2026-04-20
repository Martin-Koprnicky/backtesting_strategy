import sys
import shutil
import hashlib
import time
import logging

logging.basicConfig(filename=f"{sys.argv[5]}", filemode="w", level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

from pathlib import Path

def sync_up(source_path: Path, replica_path: Path) -> None:
    source = [path.relative_to(source_path) for path in source_path.rglob('*')]
    replica = [path.relative_to(replica_path) for path in replica_path.rglob('*')]
    files_to_remove = [path for path in replica if path not in set(source)]
    already_handled = set()

    def add_paths_to_already_handled_set(path: Path, current_list: list) -> None:
        paths_to_handle = [p for p in set(current_list) if str(p).startswith(str(path))]
        for p in paths_to_handle:
            already_handled.add(p)
            logger.debug(f"Path added to already handled set: {p}")

    for path in files_to_remove:
        logger.debug(f"Path in files to handle: {path}")
        if path in already_handled:
            logger.debug(f"Path already handled: {path}")
            continue
        try:
            if (replica_path/path).is_dir():
                shutil.rmtree(replica_path / path)
                logger.info(f"Directory removed. path: {replica_path/path}")
                add_paths_to_already_handled_set(path, files_to_remove)

            else:
                (replica_path/path).unlink()
                logger.info(f"File removed. path: {replica_path/path}")
        except FileNotFoundError as e:
            logging.exception("FileNotFoundError")

    already_handled.clear()

    striped_replica = [path.relative_to(replica_path) for path in replica_path.rglob('*')]
    files_to_check = [path for path in striped_replica if not (replica_path/path).is_dir()]
    files_to_add = [path for path in source if path not in set(striped_replica)]

    for path in files_to_check:
        checking_hashes = dict()

        for kind in [source_path, replica_path]:
            with open(kind/path, "rb") as f:
                checking_hashes[kind] = hashlib.md5(f.read()).hexdigest()

        if checking_hashes[source_path] != checking_hashes[replica_path]:
            logger.debug(f"replica hash != source hash, path: {path}")
            files_to_add.append(path)
            logger.info(f"Path added to files to add. path: {path}")

    for path in files_to_add:
        try:
            if (source_path/path).is_dir():
                shutil.copytree(src=source_path / path, dst=replica_path / path)
                logger.info(f"Directory copied from: {source_path / path} to: {replica_path / path}")
                add_paths_to_already_handled_set(path, files_to_add)

            else:
                shutil.copy2(src=source_path / path, dst=replica_path / path)
                logger.info(f"File copied from: {source_path / path} to: {replica_path / path}")

        except FileNotFoundError as e:
            logging.exception("FileNotFoundError")

def main():
    source_path = Path(sys.argv[1])
    replica_path = Path(sys.argv[2])
    interval_between_synchronizations = int(sys.argv[3])
    amount_of_synchronizations = int(sys.argv[4])

    logger.info("Logger started")
    for n in range(amount_of_synchronizations):
        logger.info(f"Sync number {n+1} started")
        sync_up(source_path, replica_path)
        logger.info(f"Sync number {n+1} was successful")
        if n+1 == amount_of_synchronizations:
            break
        time.sleep(interval_between_synchronizations)

    logger.info("Logger stopped")

if __name__ == "__main__":
    main()