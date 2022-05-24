# tar-like

![Tar Like Diagram](docs/imgs/tar-like.png)

Folder transfer in tar like fashion. It consists of few components that let the process by streamlined.

* __index phase__ create an index of files to be transfered, capturing their `path`, `size` and `hash` (`md5`)
* __proxy__ the receiving end which has the DB created above at hand
* __upload__ the sending end  which also has the DB created above at hand
* __check__ optional tool that verifies that the files matches the hash in the DB

The whole process creates virtual `tar` like file inside the DB, which is for now just a simple concatenation of files.
In particular it just computes the position of each file within the concatenated file (`offset` and `offset_end`).
This virtual `tar` file - `SQLite` database is then shared between the sender and receiver.
The final step is to start a `tar_like.proxy` on the receiving end and `tar_like.upload` on sending site.
The sender `tar_like.upload` collects the files into a `segment` in memory (of certain arbitrary __block_size__ i.e. 10'000'000 = 10MB)
this segment is then __compressed__ using `LZ4` and using `PUT` method uploaded to `tar_like.proxy` which as it knows the
structure and from the __URL__ provided looks up the segment index, and after decompression it split the block segments back into files.

> Note: the segments are of a fixed size, however as the structure of segment is pulled from DB dynamically it can accomodate. 
> In addition the size of a segment is part of the __URL__.

It is __expected__ that the files __do not change__ during the upload. Otherwise the hashes will not match. As such it is not a problem you can retry, but the delta transfer of not yet considered and/or developed (~_new index,delta computation, new upload, resize or delete files as needed_).

## Containerization

The app was for ease of execution and portability also contanerized. It is utilizing [Docker](https://www.docker.com/) for this purpose (but [Podman](https://podman.io/) should do as well).

As a preparation step run the [mkDockerImage.sh](mkDockerImage.sh) to prepare `python:3` based image with dependencies.

> Note on containers: there was spotted an issue while running in docker container, which is most likely caused by too little memory for docker VM. The error can be seen as an error of non matching read and expected (`Content-Length`) block size.
## Individual steps

Following subsections describes the process from indexing over reception and sending up to optional hash check.
### Index

__CLI Parameters__:

```
usage: tar_like.index [-h] [-b BASE_FOLDER] [-db DATABASE] [-x EXCLUDE] [-c]

options:
  -h, --help            show this help message and exit
  -b BASE_FOLDER, --base-folder BASE_FOLDER
                        Specify base folder
  -db DATABASE, --database DATABASE
                        Specify database file (SQLite)
  -x EXCLUDE, --exclude EXCLUDE
                        Exclude regex (repeat as needed)
  -c, --clean           Clean the DB before inserting
```

An example how to make an index of this folder:

```bash
python -mtar_like.index -x .git -x __pycache__ -x tmp/ -c
```

or dockerized [`./r01-index.sh`](r01-index.sh)


* `-x` exclude of some regex pattern matched against the filepath
* `-c` clean db before inserting values

To check the resulting sqlite DB:

```bash
sqlite3 ~/.tar_like.sqlite '.mode table' 'SELECT * FROM tar LIMIT 40;'
```

### Proxy

__CLI Parameters__:

```
usage: tar_like.proxy [-h] [-b BASE_FOLDER] [-db DATABASE] [port]

positional arguments:
  port                  Specify alternate port [default: 8000]

options:
  -h, --help            show this help message and exit
  -b BASE_FOLDER, --base-folder BASE_FOLDER
                        Specify base folder
  -db DATABASE, --database DATABASE
                        Specify database file (SQLite)
```

On the receiving end run:

```bash
python -mtar_like.proxy
```

or dockerized [`./r02-proxy.sh`](r02-proxy.sh)

### Upload

__CLI Parameters__:

```
usage: tar_like.upload [-h] [-b BASE_FOLDER] [--use-s3] [--ignore-done] [--ignore-ca] [-db DATABASE] [-dbp DATABASE_PROGRESS] [-u UPLOAD_URL] [-p NO_PROCESSES]
                       [-f FIRST_BLOCK] [-l LAST_BLOCK] [-s BLOCK_SIZE]

options:
  -h, --help            show this help message and exit
  -b BASE_FOLDER, --base-folder BASE_FOLDER
                        Specify base folder
  --use-s3              Use S3 backend instead of filesystem (incl.HCP)
  --ignore-done         ignore that something was already uploaded
  --ignore-ca           ignore invalid/unverifiable TLS CA
  -db DATABASE, --database DATABASE
                        Specify database file (SQLite)
  -dbp DATABASE_PROGRESS, --database-progress DATABASE_PROGRESS
                        Specify database file to track progress (SQLite)
  -u UPLOAD_URL, --upload-url UPLOAD_URL
                        Specify upload URL base
  -p NO_PROCESSES, --no-processes NO_PROCESSES
                        Specify number of processes for upload
  -f FIRST_BLOCK, --first-block FIRST_BLOCK
                        Specify first block
  -l LAST_BLOCK, --last-block LAST_BLOCK
                        Specify last block
  -s BLOCK_SIZE, --block-size BLOCK_SIZE
                        Specify block size
```

On the sending end run:

```bash
python -mtar_like.upload -f 0 -s 100000
```

or dockerized [`./r03-upload.sh`](r03-upload.sh)

where:

* `-f 0` is the number of first block to send
* `-s 100000` is the size of block in bytes

there is also an alternative that uses __S3__ (or alike interface - i.e. __HCP__ - Hitachi Cloud Platform) as a source of files:

using Docker [`./r05-upload_s3.sh`](r05-upload_s3.sh) it requires some envronment variables see [`.tar_like_rc.example`](.tar_like_rc.example).


### Check

__CLI Parameters__:

```
usage: tar_like.check [-h] [-b BASE_FOLDER] [-db DATABASE] [-f FIRST_BLOCK] [-l LAST_BLOCK] [-s BLOCK_SIZE]

options:
  -h, --help            show this help message and exit
  -b BASE_FOLDER, --base-folder BASE_FOLDER
                        Specify base folder
  -db DATABASE, --database DATABASE
                        Specify database file (SQLite)
  -f FIRST_BLOCK, --first-block FIRST_BLOCK
                        Specify first block
  -l LAST_BLOCK, --last-block LAST_BLOCK
                        Specify last block
  -s BLOCK_SIZE, --block-size BLOCK_SIZE
                        Specify block size
```

To check the checksums of files on filesystem vs in the DB

```bash
python -mtar_like.check
```

or dockerized [`./r04_check.sh`](r04_check.sh)


## Notes on containerised deployment

The containers are the easiest way of deploying the `tar_like` proxy (and other parts). There are ready made scripts, that can be used. To make things customisable there is a number of variables that can override the default values and behavior as well as number of paramaters tha the individual parts access when run from commandline (including use inside docker) for those see sections `CLI Parameters` above.

The environment variables with their default values as used by the scripts are:

| Name               | Default value                | Purpose                                                                                                                                                                                                          |
|--------------------|------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `DDIR`             | `$PWD/tmp`                   | Destination directory R/W, stores data as well as the `.tar_like.sqlite`                                                                                                                                         |
| `EX_PYCACERT`      | `~/.python-cacert.pem`       | the proxy CA bundle (or `--ignore-ca`)                                                                                                                                                                           |
| `IN_PYCACERT`      | `ca-cert.pem`                | the S3/HCP source CA                                                                                                                                                                                             |
| `LOCAL_BIND`       | `8000`                       | Where should the docker lister for HTTP access forwarded to port `8000` inside container of `tar_like.proxy`                                                                                                     |
| `LOCAL_BIND_HTTPS` | `8443`                       | Where should the docker lister for HTTPS access forwarded to port `8443` inside container of `haproxy` which in turn contact the `tar_like.proxy` localy via `127.0.0.1:8000` __inside__ container (same net-ns) |
| `SDIR`             | `$PWD`                       | source directory, where to look for files to `tar_like.index` and `tar_like.upload` (R/O)                                                                                                                        |
| `UDIR`             | `/data/rw/recv-test`         | Where to put the uploaded data to the `tar_like.proxy` (R/W) __inside__ container                                                                                                                                |
| `UPLOAD_URL`       | `http://172.17.0.1:8000/tar` | Used by `tar_like.upload` to know where to contact the `tar_like.proxy`                                                                                                                                          |

> Note: it is expected that in most cased only these variables are to be modified not the config files or scripts. The most frequent modification should be `LOCAL_BIND_HTTPS` eventually `DDIR` along with `SDIR`

__TO DOes__:

* add intermediate hash layer, where not __paths__ will be transferred but __hashes__ (i.e. SHA1) and then reverse mapped to files on target machine
* extend the __hashes__ to __merkle trees__ ([Merkle DAGs: Structuring Data for the Distributed Web](https://proto.school/merkle-dags) and [Merkle Directed Acyclic Graphs](https://docs.ipfs.io/concepts/merkle-dag/#merkle-directed-acyclic-graphs-dags))
* consider __Rust__, __Go__ or __C++__ for better server/proxy side
* alternative transports (Wiki:[Tsunami UDP Protocol](https://en.wikipedia.org/wiki/Tsunami_UDP_Protocol) also @ [Source Forge Proj](https://sourceforge.net/projects/tsunami-udp/), [UDP-Based Protocol (UDT)](https://www.haivision.com/resources/streaming-video-definitions/udp-based-protocol-udt/) also @ [Source Forge Web](https://udt.sourceforge.io/) evolution to [SRT - Secure Reliable Transport](https://www.haivision.com/products/srt-secure-reliable-transport/), ref. IBM Aspera FASP or Data Expedition Fast File Transfer)
* [SyncThing](https://syncthing.net/), [Resilio](https://www.resilio.com/) former __BTSync__ (aka BitTorrent Sync)
* Multicast [PGM](https://en.wikipedia.org/wiki/Pragmatic_General_Multicast) and [Clonezilla](https://clonezilla.org/show-live-doc-content.php?topic=clonezilla-live/doc/11_lite_server) deprecated: [partimage](https://www.partimage.org/), [fsarchiver](https://www.fsarchiver.org/), [partclone](https://partclone.org/)
* [rclone](https://en.wikipedia.org/wiki/Rclone) cloud backends
