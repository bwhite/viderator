import vidfeat
import pyffmpeg
import argparse


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('video_file', help=('input video file'))

    ARGS = parser.parse_args()

    stream = pyffmpeg.VideoStream()
    stream.open(ARGS.video_file)
    for x in vidfeat.convert_video(stream, ('frameiter', ['RGB'])):
        print(x)

    for x in vidfeat.convert_video_ffmpeg(ARGS.video_file, ('frameiter', ['RGB'])):
        print(x)

    stream = pyffmpeg.VideoStream()
    stream.open(ARGS.video_file)
    out = vidfeat.convert_video(stream, ('videostream',))
    print(out)
