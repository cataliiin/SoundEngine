import numpy as np
from .effect import Effect


class ReverbEffect(Effect):
    """
    Reverb ( suma de reflexii ale sunetului pe peretii unei camere ) 
    practic simuleaza o camera 
    reverb mare ( 1 ) simuleaza o camera mare ca o catedrala
    reverb mic ( 0.4 ) simuleaza o camera mica ca o baie
    damping controleaza cat de mult se atenuieaza sunetul in timp


    efect creat cu mult ajutor de la AI
    ca e cam complicat :))
    """

    def __init__(
        self,
        room_size: float = 0.5,
        damping: float = 0.5,
        mix: float = 0.3,
    ):
        self.room_size = float(room_size)
        self.damping = float(damping)
        self.mix = float(mix)
        
        self._combs = None
        self._allpasses = None

    def _check_params(self) -> None:
        self.room_size = float(np.clip(self.room_size, 0.0, 1.0))
        self.damping = float(np.clip(self.damping, 0.0, 1.0))
        self.mix = float(np.clip(self.mix, 0.0, 1.0))

    def apply(self, buffer: np.ndarray, samplerate: int) -> np.ndarray:
        if buffer.size == 0:
            return buffer

        self._check_params()

        x = buffer.astype(np.float32, copy=False)
        if x.ndim == 1:
            x = x[:, None]

        # delay times (samples 44.1kHz, scaled pt samplerate si room_size)
        scale = samplerate / 44100.0
        room_scale = 0.5 + self.room_size * 2.5  # 0.5x la 3x
        comb_delays = [int(1116 * scale * room_scale), int(1188 * scale * room_scale), 
                       int(1277 * scale * room_scale), int(1356 * scale * room_scale)]
        allpass_delays = [int(556 * scale), int(441 * scale)]

        # init buffers
        if self._combs is None:
            self._combs = []
            for delay in comb_delays:
                self._combs.append({
                    'buffer': np.zeros((delay, x.shape[1]), dtype=np.float32),
                    'pos': 0,
                    'damp': np.zeros(x.shape[1], dtype=np.float32)
                })
            
            self._allpasses = []
            for delay in allpass_delays:
                self._allpasses.append({
                    'buffer': np.zeros((delay, x.shape[1]), dtype=np.float32),
                    'pos': 0
                })

        # feedback mai puternic la room_size mare
        fb = 0.5 + self.room_size * 0.4 

        out = np.empty_like(x, dtype=np.float32)

        for i in range(x.shape[0]):
            # parallel comb filters cu damping
            comb_sum = np.zeros(x.shape[1], dtype=np.float32)
            
            for comb in self._combs:
                buf = comb['buffer']
                pos = comb['pos']
                damp_state = comb['damp']
                
                # citeste delayed
                delayed = buf[pos]
                
                # damping lowpass
                damp_state[:] = damp_state * (1.0 - self.damping) + delayed * self.damping
                
                # adauga la suma
                comb_sum += delayed
                
                # scrie cu feedback damped
                buf[pos] = x[i] + damp_state * fb
                comb['pos'] = (pos + 1) % len(buf)
            
            # normalizeaza (4 combs)
            allpass_in = comb_sum * 0.25
            
            # series allpass pt diffusion
            for allpass in self._allpasses:
                buf = allpass['buffer']
                pos = allpass['pos']
                
                delayed = buf[pos]
                
                
                allpass_out = -allpass_in + delayed
                buf[pos] = allpass_in + delayed * 0.5
                
                allpass_in = allpass_out
                allpass['pos'] = (pos + 1) % len(buf)
            
            wet_gain = 1.0 + self.room_size * 0.5  # boost la room_size mare
            wet = allpass_in * wet_gain
            out[i] = x[i] * (1.0 - self.mix) + wet * self.mix

        return np.clip(out, -1.0, 1.0)

    def params(self) -> dict:
        return {
            "room_size": self.room_size,
            "damping": self.damping,
            "mix": self.mix,
        }
