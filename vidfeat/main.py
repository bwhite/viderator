import imfeat
import pyffmpeg
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
        #print line
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
    x,y = map(int, re.match('(\d+)\s+(\d+)', size).groups())

    # 255
    maxcol = fp.readline()
    buf += maxcol

    # <rgb data>
    data = fp.read(x*y*3)
    buf += data

    frame = Image.open(StringIO.StringIO(buf))
    return frame


def convert_video_ffmpeg(file_name, image_modes, frozen=False):
    """
    Args:
        filename: video file to open
        modes: list of valid video types (only 'frameiter' is supported)
        frozen: use the ffmpeg binary extracted from  ./ffmpegbin.tar
                (see vidfeat.freeze_ffmpeg)

    Returns:
        Valid image

    Raises:
        ValueError: There was a problem converting the color.
    """

    if not image_modes[0] == 'frameiter':
        raise ValueError('Unknown image type')

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
            with tarfile.open('ffmpegbin.tar') as f:
                f.extractall(ffmpegdir)

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
            frame_num = 0
            while True:
                frame = _read_ppm(proc.stdout)
                if frame is None:
                    break
                yield frame_num, frame_num / fps, frame
                frame_num += 1
        finally:
            # Kill the ffmpeg process early if the generator is destroyed
            proc.kill()
            proc.wait()

    return gen()


def frame_iter(stream, image_modes):
    SEEK_START_ATTEMPTS = 3
    # Use seek to find the first good frame
    for i in range(SEEK_START_ATTEMPTS):
        try:
            stream.tv.seek_to_frame(i)
        except IOError:
            continue
        else:
            break
    fps = stream.tv.get_fps()
    while 1:
        _, num, frame = stream.tv.get_current_frame()[:3]
        yield num, num / fps, imfeat.convert_image(frame, image_modes)
        try:
            stream.tv.get_next_frame()
        except IOError:
            break


def convert_video(video, modes):
    """
    Args:
        image: A pyffmpeg.VideoStream video object
        modes: List of valid video types

    Returns:
        Valid image

    Raises:
        ValueError: There was a problem converting the color.
    """
    if isinstance(video, pyffmpeg.VideoStream):
        if modes[0] == 'videostream':
            return video
        elif modes[0] == 'frameiter':
            return frame_iter(video, modes[1])
    else:
        raise ValueError('Unknown image type')
