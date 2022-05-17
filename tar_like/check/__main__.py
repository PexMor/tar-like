#!/usr/bin/python

import argparse
import logging
import os
import sys
import os.path

from .. import FileDB, file_hash, BLK_30M

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

    blk_size = args.block_size
    l_row = db.get_last_row_by_id()
    if args.last_block is not None:
        l_blk = args.last_block
    else:
        l_blk = int((l_row["offset_end"] + blk_size - 1) / blk_size)
    f_blk = args.first_block
    ofs_start = f_blk*blk_size
    ofs_end = l_blk*blk_size
    logger.info(f"{f_blk:,}..{l_blk:,} : {ofs_start:,}..{ofs_end:,} : {l_row['offset_end']+1:,} B < {l_blk*blk_size:,} B")
    print(f"--=[ checking Begin: '{base_path}'")
    # id/0,path/1,size/2,offset/3,offset_end/4,hash/5
    cnt_ok = 0
    cnt_err = 0
    sum_ok = 0
    sum_err = 0
    for row in db.get_all():
        f_offset = row[3]
        f_offset_end = row[4]
        f_path = row[1]
        f_path_arr = f_path.split(os.sep)
        ff_path = (os.sep).join([*base_path_arr, *f_path_arr])
        if f_offset_end>=ofs_start and f_offset<=ofs_end:
            f_hash = row[5]        
            hash_res = file_hash(ff_path)
            if f_hash != hash_res:
                print(f"{ff_path} : {f_hash} != {hash_res}")
                cnt_err+=1
                sum_err+=row[2]
            else:
                cnt_ok+=1
                sum_ok+=row[2]
        else:
            print(f"{ff_path} : {f_offset:,}..{f_offset_end:,}")
        if f_offset_end>=ofs_end:
            break
    print(f"--=[ checking End: '{base_path}'")
    print(f"OK: {cnt_ok:,}/{sum_ok:,} B Err: {cnt_err:,}/{sum_err:,} B")

    print(f"Database path : {db_path}")
    cmds = [".mode table", "SELECT * FROM tar LIMIT 40;"]
    cmd_str = "'" + "' '".join(cmds) + "'"
    print(f"Sqlite cmd    : sqlite3 '{db_path}' {cmd_str}")
