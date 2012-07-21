import bindepend
from contextlib import contextmanager
import tarfile
import os
import tempfile
import shutil
import subprocess

bindepend.silent = True


@contextmanager
def freeze_ffmpeg(preset_path='/tmp/ffmpegbin.tar'):
    """Archive the ffmpeg binary and its dependencies so it can be copied to
    hadoop. The ffmpeg found on the path (i.e. `which ffmpeg`) is used. The
    tar file is created in a temp folder and cleaned up automatically.

    Returns:
        absolute path to a tar file

    Raises:
        OSError:  FFMPEG not found.

    Example:
        with freeze_ffmpeg() as ffmpegtar:
            hadoopy.launch_frozen(hdfs_input, hdfs_output,
                                  'hadoopy_script.py',
                                  files=[ffmpegtar])

    """
    if os.path.exists(preset_path):
        yield preset_path
        return
    try:
        tmpdir, tar = main()
        yield tar
    finally:
        shutil.rmtree(tmpdir)


def main():
    proc = subprocess.Popen('which ffmpeg', shell=True, stdout=subprocess.PIPE)
    program = proc.stdout.read().strip()
    if not program:
        raise OSError('ffmpeg not installed!')
    libs = bindepend.selectImports(program)

    tmpdir = tempfile.mkdtemp()
    tar = os.path.join(tmpdir, 'ffmpegbin.tar')
    f = tarfile.open(tar, 'w')
    f.dereference = True  # for Python 2.4 compatibility, this is not in constructor
    for _, fn in libs + [('', program)]:
        f.add(fn, arcname=os.path.basename(fn))
    f.close()
    return tmpdir, tar


if __name__ == '__main__':
    main()
