#!/usr/bin/python

import argparse
import logging
import os
import io
import requests
import os.path
import functools
import lz4framed
import multiprocessing as mp
import urllib3.exceptions

from typing import List
from .. import FileDB, BLK_64M, BLK_1K, BLK_10K

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

db = None
url_pfx = None
tar_id = None
base_path_arr: List[str] = None
x_blk_size: int = None


def upload_block(ii):
    global db, base_path_arr, tar_id
    res = db.get_block_silent(ii, x_blk_size)
    io_buffer = io.BytesIO()
    acc_use = 0
    session = requests.session()
    for jj, blk in enumerate(res):
        path_arr = blk["path"].split(os.sep)
        fpath = (os.sep).join([*base_path_arr, *path_arr])
        with open(fpath, "rb") as fh:
            logger.debug(f"{fpath}: {blk['r0s']}..{blk['r1e']} ({blk['use']})")
            fh.seek(blk["r0s"])
            io_buffer.write(fh.read(blk["use"]))
        acc_use += blk["use"]
    logger.debug(f"{ii:,}:acc_use={acc_use}")
    compressed = lz4framed.compress(io_buffer.getbuffer())
    io_buffer.close()
    headers = {"Content-Length": str(len(compressed))}
    try:
        session.request(
            method="PUT",
            url=f"{url_pfx}/{tar_id}/{x_blk_size}/{ii}",
            headers=headers,
            data=compressed,
        )
    except urllib3.exceptions.ProtocolError as ex:
        logger.error("Upload error", ex)
    except requests.exceptions.ConnectionError as ex:
        logger.error("Upload error", ex)


if __name__ == "__main__":
    parser = argparse.ArgumentParser("tar_like.upload")
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
        "-u",
        "--upload-url",
        action="store",
        default="http://localhost:8000/tar",
        type=str,
        help="Specify upload URL base",
    )
    parser.add_argument(
        "-p",
        "--no-processes",
        action="store",
        default=5,
        type=int,
        help="Specify number of processes for upload",
    )
    parser.add_argument(
        "-f",
        "--first-block",
        action="store",
        default=0,
        type=int,
        help="Specify first block",
    )
    parser.add_argument(
        "-l",
        "--last-block",
        action="store",
        type=int,
        help="Specify last block",
    )
    parser.add_argument(
        "-s",
        "--block-size",
        action="store",
        default=BLK_64M,
        type=int,
        help="Specify block size",
    )

    args = parser.parse_args()
    base_path = os.path.normpath(args.base_folder)
    db_path = os.path.abspath(os.path.normpath(os.path.expanduser(args.database)))
    base_path_arr = base_path.split(os.sep)
    if base_path in [".", os.sep]:
        no_cut = 0
    else:
        no_cut = len(base_path_arr)
    logger.info(f"'{args.base_folder}' -> '{base_path}' (len-1={no_cut})")
    hash_res = "dummy"
    r_path = None
    db = FileDB(db_path)

    last_info = db.get_last_row_by_id()
    total_size = last_info["offset_end"] + 1
    x_blk_size = args.block_size
    no_blocks = int((total_size + x_blk_size - 1) / x_blk_size)
    if args.last_block is not None:
        no_blocks = int(args.last_block) + 1

    DEFAULT_TAR_ID = 0
    tar_id = DEFAULT_TAR_ID
    url_pfx = args.upload_url
    first_block = args.first_block
    os.environ["NO_PROXY"] = "localhost"
    mp.set_start_method("fork")
    p = mp.Pool(args.no_processes)
    p_arr = list(range(first_block, no_blocks))
    p.map(upload_block, p_arr)
    p.close()
    p.join()
    print(f"Blocks        : {first_block}..{no_blocks-1}")
    print(f"Total size    : {total_size:,} Bytes")
    print(f"Database path : {db_path}")
    cmds = [".mode table", "SELECT * FROM tar LIMIT 40;"]
    cmd_str = "'" + "' '".join(cmds) + "'"
    print(f"Sqlite cmd    : sqlite3 '{db_path}' {cmd_str}")
    print(f"No processes  : {args.no_processes}")
    print(f"No blocks     : {no_blocks}")
