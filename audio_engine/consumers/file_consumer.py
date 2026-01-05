import soundfile
import numpy
from .consumer import Consumer


class FileConsumer(Consumer):
	def __init__(self, filename: str, samplerate: int, channels: int):
		self.sound_file = soundfile.SoundFile(filename, mode='w', samplerate=samplerate, channels=channels, subtype='PCM_16')

	def write(self, buffer: numpy.ndarray):
		if buffer.size == 0:
			return
		
		if buffer.ndim == 1:
			buffer = buffer[:, None]
		
		self.sound_file.write(buffer)

	def close(self):
		self.sound_file.close()
