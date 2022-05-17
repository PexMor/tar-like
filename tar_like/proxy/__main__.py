#!/usr/bin/python
import os
import argparse
import http.server as SimpleHTTPServer

from asyncio.log import logger
from . import mkTarRequestHandler
# from .. import FileDB

parser = argparse.ArgumentParser()
parser.add_argument(
    "port",
    action="store",
    default=8000,
    type=int,
    nargs="?",
    help="Specify alternate port [default: 8000]",
)
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
args = parser.parse_args()
base_path = os.path.normpath(args.base_folder)
base_path_arr = base_path.split(os.sep)
db_path = os.path.abspath(os.path.normpath(os.path.expanduser(args.database)))
logger.info(f"Base path : {args.base_folder}")
logger.info(f"DB path   : {db_path}")
SimpleHTTPServer.test(
    HandlerClass=mkTarRequestHandler(base_path_arr, db_path), port=args.port
)
