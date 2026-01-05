from typing import List
from sources.source import Source
from consumers.consumer import Consumer
from effects.effect import Effect

"""
Clasa care conecteaza o sursa la un consumator
si aplica efecte
"""

class Tunnel:
	def __init__(self, source: Source, consumer: Consumer):
		self.source = source
		self.consumer = consumer
		self.effects: List[Effect] = []

	def add_effect(self, effect: Effect):
		self.effects.append(effect)

	def process_and_deliver(self, num_frames: int):
		buf = self.source.read(num_frames)
		if buf.size == 0:
			return False

		if buf.ndim == 1:
			buf = buf[:, None]

		for eff in self.effects:
			buf = eff.apply(buf, getattr(self.source, 'samplerate', 44100))

		self.consumer.write(buf)
		return True

