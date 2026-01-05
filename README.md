# PrPS Audio Engine

Motor de procesare audio în timp real cu interfață grafică, care suportă aplicarea de efecte audio pe fișiere sau input live.

## Instalare

```bash
# Creează un virtual environment
python -m venv venv

# Activează venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Instalează dependențele
pip install -r requirements.txt
```

## Utilizare

Pornește aplicația:
```bash
python gui.py
```

### Funcționalități

**Surse Audio:**
- Fișier audio (WAV, MP3, FLAC, etc.)
- Input live de la microfon

**Efecte disponibile:**
- **Gain** - Control volum
- **Echo** - Ecou cu delay ajustabil
- **Distortion** - Distorsiune/overdrive
- **Reverb** - Reverberație
- **Tremolo** - Modulare amplitudine

**Output:**
- Redare live prin difuzoare
- Export în fișier audio

### Utilizare GUI

1. Selectează sursa audio (File/Live)
2. Pentru fișier: alege fișierul audio
3. Pentru live: configurează dispozitivul de input
4. Adaugă efecte din lista disponibilă
5. Ajustează parametrii fiecărui efect
6. Pornește procesarea audio
7. Oprește și salvează (opțional)

## Dependențe

- `numpy` - Procesare array-uri audio
- `sounddevice` - I/O audio live
- `soundfile` - Citire/scriere fișiere audio
