import imfeat
import subprocess
import Image
import re
import StringIO
import tarfile
import os


def _read_fps(stderr):
    """Read the fps from FFMpeg's debug output
    """
    # Stream #0.0: Video: mpeg4, yuv420p, 1280x720 \
    # [PAR 1:1 DAR 16:9], 29.97 fps, 29.97 tbr, 29.97 tbn, 30k tbc
    while 1:
        line = stderr.readline()
        print line.strip()
        if not line:
            raise Exception("couldn't parse FPS from ffmpeg stderr")

        m = re.search('Stream #.* Video: .* ([\.\d]+) tbr', line)
        if not m is None:
            return float(m.groups()[0])


def _read_ppm(fp):
    """Read one PPM image at a from a stream (ffmpeg image2pipe output)
    """
    buf = ''
    format = fp.readline()
    if not format:
        return None

    # P6
    buf += format
    size = fp.readline()
    buf += size

    # 320 240
    x, y = map(int, re.match('(\d+)\s+(\d+)', size).groups())

    # 255
    maxcol = fp.readline()
    buf += maxcol

    # <rgb data>
    data = fp.read(x*y*3)
    buf += data
    # TODO(brandyn): Make this numpy
    frame = Image.open(StringIO.StringIO(buf))
    return frame


def frame_iter(file_name, frozen=False):
    """
    Args:
        filename: video file to open
        frozen: use the ffmpeg binary extracted from  ./ffmpegbin.tar
                (see vidfeat.freeze_ffmpeg)

    Returns:
        Valid image

    Raises:
        ValueError: There was a problem converting the color.
    """
    if frozen:
        assert 'ffmpegbin.tar' in os.listdir(os.curdir), \
               "convert_video_ffmpeg was called with frozen=True, but \
               ffmpegbin.tar wasn't found. Make sure freeze_ffmpeg() was \
               passed to hadoopy.launch_frozen"

        # Extract the ffmpeg binaries, if needed
        ffmpegdir = os.path.join(os.curdir, 'ffmpegbin')
        ffmpegcmd = os.path.join(ffmpegdir, 'ffmpeg')

        if not os.path.exists(ffmpegdir):
            os.makedirs(ffmpegdir)

        if not os.path.exists(ffmpegcmd) or os.path.getmtime(ffmpegcmd) < \
           os.path.getmtime('ffmpegbin.tar'):
            f = tarfile.open('ffmpegbin.tar')
            f.extractall(ffmpegdir)
            f.close()

        # Launch ffmpeg with subprocess
        args = ('-i %s -f image2pipe -vcodec ppm -' % file_name).split()
        proc = subprocess.Popen([ffmpegcmd] + args,
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            env={'LD_LIBRARY_PATH': ffmpegdir},
                            close_fds=True, shell=False)
    else:
        cmd = 'ffmpeg -i %s -f image2pipe -vcodec ppm -' % file_name
        proc = subprocess.Popen(cmd,
                            stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            close_fds=True, shell=True)

    # Get the FPS from the ffmpeg stderr dump
    fps = _read_fps(proc.stderr)
    # Read and yield PPMs from the ffmpeg pipe
    
    def gen():
        try:
            frame_num = -1
            while True:
                frame = _read_ppm(proc.stdout)
                frame_num += 1
                if frame is None:
                    break
                yield frame_num, frame_num / fps, frame
        finally:
            # Kill the ffmpeg process early if the generator is destroyed
            proc.kill()
            proc.wait()
    return gen()
