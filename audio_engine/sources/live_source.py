import sounddevice
import numpy
from .source import Source
from ..utils.ring_buffer import RingBuffer


class LiveSource(Source):
	def __init__(
		self,
		samplerate: int = 44100,
		channels: int = 1,
		blocksize: int = 1024,
		device=None,
		buffer_seconds: float = 2.0,
	):
		self.samplerate = samplerate
		self.channels = channels
		self._blocksize = blocksize

		# Use smaller buffer (3-4 blocks) instead of 2 seconds for lower latency
		capacity_frames = max(self._blocksize * 4, int(self.samplerate * buffer_seconds))
		self.ring_buffer = RingBuffer(capacity_frames=capacity_frames, channels=self.channels)

		def callback(indata, frames, time, status):
			self.ring_buffer.write(indata.copy())

		self._stream = sounddevice.InputStream(
			samplerate=self.samplerate,
			channels=self.channels,
			blocksize=self._blocksize,
			callback=callback,
			device=device,
		)
		self._stream.start()

	def read(self, num_frames: int) -> numpy.ndarray:
		data = self.ring_buffer.read(num_frames, block=True, timeout=1.0)
		if data.size == 0:
			return numpy.empty((0, self.channels), dtype=numpy.float32)
		return data

	def close(self):
		try:
			self._stream.stop()
			self._stream.close()
		except Exception:
			pass    

