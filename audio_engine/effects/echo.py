import numpy as np
from .effect import Effect


class EchoEffect(Effect):

    def __init__(self, delay_ms: float = 400.0, feedback: float = 0.35):
        self.delay_ms = float(delay_ms)
        self.feedback = float(np.clip(feedback, 0.0, 0.9))

        self._buffer = None
        self._pos = 0

    def apply(self, buffer: np.ndarray, samplerate: int) -> np.ndarray:
        if buffer.size == 0:
            return buffer
        
        x = buffer.astype(np.float32, copy=False)
        if x.ndim == 1:
            x = x[:, None]

        # conversie delay ms in cate samples avem nevoie
        delay_samples = max(1, int(self.delay_ms * samplerate / 1000.0))
        # aloca buffer
        if self._buffer is None or self._buffer.shape != (delay_samples, x.shape[1]):
            self._buffer = np.zeros((delay_samples, x.shape[1]), dtype=np.float32)
            self._pos = 0

        out = np.empty_like(x, dtype=np.float32) # creaza o variabila ca buffer ( x ) dar goala cu valori neinitializate practic random ( garbage din memorie) pt ca e mai rapid
        # amestecam semnalul original cu cel intarziat
        for i in range(x.shape[0]):
            delayed = self._buffer[self._pos]
            out[i] = x[i] + delayed
            self._buffer[self._pos] = x[i] + delayed * self.feedback
            self._pos = (self._pos + 1) % delay_samples

        return np.clip(out, -1.0, 1.0)

    def params(self) -> dict:
        return {"delay_ms": self.delay_ms, "feedback": self.feedback}
