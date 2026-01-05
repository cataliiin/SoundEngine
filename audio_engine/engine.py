import time

from .effects.effect import Effect
from .effects.gain import GainEffect
from .effects.echo import EchoEffect
from .effects.distortion import DistortionEffect
from .effects.reverb import ReverbEffect
from .effects.tremolo import TremoloEffect

from .sources.file_source import FileSource
from .sources.live_source import LiveSource
from .consumers.file_consumer import FileConsumer
from .consumers.live_consumer import LiveConsumer


class AudioEngine:
	def __init__(self, samplerate=44100, channels=1, blocksize=1024):
		self.samplerate = samplerate
		self.channels = channels
		self.blocksize = blocksize
		
		self._registry = {
			"gain": GainEffect,
			"echo": EchoEffect,
			"distortion": DistortionEffect,
			"reverb": ReverbEffect,
			"tremolo": TremoloEffect,
		}
		
		self._input = None
		self._output = None
		self._effects = []
		self._source = None
		self._consumer = None
		self._built = False
		self._should_stop = False

	#INFO
	def list_input_devices(self):
		import sounddevice as sd
		devices = sd.query_devices()
		return [
			(idx, d["name"])
			for idx, d in enumerate(devices)
			if d.get("max_input_channels", 0) > 0
		]

	def list_output_devices(self):
		import sounddevice as sd
		devices = sd.query_devices()
		return [
			(idx, d["name"])
			for idx, d in enumerate(devices)
			if d.get("max_output_channels", 0) > 0
		]

	# return format:
	# { "kind": "file", "path": "output.wav", ... }
	# or
	# { "kind": "live", "samplerate": 44100, "channels": 2, ... }
	def get_input_configuration(self):
		return self._input

	# return format:
	# { "kind": "file", "path": "output.wav", ... }
	# or
	# { "kind": "live", "samplerate": 44100, "channels": 2, ... }
	def get_output_configuration(self):
		return self._output

	def get_effects_registry(self):
		return dict(self._registry)

	def get_effects(self):
		return list(self._effects)

	def get_effect_default_params(self, name: str):
		cls = self._registry.get(name.lower())
		if not cls:
			raise KeyError(f"Unknown effect: {name}")
		eff = cls()
		return eff.params()


	#CONFIGURATION
	# example:
	# engine.configure_input("file", path="input.wav")
	# engine.configure_input("live", samplerate=44100, channels=2, blocksize=1024, device=1)
	def configure_input(self, kind: str, **kwargs):
		kind = kind.lower()
		if kind == "file":
			path = kwargs.get("path") or kwargs.get("filename")
			if not path:
				raise ValueError()
			self._input = {"kind": "file", "path": path}
		else:
			samplerate = kwargs.get("samplerate", self.samplerate)
			channels = kwargs.get("channels", self.channels)
			blocksize = kwargs.get("blocksize", self.blocksize)
			if samplerate <= 0 or channels <= 0 or blocksize <= 0:
				raise ValueError()
			self._input = {
				"kind": "live",
				"samplerate": samplerate,
				"channels": channels,
				"blocksize": blocksize,
				"device": kwargs.get("device"),
				"buffer_seconds": kwargs.get("buffer_seconds", 0.1),
			}
		return self

	def configure_output(self, kind: str = "live", **kwargs):
		kind = kind.lower()
		if kind == "file":
			path = kwargs.get("path") or kwargs.get("filename")
			if not path:
				raise ValueError()
			self._output = {
				"kind": "file",
				"path": path,
				"samplerate": kwargs.get("samplerate"),
				"channels": kwargs.get("channels"),
			}
		else:
			samplerate = kwargs.get("samplerate")
			channels = kwargs.get("channels")
			blocksize = kwargs.get("blocksize", self.blocksize)
			if blocksize <= 0:
				raise ValueError()
			if samplerate is not None and samplerate <= 0:
				raise ValueError()
			if channels is not None and channels <= 0:
				raise ValueError()
			self._output = {
				"kind": "live",
				"samplerate": samplerate,
				"channels": channels,
				"blocksize": blocksize,
				"device": kwargs.get("device"),
			}
		return self

	def add_effect(self, effect, **kwargs):
		if isinstance(effect, Effect):
			self._effects.append(effect)
		elif isinstance(effect, str):
			name = effect.lower()
			cls = self._registry.get(name)
			if not cls:
				raise KeyError(f"Unknown effect: {effect}")
			self._effects.append(cls(**kwargs))
		elif isinstance(effect, type) and issubclass(effect, Effect):
			instance = effect(**kwargs)
			self._effects.append(instance)
		else:
			raise TypeError()
		return self

	def clear_effects(self):
		self._effects.clear()

	def remove_effect(self, index: int):
		if 0 <= index < len(self._effects):
			self._effects.pop(index)

	def reorder_effects(self, old_index: int, new_index: int):
		if 0 <= old_index < len(self._effects) and 0 <= new_index < len(self._effects):
			effect = self._effects.pop(old_index)
			self._effects.insert(new_index, effect)


	#BUILD, RUN
	def build(self):
		if not self._input:
			raise ValueError()
		
		self._source = self._create_source()
		sr = getattr(self._source, "samplerate", self.samplerate)
		ch = getattr(self._source, "channels", self.channels)
		
		if not self._output:
			self._output = {"kind": "live", "samplerate": sr, "channels": ch}
		
		self._consumer = self._create_consumer(sr, ch)
		self._built = True
		return self

	def start(self, frames=None, duration=None, on_chunk=None):
		self._ensure_built()
		
		chunk = frames or self.blocksize
		start_time = time.perf_counter()
		
		self._should_stop = False
		
		try:
			while not self._should_stop:
				buf = self._source.read(chunk)
				if buf.size == 0:
					break
				
				buf = self._process_buffer(buf)
				
				if on_chunk:
					on_chunk(buf)
				
				self._consumer.write(buf)
				
				if duration and (time.perf_counter() - start_time) >= duration:
					break
		except KeyboardInterrupt:
			pass
		except Exception as e:
			raise
		finally:
			self._cleanup_resources()

	def stop(self):
		self._should_stop = True

	def is_running(self):
		return self._built and not self._should_stop

	def is_built(self):
		return self._built

	#INTERNAL
	def _create_source(self):
		cfg = self._input
		if cfg["kind"] == "file":
			return FileSource(cfg["path"])
		
		return LiveSource(
			samplerate=cfg["samplerate"],
			channels=cfg["channels"],
			blocksize=cfg["blocksize"],
			device=cfg.get("device"),
			buffer_seconds=cfg["buffer_seconds"],
		)

	def _create_consumer(self, samplerate, channels):
		cfg = self._output
		sr = cfg.get("samplerate") or samplerate
		ch = cfg.get("channels") or channels
		
		if cfg["kind"] == "file":
			return FileConsumer(filename=cfg["path"], samplerate=sr, channels=ch)
		
		return LiveConsumer(
			samplerate=sr,
			channels=ch,
			blocksize=cfg.get("blocksize", self.blocksize),
			device=cfg.get("device"),
		)

	def _ensure_built(self):
		if not self._built:
			self.build()

	def _process_buffer(self, buf):
		if buf.ndim == 1:
			buf = buf[:, None]
		
		for eff in self._effects:
			buf = eff.apply(buf, getattr(self._source, "samplerate", self.samplerate))
		
		return buf
	
	def _cleanup_resources(self):
		for comp in [self._source, self._consumer]:
			if comp and hasattr(comp, "close"):
				try:
					comp.close()
				except Exception:
					pass
		self._source = None
		self._consumer = None
		self._built = False



	def __enter__(self):
		return self

	def __exit__(self, *args):
		self.stop()
