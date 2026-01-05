import soundfile
import numpy
from .source import Source

class FileSource(Source):
	def __init__(self, filename: str):
		self.sound_file = soundfile.SoundFile(filename, mode='r')
		self.samplerate = self.sound_file.samplerate
		self.channels = self.sound_file.channels

	def read(self, num_frames: int) -> numpy.ndarray:
		data = self.sound_file.read(frames=num_frames, dtype='float32', always_2d=True)

		if data.size == 0:
			return numpy.empty((0, self.channels), dtype='float32')
		return data

	def close(self):
		self.sound_file.close()