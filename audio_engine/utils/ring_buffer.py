import threading
import numpy as np
import time


class RingBuffer:
    """
    Buffer circular thread safe
    Suprascrie automat datele vechi cannd e plin
    
    """
    
    def __init__(self, capacity_frames: int, channels: int):
        """        
            capacity_frames: Numar maxim de frame-uri audio
            channels: Numar canale (1=mono, 2=stereo)
        """
        if capacity_frames <= 0:
            raise ValueError("capacity_frames must be > 0")
        if channels <= 0:
            raise ValueError("channels must be > 0")
        
        self._buffer = np.zeros((capacity_frames, channels), dtype=np.float32)
        self._capacity = capacity_frames
        self._channels = channels
        
        self._write_pos = 0
        self._read_pos = 0
        self._size = 0
        
        self._lock = threading.Lock()
        self._data_available = threading.Condition(self._lock)
    
    def available(self) -> int:
        with self._lock:
            return self._size
    
    
    def _copy_into_buffer(self, data: np.ndarray):
        """
        Uz intern: copiaza date in buffer la pozitia curenta de scriere
        Gestioneaza wrap around automat 
        Caller trebuie sa detina lock.
        
        """
        num_frames = data.shape[0]
        end_pos = (self._write_pos + num_frames) % self._capacity
        
        if self._write_pos + num_frames <= self._capacity:
            self._buffer[self._write_pos:self._write_pos + num_frames] = data
        else:
            first_chunk = self._capacity - self._write_pos
            self._buffer[self._write_pos:] = data[:first_chunk]
            self._buffer[:end_pos] = data[first_chunk:]
        
        self._write_pos = end_pos
    
    
    def _copy_from_buffer(self, num_frames: int) -> np.ndarray:
        """
        Uz intern: copiaza date din buffer la pozitia curenta de citire.
        Gestioneaza wrap around automat
        Caller trebuie sa detina lock

        
        returneaza date audio copiate (num_frames, channels)
        """
        end_pos = (self._read_pos + num_frames) % self._capacity
        
        if self._read_pos + num_frames <= self._capacity:
            output = self._buffer[self._read_pos:self._read_pos + num_frames].copy()
        else:
            first_chunk = self._capacity - self._read_pos
            output = np.vstack((
                self._buffer[self._read_pos:],
                self._buffer[:end_pos]
            ))
        
        self._read_pos = end_pos
        return output
    
    
    def write(self, data: np.ndarray):
        """
        Scrie frame-uri audio in buffer (apelat din callback thread)
        Suprascrie automat datele vechi daca e plin
        Normalizeaza format si notifica thread-urile care asteapta
        
        """
        if data.size == 0:
            return
        
        # Normalizeaza array-uri mono 1D la format 2D (N,) -> (N, 1)
        if data.ndim == 1:
            data = data[:, None]
        
        # Valideaza numar canale
        if data.shape[1] != self._channels:
            raise ValueError(
                f"Channel mismatch: got {data.shape[1]}, expected {self._channels}"
            )
        
        data = data.astype(np.float32, copy=False)
        num_frames = data.shape[0]
        
        with self._lock:
            if num_frames >= self._capacity:
                self._copy_into_buffer(data[-self._capacity:])
                self._read_pos = self._write_pos
                self._size = self._capacity
            else:
                overflow = max(0, self._size + num_frames - self._capacity)
                
                if overflow > 0:
                    self._read_pos = (self._read_pos + overflow) % self._capacity
                    self._size -= overflow
                
                self._copy_into_buffer(data)
                self._size += num_frames
            
            self._data_available.notify_all()
    
    
    def read(self, num_frames: int, block: bool = True, 
             timeout: float | None = None) -> np.ndarray:
        """
        Citeste frame-uri audio din buffer (apelat din main thread).
        
        num_frames: Numar frame-uri de citit
        block: Daca True asteapta date, daca False returneaza imediat
        timeout: Secunde maxime de asteptare (None = infinit), doar daca block=True
        
        returneaza:
            Date audio (frames_reale, canale) unde frames_reale <= num_frames.
            Returneaza array gol (0, canale) daca nu sunt date si nu blocheaza.
        """
        if num_frames <= 0:
            return np.empty((0, self._channels), dtype=np.float32)
        
        with self._lock:
            if block:
                if timeout is None:
                    while self._size < num_frames:
                        self._data_available.wait()
                else:
                    deadline = time.time() + timeout
                    while self._size < num_frames:
                        remaining = deadline - time.time()
                        if remaining <= 0:
                            break  # Timeout expirat
                        self._data_available.wait(remaining)
            
            frames_to_read = min(num_frames, self._size)
            
            if frames_to_read == 0:
                return np.empty((0, self._channels), dtype=np.float32)
            
            output = self._copy_from_buffer(frames_to_read)
            self._size -= frames_to_read
            
            return output
