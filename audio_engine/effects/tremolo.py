import numpy as np
from .effect import Effect


class TremoloEffect(Effect):
    """Modulare de amplitudine"""

    def __init__(self, rate_hz: float = 5.0, depth: float = 0.7):
        self.rate_hz = float(rate_hz)
        self.depth = float(np.clip(depth, 0.0, 1.0))
        self._phase = 0.0

    def apply(self, buffer: np.ndarray, samplerate: int) -> np.ndarray:
        if buffer.size == 0:
            return buffer

        x = buffer.astype(np.float32, copy=False)
        if x.ndim == 1:
            x = x[:, None]

        out = np.empty_like(x, dtype=np.float32) # creaza o variabila ca buffer ( x ) dar goala cu valori neinitializate practic random ( garbage din memorie )
        inc = 2 * np.pi * self.rate_hz / samplerate # incrementul de faza
        for i in range(x.shape[0]):
            oscilator = (1.0 - self.depth) + self.depth * (0.5 * (1.0 + np.sin(self._phase))) # oscilator intre (1-depth) si 1
            out[i] = x[i] * oscilator # aplicam tremolo
            self._phase = (self._phase + inc) % (2 * np.pi)

        return out

    def params(self) -> dict:
        return {"rate_hz": self.rate_hz, "depth": self.depth}
