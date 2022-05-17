#!/usr/bin/env

import sqlite3
import os
import sys
import argparse
import os.path

if __name__ == "__main__":
    parser = argparse.ArgumentParser("cvt.py")
    parser.add_argument(
        "-i",
        "--input-db",
        action="store",
        required=True,
        type=str,
        help="Specify input sqlite db",
    )
    parser.add_argument(
        "-o",
        "--output-db",
        action="store",
        required=True,
        type=str,
        help="Specify output sqlite db",
    )
    parser.add_argument(
        "-s",
        "--select",
        action="store",
        # default="SELECT path,size,hash FROM test",
        default="SELECT a as path,b as size,c as hash FROM test",
        type=str,
        help="Specify input db select ",
    )
    args = parser.parse_args()

    icon = sqlite3.connect(args.input_db)
    icon.isolation_level = None
    icur = icon.cursor()

    ocon = sqlite3.connect(args.output_db)
    ocon.isolation_level = None
    ocur = ocon.cursor()
    ocur.execute("BEGIN")
    doms = []
    try:
        ocur.execute("DROP TABLE IF EXISTS tar;")
        ocur.execute(
            "CREATE TABLE tar (id INT64, path TEXT, size INT64, offset INT64, offset_end INT64, hash TEXT);"
        )
        rows = icur.execute(args.select)
        id = 0
        tar_items = []
        ofs = 0
        for row in rows:
            flen = int(row[1])
            if flen > 0:
                tar_item = (id, row[0], flen, ofs, ofs + flen - 1, row[2])
                ofs += flen
                id += 1
                tar_items.append(tar_item)
        ocur.executemany(
            "INSERT INTO tar (id,path,size,offset,offset_end,hash) VALUES (?, ?, ?, ?, ?, ?);",
            tar_items,
        )
        ocur.execute("COMMIT")
    except sqlite3.Error as ex:
        ocur.execute("ROLLBACK")
