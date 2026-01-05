from abc import ABC, abstractmethod
import numpy

"""

Clasa abstracta pentru efecte

"""

class Effect(ABC):

	@abstractmethod
	def apply(self, buffer: numpy.ndarray, samplerate: int) -> numpy.ndarray:
		raise NotImplementedError()

	@abstractmethod
	def params(self) -> dict:
		raise NotImplementedError()

