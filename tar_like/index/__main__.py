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
        default=".",
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
    parser.add_argument(
        "-x",
        "--exclude",
        action="append",
        type=str,
        help="Exclude regex (repeat as needed)",
    )
    parser.add_argument(
        "-c",
        "--clean",
        action="store_true",
        default=False,
        help="Clean the DB before inserting",
    )

    args = parser.parse_args()
    base_path = os.path.normpath(args.base_folder)
    db_path = os.path.abspath(os.path.normpath(os.path.expanduser(args.database)))
    if base_path in [".", os.sep]:
        no_cut = 0
    else:
        no_cut = len(base_path.split(os.sep))
    logger.info(f"'{args.base_folder}' -> '{base_path}' (len-1={no_cut})")
    hash_res = "dummy"
    r_path = None
    db = FileDB(db_path, clean_db=args.clean)

    if args.exclude is not None:
        rex = [re.compile(re_str) for re_str in args.exclude]
    else:
        rex = []
    g_ofs = 0
    g_id = 0
    for root, d_names, f_names in os.walk(base_path):
        for f in f_names:
            # get path including prefix
            x_path = os.path.normpath(os.path.join(root, f))
            if not any([rex_item.search(x_path) is not None for rex_item in rex]):
                s_path = x_path.split(os.sep)
                # split the path into chunks and peel off the prefix
                a_path = s_path[no_cut:]
                # create the relative path
                r_path = os.path.join(*a_path)
                hash_res = file_hash(x_path)
                f_size = os.path.getsize(x_path)
                logger.debug(
                    f"{g_id+1:3,}|{g_ofs:14,}|{f_size:14,}|{hash_res}|{r_path}"
                )
                db.insert(g_id, r_path, f_size, g_ofs, g_ofs + f_size - 1, hash_res)
                g_id += 1
                g_ofs += f_size
    print(f"Database path : {db_path}")
    cmds = [".mode table", "SELECT * FROM tar LIMIT 40;"]
    cmd_str = "'" + "' '".join(cmds) + "'"
    print(f"Sqlite cmd    : sqlite3 '{db_path}' {cmd_str}")
    print(f"Total size    : {g_ofs:,} Bytes")
    print(f"Regexes       : {args.exclude}")
