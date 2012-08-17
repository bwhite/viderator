import subprocess
import tarfile
import os
import re
import sys
import numpy as np


def _read_fps(stderr):
    """Read the fps from FFMpeg's debug output
    """
    
    while 1:
        line = stderr.readline()
        print line.strip()
        if 'Frame rate very high for a muxer not' in line:
            raise IOError(line)
        if ': No such file or directory' in line:
            raise IOError(line)
        if not line:
            raise IOError("couldn't parse FPS from ffmpeg stderr")
        # Method 0
        # Stream #0.0: Video: mpeg4, yuv420p, 1280x720 [PAR 1:1 DAR 16:9], 29.97 fps, 29.97 tbr, 29.97 tbn, 30k tbc
        m = re.search('Stream #.* Video: ppm,.* ([\.\d]+) fps\(c\)', line)
        
        if not m is None:
            return float(m.groups()[0])
        # Method 1
        # Stream #0:0(und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 1280x720 [SAR 1:1 DAR 16:9], 1984 kb/s, 29.97 fps, 29.97 tbr, 30k tbn, 59.94 tbc
        # Stream #0:0(und): Video: h264 (High) (avc1 / 0x31637661), yuv420p, 640x360 [SAR 1:1 DAR 16:9], 751 kb/s, 25 fps, 25 tbr, 25k tbn, 50 tbc
        m = re.search('Stream #.* Video: .* ([\.\d]+) fps', line)
        if not m is None:
            return float(m.groups()[0])


def _read_ppm(fp):
    """Read one PPM image at a from a stream (ffmpeg image2pipe output)
    """
    l = fp.readline()[:-1]
    assert l == 'P6'
    l = fp.readline()[:-1]
    try:
        cols, rows = map(int, l.split())
    except ValueError:  # No more images
        return
    l = fp.readline().strip()
    try:
        assert l == '255'
    except:
        print repr(l)
        raise
    frame = np.frombuffer(fp.read(cols * rows * 3), dtype=np.uint8).reshape((rows, cols, 3))
    # Flip from RGB to BGR
    return np.ascontiguousarray(frame[:, :, ::-1])


def frame_iter(file_name, frozen=False, frame_skip=1):
    """
    Args:
        filename: video file to open
        frozen: use the ffmpeg binary extracted from  ./ffmpegbin.tar
            (see vidfeat.freeze_ffmpeg)
        frame_skip: How many frames to increment by (default 1 produces all frames,
            2 skips every other one)

    Yields:
        Tuple of frame_num, frame_time, frame where
        frame_num: Current frame number (starts at 0)
        frame_time: Current video time (starts at 0., uses FPS taken from ffmpeg)
        frame: Numpy array (bgr)

    Raises:
        IOError: Problem reading from ffmpeg
    """
    assert frame_skip > 0 and isinstance(frame_skip, int)
    frame_skip = int(max(frame_skip, 1))
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
    proc.stderr.close()
    # Read and yield PPMs from the ffmpeg pipe
    try:
        frame_num = -1
        while True:
            frame = _read_ppm(proc.stdout)
            frame_num += 1
            if frame is None:
                break
            if frame_num % frame_skip == 0:
                yield frame_num, frame_num / fps, frame
    finally:
        # Kill the ffmpeg process early if the generator is destroyed
        proc.kill()
        proc.wait()
