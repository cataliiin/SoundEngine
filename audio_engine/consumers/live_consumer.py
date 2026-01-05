import sounddevice as sd
import numpy as np
from .consumer import Consumer


class LiveConsumer(Consumer):
	def __init__(self, samplerate: int = 44100, channels: int = 1, blocksize: int = 1024, device=None):
		self.samplerate = samplerate
		self.channels = channels
		self._blocksize = blocksize
		self._stream = sd.OutputStream(samplerate=self.samplerate,
										channels=self.channels,
										blocksize=self._blocksize,
										device=device)
		self._stream.start()

	def write(self, buffer: np.ndarray):
		if buffer.size == 0:
			return
		
		if buffer.ndim == 1:
			buffer = buffer[:, None]
		
		self._stream.write(buffer)

	def close(self):
		try:
			self._stream.stop()
			self._stream.close()
		except Exception:
			pass

