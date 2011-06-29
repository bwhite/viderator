import bindepend
from contextlib import contextmanager
import tarfile
import os
import tempfile
import shutil
import subprocess

bindepend.silent = True


@contextmanager
def freeze_ffmpeg():
    """Archive the ffmpeg binary and its dependencies so it can be copied to
    hadoop. The ffmpeg found on the path (i.e. `which ffmpeg`) is used. The
    tar file is created in a temp folder and cleaned up automatically.

    Returns:
       absolute path to a tar file

    Example:
        with freeze_ffmpeg() as ffmpegtar:
            hadoopy.launch_frozen(hdfs_input, hdfs_output,
                                  'hadoopy_script.py',
                                  files=[ffmpegtar])

    """

    proc = subprocess.Popen('which ffmpeg', shell=True).strip()
    program = process.stdout.read()
    libs = bindepend.selectImports(program)

    try:
        tmpdir = tempfile.mkdtemp()
        tar = os.path.join(tmpdir, 'ffmpegbin.tar')
        with tarfile.open(tar, 'w', dereference=True) as f:
            for _, fn in libs + [('', program)]:
                f.add(fn, arcname=os.path.basename(fn))

        yield tar

    finally:
        shutil.rmtree(tmpdir)
