import numpy as np
from .effect import Effect


class DistortionEffect(Effect):

    def __init__(
        self,
        intensity: float = 5.0,
        mix: float = 1.0,
    ):
        self.intensity = float(max(0.0, intensity))
        self.mix = float(mix)

    def _check_params(self) -> None:
        # valideaza parametrii la runtime
        self.intensity = float(max(0.0, self.intensity))
        self.mix = float(np.clip(self.mix, 0.0, 1.0))

    def _db_to_lin(self, db: float) -> float:
        return float(10.0 ** (db / 20.0))

    def apply(self, buffer: np.ndarray, samplerate: int) -> np.ndarray:
        if buffer.size == 0:
            return buffer

        self._check_params()

        x = buffer.astype(np.float32, copy=False)
        if x.ndim == 1:
            x = x[:, None]
        x = np.nan_to_num(x, copy=False)

        dry = x

        # calculeaza gain din intensity
        pre_gain = (self.intensity + 1.0) ** 2

        # amplifica si soft clip
        pre = np.clip(x * pre_gain, -8.0, 8.0)
        driven = np.tanh(pre, dtype=np.float32)

        # compensare nivel
        comp = max(0.25, 1.0 / pre_gain)
        wet = driven * comp

        # blend dry/wet
        out = dry * (1.0 - self.mix) + wet * self.mix
        return np.clip(out, -1.0, 1.0)

    def params(self) -> dict:
        return {
            "intensity": self.intensity,
            "mix": self.mix,
        }
 