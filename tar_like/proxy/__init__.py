#!/usr/bin/python
#
# inspired by: https://github.com/danvk/RangeHTTPServer
#

import io
import json
import logging
import lz4framed
import os
import os.path
import pathlib
import re
import requests
import sys
import time
import yaml

from typing import List
from .. import FileDB

from datetime import datetime
from pathlib import Path
from http.server import SimpleHTTPRequestHandler

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


def mkTarRequestHandler(base_path_arr: List[str], a_db_path: str):
    class TarRequestHandler(SimpleHTTPRequestHandler):
        RECV_PATH_ARR = base_path_arr
        db_path = a_db_path

        def do_PUT(self):
            logger.info(f"path = {self.path}")
            ts_b = datetime.now()
            path_arr = self.path.split(os.sep)
            path_arr = path_arr[-3:]
            path_arr = [int(ii) for ii in path_arr]
            tar_id, tar_blk_size, tar_blk_no = path_arr
            db = FileDB(self.db_path)
            res = db.get_block_silent(tar_blk_no, tar_blk_size)
            self.send_response(200)
            io_buf = io.BytesIO()
            io_buf.write(self.rfile.read(int(self.headers["Content-Length"])))
            dec = lz4framed.decompress(io_buf.getbuffer())
            io_buf.close()
            for blk in res:
                # print("---\n",blk)
                blk_path_arr = blk["path"].split(os.sep)
                rel_path = (os.sep).join([*self.RECV_PATH_ARR, *blk_path_arr])
                pdir = os.path.dirname(rel_path)
                Path(pdir).mkdir(parents=True, exist_ok=True)
                Path(rel_path).touch()
                with open(rel_path, "rb+") as fp:
                    os.lseek(fp.fileno(), blk["r0s"], os.SEEK_SET)
                    fp.write(dec[blk["bofs"] : blk["bofs"] + blk["use"]])
            ctype = "text/plain"
            gmt_str = time.strftime(
                "%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time())
            )
            response = json.dumps(path_arr)
            response_bytes = response.encode("UTF-8")
            response_length = len(response_bytes)
            self.send_header("Content-type", ctype)
            self.send_header("Content-Length", str(response_length))
            self.send_header("Last-Modified", gmt_str)
            self.end_headers()
            self.wfile.write(response_bytes)
            dur_secs = (datetime.now() - ts_b).total_seconds()
            logger.info(f"Done: {tar_blk_no:10,} dur: {dur_secs:,}")
            return

    return TarRequestHandler
