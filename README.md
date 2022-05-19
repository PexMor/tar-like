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

On the receiving end run:

```bash
python -mtar_like.proxy
```

or dockerized [`./r02-proxy.sh`](r02-proxy.sh)

### Upload

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

To check the checksums of files on filesystem vs in the DB

```bash
python -mtar_like.check
```

or dockerized [`./r04_check.sh`](r04_check.sh)

__TO DOes__:

* add intermediate hash layer, where not __paths__ will be transferred but __hashes__ (i.e. SHA1) and then reverse mapped to files on target machine
* extend the __hashes__ to __merkle trees__ ([Merkle DAGs: Structuring Data for the Distributed Web](https://proto.school/merkle-dags) and [Merkle Directed Acyclic Graphs](https://docs.ipfs.io/concepts/merkle-dag/#merkle-directed-acyclic-graphs-dags))
* consider __Rust__, __Go__ or __C++__ for better server/proxy side
* alternative transports (Wiki:[Tsunami UDP Protocol](https://en.wikipedia.org/wiki/Tsunami_UDP_Protocol) also @ [Source Forge Proj](https://sourceforge.net/projects/tsunami-udp/), [UDP-Based Protocol (UDT)](https://www.haivision.com/resources/streaming-video-definitions/udp-based-protocol-udt/) also @ [Source Forge Web](https://udt.sourceforge.io/) evolution to [SRT - Secure Reliable Transport](https://www.haivision.com/products/srt-secure-reliable-transport/), ref. IBM Aspera FASP or Data Expedition Fast File Transfer)
* [SyncThing](https://syncthing.net/), [Resilio](https://www.resilio.com/) former __BTSync__ (aka BitTorrent Sync)
* Multicast [PGM](https://en.wikipedia.org/wiki/Pragmatic_General_Multicast) and [Clonezilla](https://clonezilla.org/show-live-doc-content.php?topic=clonezilla-live/doc/11_lite_server) deprecated: [partimage](https://www.partimage.org/), [fsarchiver](https://www.fsarchiver.org/), [partclone](https://partclone.org/)
* [rclone](https://en.wikipedia.org/wiki/Rclone) cloud backends
