from abc import ABC, abstractmethod
import numpy

"""

Clasa abstracte pentru consumatori

"""

class Consumer(ABC):

    @abstractmethod
    def write(self, data: numpy.ndarray):
	    raise NotImplementedError()
        