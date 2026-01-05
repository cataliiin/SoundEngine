from abc import ABC, abstractmethod
import numpy

"""

Clasa abstracta pentru surse

"""

class Source(ABC):

	@abstractmethod
	def read(self, num_frames: int) -> numpy.ndarray:
		raise NotImplementedError()

