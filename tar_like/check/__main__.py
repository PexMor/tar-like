#!/usr/bin/python

import argparse
import logging
import os
import os.path
import re

from .. import FileDB, file_hash

### Beg: Logging config
logging_level = os.environ.get("LOGLEVEL", "DEBUG")
logging_fmt = "%(levelname)s:%(name)s:%(message)s"
logging_fmt = "%(message)s"
try:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging_level)
    handler = logger.handlers[0]
    handler.setFormatter(logging.Formatter(logging_fmt))
except IndexError:
    logging.basicConfig(level=logging_level, format=logging_fmt)
### End: Logging config


if __name__ == "__main__":
    parser = argparse.ArgumentParser("tar_like.index")
    parser.add_argument(
        "-b",
        "--base-folder",
        action="store",
        default="tmp/recv",
        type=str,
        help="Specify base folder",
    )
    parser.add_argument(
        "-db",
        "--database",
        action="store",
        default="~/.tar_like.sqlite",
        type=str,
        help="Specify database file (SQLite)",
    )

    args = parser.parse_args()
    base_path = os.path.normpath(args.base_folder)
    base_path_arr = base_path.split(os.sep)
    db_path = os.path.abspath(os.path.normpath(os.path.expanduser(args.database)))
    if base_path in [".", os.sep]:
        no_cut = 0
    else:
        no_cut = len(base_path.split(os.sep))
    logger.info(f"'{args.base_folder}' -> '{base_path}' (len-1={no_cut})")
    db = FileDB(db_file=db_path)
    
    print(f"--=[ checking Begin: '{base_path}'")
    for row in db.get_all():
        f_path = row[1]
        f_hash = row[5]
        f_path_arr = f_path.split(os.sep)
        ff_path = (os.sep).join([*base_path_arr,*f_path_arr])
        hash_res = file_hash(ff_path)
        if f_hash != hash_res:
            print(f"{ff_path} : {f_hash} != {hash_res}")
    print(f"--=[ checking End: '{base_path}'")

    print(f"Database path : {db_path}")
    cmds = [".mode table", "SELECT * FROM tar LIMIT 40;"]
    cmd_str = "'" + "' '".join(cmds) + "'"
    print(f"Sqlite cmd    : sqlite3 '{db_path}' {cmd_str}")
