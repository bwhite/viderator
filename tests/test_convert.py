import vidfeat
import pyffmpeg

stream = pyffmpeg.VideoStream()
stream.open('may4_sm.mpg')
for x in vidfeat.convert_video(stream, ('frameiter', ['RGB'])):
    print(x)

stream = pyffmpeg.VideoStream()
stream.open('may4_sm.mpg')
out = vidfeat.convert_video(stream, ('videostream',))
print(out)
