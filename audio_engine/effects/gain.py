from .effect import Effect
import numpy as np


class GainEffect(Effect):

    def __init__(self, gain_db: float = 0.0):
        self.gain_db = float(gain_db)

    # conversie db in factor linear
    def _lin(self) -> float:
        return float(10.0 ** (self.gain_db / 20.0))

    def apply(self, buffer: np.ndarray, samplerate: int) -> np.ndarray:
        if buffer.size == 0:
            return buffer
        x = buffer.astype(np.float32, copy=False)
        return x * self._lin()

    def params(self) -> dict:
        return {"gain_db": self.gain_db}
