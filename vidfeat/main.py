import imfeat
import pyffmpeg


def frame_iter(stream, image_modes, mod=1):
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
    num = 0
    while 1:
        if num % mod == 0:
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
        elif modes[0] == 'frameiterskip':
            return frame_iter(video, modes[1], modes[2])
    else:
        raise ValueError('Unknown image type')
