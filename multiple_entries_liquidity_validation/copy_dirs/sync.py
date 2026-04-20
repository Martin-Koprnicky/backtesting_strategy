import logging
import sys
import shutil
import time
import hashlib
import os.path

logging.basicConfig(filename=sys.argv[5], filemode="w", format="%(asctime)s - %(levelname)s - %(message)s", level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())

from pathlib import Path

def sync(source_path: Path, replica_path: Path) -> None:

    source = [path.relative_to(source_path) for path in source_path.rglob("*")]
    replica = [path.relative_to(replica_path) for path in replica_path.rglob("*")]

    already_handled = set()

    def add_to_already_handled_set(path, path_list):
        paths_to_add = [p for p in path_list if str(p).startswith(str(path))]
        for p in paths_to_add:
            already_handled.add(p)

    files_to_remove = [path for path in replica if path not in set(source)]

    for path in files_to_remove:
        logger.debug(f"Path in files to remove: {path}")
        if path in already_handled:
            logger.debug(f"Path already handled: {path}")
            continue

        try:
            rpl_path = replica_path/path
            if (rpl_path).is_dir():
                shutil.rmtree(rpl_path)
                logger.info(f"Directory removed. path: {rpl_path}")
                add_to_already_handled_set(path, files_to_remove)
            else:
                path.unlink()
                logger.info(f"File removed. path: {rpl_path}")

        except FileNotFoundError as e:
            logger.exception(f"FileNotFoundError")

    already_handled.clear()
    replica = [path.relative_to(replica_path) for path in replica_path.rglob("*")]
    files_to_check = [path for path in replica if not (replica_path/path).is_dir()]
    files_to_add = [path for path in source if path not in set(replica)]

    for path in files_to_check:
        logger.debug(f"Path in files to check: {path}")
        hashes_to_check = set()

        for kind in [source_path, replica_path]:
            
            with open(file=f"{kind}/{path}", mode="rb") as f:
                file = f.read()
                hashes_to_check.add(hashlib.md5(file).hexdigest())
        
        if len(hashes_to_check) != 1:
            logger.debug(f"Path added to files to add: {path}")
            files_to_add.append(path)

    for path in files_to_add:
        logger.debug(f"Path in files to add: {path}")
        if path in already_handled:
            logger.debug(f"Path already handled: {path}")
            continue
        try:
            src_path = source_path/path
            rpl_path = replica_path/path
            if (src_path).is_dir():
                shutil.copytree(src=src_path, dst=rpl_path)
                logger.info(f"Directory copied from {src_path} to {rpl_path}")
                add_to_already_handled_set(path, files_to_add)
            else:
                shutil.copy(src=src_path, dst=rpl_path)
                logger.info(f"File copied from {src_path} to {rpl_path}")

        except FileNotFoundError as e:
            logger.exception(f"FileNotFoundError")

def main():
    source_path = Path(sys.argv[1])
    replica_path = Path(sys.argv[2])
    interval_between_syncs = int(sys.argv[3])
    amount_of_syncs = int(sys.argv[4])

    logger.info("Logging started.")

    if not source_path.exists():
        print("Error: source file does not exists")
        return

    if not replica_path.exists():
        Path.mkdir(self=replica_path, parents=True, exist_ok=True)

    for n in range(amount_of_syncs):
        logger.info(f"Round number of synchronization: {n+1}")
        sync(source_path, replica_path)
        if n+1 == amount_of_syncs:
            break
        time.sleep(interval_between_syncs)

    logger.info("Logging stopped.")


if __name__ == "__main__":
    main()