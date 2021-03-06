#!/usr/bin/python

import argparse
import boto3
import functools
import io
import logging
import lz4framed
import multiprocessing as mp
import os
import os.path
import requests
import sys
import certifi
import urllib3
import urllib3.exceptions

from dataclasses import dataclass
from typing import List
from .. import FileDB, BLK_32M, BLK_16M, BLK_30M, BLK_32M_I, get_data_range, set_use_s3

### Beg: Logging config
logging_level = os.environ.get("LOGLEVEL", "INFO")
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

TIMEOUT_SECS: float = 120.0


@dataclass(frozen=True)
class DoneBlk:
    tar_id: int
    blk_size: int
    blk_id: int


@dataclass(frozen=True)
class FinishToken:
    pass


@dataclass(frozen=True)
class AbortOp:
    pass


db = None
url_pfx = None
tar_id = None
base_path_arr: List[str] = None
x_blk_size: int = None
q_blk_done: mp.Queue = None
ignore_done: bool = False
ignore_ca: bool = False


def upload_db(db_fn):
    global tar_id, ignore_ca
    session = requests.session()
    io_buffer = io.BytesIO()
    with open(db_fn, "rb") as fh:
        io_buffer.write(fh.read())
    compressed = lz4framed.compress(io_buffer.getbuffer())
    io_buffer.close()
    db_compressed_len = len(compressed)
    headers = {"Content-Length": str(db_compressed_len)}
    db_upload_url = f"{url_pfx}/{tar_id}/db"
    logger.info(
        f"Uploading the DB to {db_upload_url} compressed size {db_compressed_len:,}"
    )
    try:
        resp = session.request(
            method="PUT",
            url=db_upload_url,
            headers=headers,
            data=compressed,
            verify=not ignore_ca,
        )
    except urllib3.exceptions.ProtocolError as ex:
        logger.error("Upload error", ex)
    except requests.exceptions.ConnectionError as ex:
        logger.error("Upload error", ex)


def upload_block(blk_id: int):
    global db, base_path_arr, tar_id, q_blk_done, ignore_done, ignore_ca
    if not ignore_done and db.check_if_done(tar_id, x_blk_size, blk_id):
        logger.info(f"Block {blk_id:,} was already uploaded")
    else:
        res = db.get_block_silent(x_blk_size, blk_id)
        io_buffer = io.BytesIO()
        acc_use = 0
        session = requests.session()
        for jj, blk in enumerate(res):
            path_arr = blk["path"].split(os.sep)
            fpath = (os.sep).join([*base_path_arr, *path_arr])
            # logger.info(f"{blk_id:,} {fpath}: {blk['r0s']}..{blk['r1e']} ({blk['use']})")
            get_data_range(fpath, offset=blk["r0s"], data_len=blk["use"], ioh=io_buffer)
            acc_use += blk["use"]
        logger.debug(f"{blk_id:,}:acc_use={acc_use}")
        compressed = lz4framed.compress(io_buffer.getbuffer().tobytes())
        len_compressed = len(compressed)
        io_buffer.close()
        headers = {"Content-Length": str(len_compressed)}
        try:
            logger.info(f"{x_blk_size:,}/{blk_id:,} : {len_compressed:,} B")
            resp = session.request(
                method="PUT",
                url=f"{url_pfx}/{tar_id}/{x_blk_size}/{blk_id}",
                headers=headers,
                data=compressed,
                timeout=TIMEOUT_SECS,
                verify=not ignore_ca,
            )
            if resp.ok:
                q_blk_done.put(DoneBlk(tar_id, x_blk_size, blk_id))
        except urllib3.exceptions.ProtocolError as ex:
            logger.error("Protocol error")
            q_blk_done.put(AbortOp())
        except requests.exceptions.ConnectionError as ex:
            logger.error("Connection error")
            q_blk_done.put(AbortOp())


def get_res(no_processes: int):
    global q_blk_done, db
    cnt = no_processes
    while cnt > 0:
        res = q_blk_done.get()
        logger.info(res)
        if isinstance(res, FinishToken):
            cnt -= 1
        elif isinstance(res, DoneBlk):
            db.save_res(res.tar_id, res.blk_size, res.blk_id)
        elif isinstance(res, AbortOp):
            pass
    logger.info("Finished consuming results")


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
        "--use-s3",
        action="store_true",
        default=False,
        help="Use S3 backend instead of filesystem (incl.HCP)",
    )
    parser.add_argument(
        "--ignore-done",
        action="store_true",
        default=False,
        help="ignore that something was already uploaded",
    )
    parser.add_argument(
        "--ignore-ca",
        action="store_true",
        default=False,
        help="ignore invalid/unverifiable TLS CA",
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
        "-dbp",
        "--database-progress",
        action="store",
        default="~/.tar_like_progress.sqlite",
        type=str,
        help="Specify database file to track progress (SQLite)",
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
        default=BLK_30M,
        type=int,
        help="Specify block size",
    )

    ca_bundle = certifi.where()
    urllib3.disable_warnings()
    print(f"CA Cert Bundle: {ca_bundle}")
    args = parser.parse_args()

    DEFAULT_TAR_ID = 0
    tar_id = DEFAULT_TAR_ID
    url_pfx = args.upload_url
    first_block = args.first_block
    set_use_s3(args.use_s3)
    ignore_done = args.ignore_done
    ignore_ca = args.ignore_ca
    os.environ["NO_PROXY"] = "localhost"
    mp.set_start_method("fork")

    base_path = os.path.normpath(args.base_folder)
    db_path = os.path.abspath(os.path.normpath(os.path.expanduser(args.database)))
    db_progress_path = os.path.abspath(
        os.path.normpath(os.path.expanduser(args.database_progress))
    )
    base_path_arr = base_path.split(os.sep)
    if base_path in [".", os.sep]:
        no_cut = 0
    else:
        no_cut = len(base_path_arr)
    logger.info(f"'{args.base_folder}' -> '{base_path}' (len-1={no_cut})")
    hash_res = "dummy"
    r_path = None
    upload_db(db_path)
    # sys.exit(0)
    db = FileDB(db_file=db_path, db_progress_file=db_progress_path)

    last_info = db.get_last_row_by_id()
    total_size = last_info["offset_end"] + 1
    x_blk_size = args.block_size
    no_blocks = int((total_size + x_blk_size - 1) / x_blk_size)
    if args.last_block is not None:
        no_blocks = int(args.last_block) + 1

    q_blk_done = mp.Queue(100)
    upload_proc_pool = mp.Pool(args.no_processes)

    res_p = mp.Process(target=get_res, args=(args.no_processes,))
    res_p.start()

    p_arr = list(range(first_block, no_blocks))
    upload_proc_pool.map(upload_block, p_arr)
    logger.info("Finished mapping")
    for ii in range(0, args.no_processes):
        q_blk_done.put(FinishToken())
    upload_proc_pool.close()
    upload_proc_pool.join()
    res_p.join()
    print(f"Blocks        : {first_block}..{no_blocks-1}")
    print(f"Total size    : {total_size:,} Bytes")
    print(f"Database path : {db_path}")
    cmds = [".mode table", "SELECT * FROM tar LIMIT 40;"]
    cmd_str = "'" + "' '".join(cmds) + "'"
    print(f"Sqlite cmd    : sqlite3 '{db_path}' {cmd_str}")
    print(f"No processes  : {args.no_processes}")
    print(f"No blocks     : {no_blocks}")
    print(f"Ignore done   : {ignore_done}")
    print(f"Use S3        : {args.use_s3}")
    print(f"SSL_CERT_FILE : {os.getenv('SSL_CERT_FILE')}")
    print(f"CA Cert Bundle: {ca_bundle}")
    print(f"Ignore CA     : {ignore_ca}")
