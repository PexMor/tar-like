import boto3
import botocore.client
import botocore.exceptions
import hashlib
import io
import logging
import os
import os.path
import sqlite3
import sys

UNIT = 1000
BLK_1K = 1 * UNIT
BLK_10K = 10 * UNIT
BLK_500K = 500 * UNIT
BLK_1M = 1 * UNIT * UNIT
BLK_10M = 10 * UNIT * UNIT
BLK_50M = 50 * UNIT * UNIT
BLK_64M = 64 * UNIT * UNIT
UNIT_I = 1024
BLK_1K_I = 1 * UNIT_I
BLK_512K_I = 512 * UNIT_I
BLK_1M_I = 1 * UNIT_I * UNIT_I
BLK_10M_I = 10 * UNIT_I * UNIT_I
BLK_50M_I = 50 * UNIT_I * UNIT_I
BLK_64M_I = 64 * UNIT_I * UNIT_I

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

s3rsc = None
s3bucket = None
use_s3: bool = False


def set_use_s3(a_use_s3: bool):
    global use_s3
    use_s3 = a_use_s3


def to_bool(val: str) -> bool:
    if (
        val is None
        or val.lower() == "no"
        or val.lower() == "false"
        or val.lower() == "0"
        or val.lower() == "f"
    ):
        return False
    else:
        return True


def get_data_range(fpath: str, offset: int, data_len: int, ioh: io.BytesIO):
    global s3rsc, s3bucket
    if use_s3:
        if s3rsc is None:
            logger.info("Seting up S3")
            # required environment variables:
            # AWS_ACCESS_KEY_ID
            # AWS_SECRET_ACCESS_KEY
            # TARLIKE_S3_BUCKET
            # TARLIKE_S3_ENDPOINT - when using HCP
            # TARLIKE_S3_TLS_VERIFY - to set TLS verify
            # optional environment variables:
            # AWS_CA_BUNDLE - where to find a CA bundle file
            session = boto3.session.Session()
            s3bucket = os.getenv("TARLIKE_S3_BUCKET")
            s3endpoint = os.getenv("TARLIKE_S3_ENDPOINT")
            s3tls_verify = os.getenv("TARLIKE_S3_TLS_VERIFY")
            kwargs = {}
            if s3bucket is None:
                logger.error(
                    "Need bucket name in TARLIKE_S3_BUCKET environment variable"
                )
                sys.exit(-1)
            else:
                logger.info(f"TARLIKE_S3_BUCKET = {s3bucket}")
            if s3endpoint is not None:
                kwargs["endpoint_url"] = s3endpoint
                logger.info(f"TARLIKE_S3_ENDPOINT = {s3endpoint}")
            if s3tls_verify is not None:
                kwargs["verify"] = to_bool(s3tls_verify)
                logger.info(f"TARLIKE_S3_TLS_VERIFY = {s3tls_verify}")
            s3_config = botocore.client.Config(
                s3={"addressing_style": "virtual", "payload_signing_enabled": True},
                signature_version="s3v4",
            )
            kwargs["config"] = s3_config
            s3rsc = session.resource("s3", **kwargs)
        try:
            obj = s3rsc.Object(s3bucket, fpath)
            logger.debug(f"is is none: {obj is None}")
            logger.debug(f"obj: {obj}")
            logger.debug(f"etag: {obj.e_tag}")
            logger.debug(f"length: {obj.content_length}")
            resp = obj.get(Range="bytes={}-{}".format(offset, offset + data_len - 1))
            content = resp["Body"]
            ioh.write(content.read())
        except botocore.exceptions.ClientError as error:
            logger.error("ClientError")
            ioh.write(b"X" * data_len)
        except Exception as ex:
            logger.error("Unable to connect", ex)
            # sys.exit(-1)
    else:
        with open(fpath, "rb") as fh:
            fh.seek(offset)
            ioh.write(fh.read(data_len))


def file_hash(fname: str, hash_name: str = "md5", chunk_size: int = 8192):
    """Compute hash of a file, providing the default hash function and block size"""
    if os.path.isfile(fname):
        hash = hashlib.new(hash_name)
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash.update(chunk)
        return hash.hexdigest()
    else:
        return "--file-not-found--"


DEFAULT_SRC_DB_PATH = os.path.join(os.getenv("HOME"), ".tar_like.sqlite")
DEFAULT_PROGRESS_DB_PATH = os.path.join(os.getenv("HOME"), ".tar_like_upload.sqlite")


class FileDB:
    def __init__(
        self,
        db_file: str = DEFAULT_SRC_DB_PATH,
        db_progress_file: str = DEFAULT_PROGRESS_DB_PATH,
        clean_db: bool = False,
    ) -> None:
        # TODO: check_same_thread is only valid when access is R/O, need split here!!!
        logger.debug(f"db_file: {db_file}")
        self.db_file = db_file
        self.con = sqlite3.connect(db_file, check_same_thread=False)
        self.con.isolation_level = None
        self.cur = self.con.cursor()
        if clean_db:
            logger.info("Cleaning the DB (DROP TABLE tar)")
            self.drop_db()
        self.create_db()
        # open also progress file
        self.con_progress = sqlite3.connect(db_progress_file, check_same_thread=False)
        self.con_progress.isolation_level = None
        self.cur_progress = self.con_progress.cursor()
        if clean_db:
            logger.info("Cleaning the progress DB (DROP TABLE res)")
            self.drop_db_progress()
        self.create_db_progress()

    def drop_db_progress(self):
        self.cur_progress.execute("DROP TABLE IF EXISTS res;")

    def create_db_progress(self):
        self.cur_progress.execute(
            "CREATE TABLE IF NOT EXISTS res (tar_id INT64, blk_size INT64, blk_id INT64)"
        )
        self.cur_progress.execute(
            "CREATE INDEX IF NOT EXISTS idx_res_all ON res (tar_id,blk_size,blk_id)"
        )

    def drop_db(self):
        self.cur.execute("DROP TABLE IF EXISTS tar;")

    def create_db(self):
        self.cur.execute(
            "CREATE TABLE IF NOT EXISTS tar (id INT64, path TEXT, size INT64, offset INT64, offset_end INT64, hash TEXT)"
        )
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_tar_path ON tar (path)")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_tar_hash ON tar (hash)")
        self.cur.execute("CREATE INDEX IF NOT EXISTS idx_tar_offset ON tar (offset)")
        self.cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_tar_offset_end ON tar (offset_end)"
        )
        self.cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_tar_offset_n_offset_end ON tar (offset,offset_end)"
        )

    def insert(
        self, id: int, path: str, size: int, offset: int, offset_end: int, hash: str
    ):
        self.cur.execute(
            "INSERT INTO tar (id,path,size,offset,offset_end,hash) VALUES (?,?,?,?,?,?)",
            (id, path, size, offset, offset_end, hash),
        )

    def get_last_row_by_id(self):
        res = self.cur.execute("SELECT * FROM tar WHERE id = (SELECT MAX(id) from tar)")
        # TODO: check number of results
        db_row = res.fetchone()
        if db_row is not None:
            return {
                "id": db_row[0],
                "path": db_row[1],
                "size": db_row[2],
                "offset": db_row[3],
                "offset_end": db_row[4],
                "hash": db_row[5],
            }
        else:
            return None

    def check_if_done(self, tar_id: int, blk_size: int, blk_id: int):
        SQL = "SELECT count(*) FROM res WHERE tar_id=? AND blk_size=? AND blk_id=?"
        rowh = self.cur_progress.execute(SQL, (tar_id, blk_size, blk_id))
        res = rowh.fetchone()
        logger.debug(res)
        return res[0] > 0

    def save_res(self, tar_id: int, blk_size: int, blk_id: int):
        SQL = "INSERT INTO res (tar_id,blk_size,blk_id) VALUES (?,?,?)"
        res = self.cur_progress.execute(SQL, (tar_id, blk_size, blk_id))

    def get_all(self):
        SQL = "SELECT id,path,size,offset,offset_end,hash FROM tar"
        db_res = self.cur.execute(SQL)
        return db_res.fetchall()

    def get_block_silent(self, blk_size: int, blk_no: int):
        blk_start = blk_no * blk_size
        blk_end = blk_start + blk_size - 1
        SQL = f"SELECT id,path,size,offset,offset_end,hash FROM tar WHERE offset_end>={blk_start} AND offset<={blk_end}"
        rows = self.cur.execute(SQL)
        sum_use = 0
        collect = []
        for (r_id, r_path, r_size, r_offset, r_offset_end, r_hash) in rows:
            # default range is whole file
            range_start, range_end = 0, r_size - 1
            use = r_size
            if r_offset < blk_start and r_offset_end > blk_end:
                # file starts below the segment and ends above it
                # thus we have to carve just a blk_size out of it
                use = blk_size
                # offset from the beginning of file to the start of segment
                range_start = blk_start - r_offset
                # offset from the beginning of file to the end of segment
                range_end = range_start + blk_size - 1
            elif r_offset < blk_start:
                # file starts below the segment but ends inside the segment
                # offset from the beginning of file to the start of segment
                range_start = blk_start - r_offset
                use = r_size - range_start
            elif r_offset_end > blk_end:
                # file starts inside the selected segment but ends above it
                # offset from the beginning of file to the end of segment
                range_end = blk_end - r_offset
                use = range_end + 1
            collect.append(
                {
                    "id": r_id,
                    "path": r_path,
                    "size": r_size,
                    "r0s": range_start,
                    "r1e": range_end,
                    "use": use,
                    "bofs": sum_use,
                    "hash": r_hash,
                }
            )
            sum_use += use
        return collect

    def get_file_info(self, path: str):
        SQL = f"SELECT id,path,size,offset,offset_end,hash FROM tar WHERE path=?"
        rows = self.cur.execute(SQL, (path,))
        info = rows.fetchone()
        return {
            "id": info[0],
            "path": info[1],
            "size": info[2],
            "offset": info[3],
            "offset_end": info[4],
            "hash": info[5],
        }
