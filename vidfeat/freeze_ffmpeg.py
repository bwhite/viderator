import bindepend
from contextlib import contextmanager
import tarfile
import os


@contextmanager
def freeze_ffmpeg():
    # TODO grab this from the path
    program = '/usr/local/bin/ffmpeg'
    libs = bindepend.getImports(program)

    tar = 'ffmpegbin.tar'
    with tarfile.open(tar, 'w') as f:
        for fn in libs + [program]:
            f.add(fn, arcname=os.path.basename(fn))

        yield tar
