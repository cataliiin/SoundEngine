# PrPS Audio Engine

Motor modular de procesare audio în timp real cu interfață grafică intuitivă. Procesează audio din fișiere sau input live, aplică lanțuri de efecte și exportă rezultatele.

## Instalare

```bash
git clone https://github.com/cataliiin/SoundEngine.git

# Creează un virtual environment
python -m venv venv

# Activează venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalează dependențele
pip install -r requirements.txt
```

## Utilizare

### GUI (Interfață Grafică)

Pornește aplicația:
```bash
python gui.py
```

**Pagina Dashboard:**
- Afișare configurație curentă (samplerate, channels, blocksize)
- Status input/output
- Lanțul de efecte active
- Log în timp real

**Pagina Effects:**
- Selectare și adăugare efecte
- Reordonare efecte (Sus/Jos)
- Eliminare efecte
- Editor parametri pentru efectul selectat

**Pagina Configuration:**
- Setări generale (channels, blocksize)
- Input: fișier audio sau live de la microfon
- Output: fișier audio sau redare live
- Selector dispozitiv de sunet și samplerate

### AudioEngine (Utilizare Programatică)

Poți folosi `AudioEngine` direct în propriile aplicații Python:

```python
from audio_engine import AudioEngine

# Inițializare
engine = AudioEngine(samplerate=44100, channels=2, blocksize=1024)

# Configurare input
engine.configure_input("live", device=0)

# Configurare output
engine.configure_output("file", path="output.wav")

# Adăugare efecte
engine.add_effect("gain")
engine.add_effect("echo")
engine.add_effect("reverb")

# Construire și start
engine.build()
engine.start()
```

**Configurare Input:**

```python
# Din fișier
engine.configure_input("file", path="input.wav")

# Live (microfon)
engine.configure_input(
    "live",
    samplerate=44100,
    channels=2,
    blocksize=1024,
    device=1,  # Index dispozitiv (None = default)
    buffer_seconds=0.1
)
```

**Configurare Output:**

```python
# În fișier
engine.configure_output("file", path="output.wav", samplerate=44100, channels=2)

# Live (difuzoare)
engine.configure_output("live", blocksize=1024, device=0)
```

**Gestionare Efecte:**

```python
# Adăugare efecte
engine.add_effect("gain")
engine.add_effect("echo", delay=0.5, decay=0.6)

# Vizualizare efecte
for idx, effect in enumerate(engine.get_effects()):
    print(f"{idx}: {effect.__class__.__name__}")

# Reordonare
engine.reorder_effects(0, 2)

# Eliminare
engine.remove_effect(1)

# Ștergere toate
engine.clear_effects()

# Parametri efect
params = engine.get_effect_default_params("echo")
print(params)  # {'delay': 0.5, 'decay': 0.6}
```

**Control Execuție:**

```python
# Build (pregătire resurse)
engine.build()

# Start (procesare audio)
engine.start()

# Stop
engine.stop()

# Verificări
print(engine.is_built())
print(engine.is_running())

# Context manager
with AudioEngine() as engine:
    engine.configure_input("live")
    engine.configure_output("file", path="out.wav")
    engine.build()
    engine.start()
```

**Listare Dispozitive:**

```python
inputs = engine.list_input_devices()
for idx, name in inputs:
    print(f"{idx}: {name}")

outputs = engine.list_output_devices()
for idx, name in outputs:
    print(f"{idx}: {name}")
```

**Info Configurație:**

```python
input_cfg = engine.get_input_configuration()
output_cfg = engine.get_output_configuration()
```

## Arhitectură Modulară

Proiectul este împărțit în componente independente, fiecare cu o responsabilitate bine definită:

### `audio_engine/engine.py` - AudioEngine (Core)

Clasa principală care coordonează întregul flux audio:

**Metode principale:**
- `__init__(samplerate=44100, channels=1, blocksize=1024)` - Inițializare
- `configure_input(kind, **kwargs)` - Configurare sursă audio
- `configure_output(kind="live", **kwargs)` - Configurare destinație
- `add_effect(effect, **kwargs)` - Adăugare efect
- `remove_effect(index)` - Ștergere efect din lanț
- `clear_effects()` - Ștergere toate efectele
- `reorder_effects(old_idx, new_idx)` - Reordonare efecte
- `build()` - Pregătire resurse (source, consumer)
- `start(frames=None, duration=None, on_chunk=None)` - Execuție procesare
- `stop()` - Oprire execuție
- `is_built()` - Verifică dacă engine-ul e construit
- `is_running()` - Verifică dacă engine-ul e în execuție
- `list_input_devices()` - Listare dispozitive de intrare
- `list_output_devices()` - Listare dispozitive de ieșire
- `get_effects()` - Obține lanțul curent de efecte
- `get_input_configuration()` - Obține config input actual
- `get_output_configuration()` - Obține config output actual
- `get_effects_registry()` - Obține toate efectele disponibile
- `get_effect_default_params(name)` - Parametri default ale unui efect

### `audio_engine/sources/` - Surse Audio

Responsabile cu citirea datelor audio:

- **`file_source.py`** - Citire din fișiere audio (WAV, MP3, FLAC, OGG, etc.)
  - `read(chunk_size)` - Citire buffer de date
  - Proprietăți: `samplerate`, `channels`

- **`live_source.py`** - Capturare real-time de la microfon
  - Buffer circular thread-safe pentru minim latență
  - `read(chunk_size)` - Citire bloc audio din buffer
  - Proprietăți: `samplerate`, `channels`

- **`source.py`** - Interfață abstractă de bază
  - Metodă: `read(chunk_size)` - Trebuie implementată de subclase

### `audio_engine/consumers/` - Consumatori Audio

Responsabile cu scrierea/redarea datelor audio:

- **`file_consumer.py`** - Export în fișier audio
  - `write(data)` - Scriere buffer-ul în fișier
  - Suportă WAV, FLAC, OGG, etc.

- **`live_consumer.py`** - Redare în timp real pe difuzoare
  - `write(data)` - Trimite audio la placa de sunet
  - Redare real-time cu minim latență

- **`consumer.py`** - Interfață abstractă de bază
  - Metodă: `write(data)` - Trebuie implementată de subclase

### `audio_engine/effects/` - Efecte Audio

Procesează semnalul audio în lanț. Fiecare efect moștenește din `Effect`:

**Metode comune:**
- `apply(buffer, samplerate)` - Aplicare efect pe buffer
- `params()` - Obține parametri curenti

**Efecte disponibile:**

- **`gain.py` - Gain/Volume Control**
  - Parametri: `gain` (0.0-2.0) - Factor de amplificare
  - Schimbă amplitudinea semnalului

- **`echo.py` - Echo Effect**
  - Parametri: `delay` (0.1-1.0 sec), `decay` (0.0-1.0)
  - Creeaza ecou cu feedback controlabil
  
- **`distortion.py` - Distortion/Overdrive**
  - Parametri: `amount` (0.0-1.0), `tone` (0.0-1.0)
  - Distorsiune cu tone shaping (high-pass filter)

- **`reverb.py` - Reverb (Spatial Reverb)**
  - Parametri: `decay` (0.1-2.0 sec), `wet` (0.0-1.0)
  - Simulează reverberație în spațiu
  - Wet = balans între semnal original și procesat

- **`tremolo.py` - Tremolo (Amplitude Modulation)**
  - Parametri: `rate` (0.5-20.0 Hz), `depth` (0.0-1.0)
  - Modulează amplitudinea cu LFO (Low Frequency Oscillator)

- **`effect.py`** - Interfață abstractă de bază
  - Metodă abstractă: `apply(buffer, samplerate)` - Trebuie implementată
  - Metodă: `params()` - Returnează dict cu parametri

### `audio_engine/utils/` - Utilitare

- **`ring_buffer.py` - Ring Buffer Thread-Safe**
  - Buffer circular pentru audio live
  - Evită locking, suprascrie datele vechi când e plin
  - Permite read/write concurrent din thread-uri diferite
  - Minim latență și overhead

### `gui.py` - Interfață Grafică (Tkinter)

Interfață user-friendly cu 3 taburi:

- **Dashboard** - Vizualizare status și log
- **Effects** - Gestionare lanț de efecte
- **Configuration** - Configurare engine și I/O

## Fluxul Procesării Audio

```
[Source] --> [Effect 1] --> [Effect 2] --> ... --> [Consumer]
  (File)     (Gain)         (Echo)              (File/Live)
 (Live)      (Distortion)   (Reverb)
            (Tremolo)
```

**Pași:**
1. **Source** citește bufere de audio (1024 samples la 44100Hz = 23ms)
2. Fiecare **Effect** procesează buffer-ul **secvențial**
3. **Consumer** scrie/redă rezultatul final

Toate componentele funcționează cu **numpy arrays** pentru performanță optimă.

## Caracteristici

✅ **Modular** - Componente independente, ușor de extins cu noi efecte sau surse  
✅ **Real-time** - Procesare audio în timp real cu latență < 50ms  
✅ **Flexibil** - Utilizare prin GUI intuitivă sau direct ca bibliotecă Python  
✅ **Multi-efect** - Lanț nelimitat de efecte cu reordonare dinamică  
✅ **Thread-safe** - Buffer circular thread-safe pentru live audio  
✅ **Cross-platform** - Windows, Linux, macOS  
✅ **Builder Pattern** - Configurare prin lanturi de metode  

## Effecte Disponibile

| Efect | Parametri | Descriere |
|-------|-----------|-----------|
| **Gain** | `gain` (0.0-2.0) | Control volum (amplificare/atenuare) |
| **Echo** | `delay` (0.1-1.0), `decay` (0.0-1.0) | Ecou cu feedback controlabil |
| **Distortion** | `amount` (0.0-1.0), `tone` (0.0-1.0) | Distorsiune/overdrive cu tone control |
| **Reverb** | `decay` (0.1-2.0), `wet` (0.0-1.0) | Reverberație spațială |
| **Tremolo** | `rate` (0.5-20.0), `depth` (0.0-1.0) | Modulare amplitudine (LFO) |

## Dependințe

- **numpy** - Procesare array-uri audio pentru performanță
- **sounddevice** - I/O audio live (microfon, difuzoare)
- **soundfile** - Citire/scriere fișiere audio (WAV, FLAC, OGG, etc.)

## Exemple

### Exemplu 1: Procesare Fișier cu Efecte

```python
from audio_engine import AudioEngine

engine = AudioEngine(samplerate=44100, channels=2, blocksize=512)

# Intrare: fișier audio
engine.configure_input("file", path="muzica.wav")

# Ieșire: fișier procesat
engine.configure_output("file", path="muzica_procesata.wav")

# Lanț de efecte
engine.add_effect("gain", gain=0.8)
engine.add_effect("echo", delay=0.3, decay=0.5)
engine.add_effect("reverb", decay=1.2, wet=0.4)

# Procesează
engine.build()
engine.start()

print("Audio procesat cu succes!")
```

### Exemplu 2: Real-time Audio Processing

```python
engine = AudioEngine(samplerate=48000, channels=2)

# Input live de la microfon
engine.configure_input("live", device=0)

# Output live pe difuzoare
engine.configure_output("live", device=0)

# Adaugă amplificare și distorsiune
engine.add_effect("gain", gain=1.2)
engine.add_effect("distortion", amount=0.3, tone=0.7)

engine.build()
engine.start()  # Rulează până la Ctrl+C
```

### Exemplu 3: Listare Dispozitive

```python
engine = AudioEngine()

print("Microfoane disponibile:")
for idx, name in engine.list_input_devices():
    print(f"  {idx}: {name}")

print("\nDifuzoare disponibile:")
for idx, name in engine.list_output_devices():
    print(f"  {idx}: {name}")
```

### Exemplu 4: Context Manager

```python
from audio_engine import AudioEngine

with AudioEngine(samplerate=44100, channels=1) as engine:
    engine.configure_input("file", path="input.wav")
    engine.configure_output("file", path="output.wav")
    engine.add_effect("echo", delay=0.4, decay=0.5)
    engine.build()
    engine.start()
    # Auto-cleanup la ieșire din context
```
