import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk
from pathlib import Path

from audio_engine import AudioEngine

STANDARD_SAMPLERATES = [44100, 48000, 88200, 96000, 192000]

class AudioEngineGUI:
    def __init__(self, engine: AudioEngine | None = None):
        self.engine = engine or AudioEngine()

        self.root = tk.Tk()
        self.root.title("Audio Engine")
        self.root.geometry("480x650")
        self.root.minsize(480, 650)
        style = ttk.Style(self.root)
        style.theme_use("clam")
        base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))  # pyinstaller support
        icon_path = base_path / "icon.png"
        if icon_path.exists():
            try:
                self._icon_img = tk.PhotoImage(file=icon_path)  # keep ref to avoid GC
                self.root.iconphoto(True, self._icon_img)
            except tk.TclError:
                pass

        self._running_thread: threading.Thread | None = None
        self.status_var = tk.StringVar(value="Stopped")

        # General settings vars
        self.samplerate_var = tk.IntVar(value=self.engine.samplerate)
        self.channels_var = tk.IntVar(value=self.engine.channels)
        self.blocksize_var = tk.IntVar(value=self.engine.blocksize)

        # Input vars
        self.input_mode_var = tk.StringVar(value="live")
        self.input_path_var = tk.StringVar(value="")
        self.input_device_var = tk.StringVar(value="")
        self.input_samplerate_var = tk.IntVar(value=self.engine.samplerate)

        # Output vars
        self.output_mode_var = tk.StringVar(value="live")
        self.output_path_var = tk.StringVar(value="")
        self.output_device_var = tk.StringVar(value="")

        # Effects
        self.available_effects = sorted(self.engine.get_effects_registry().keys())
        self.effect_add_var = tk.StringVar(value=self.available_effects[0] if self.available_effects else "")
        self.effect_param_vars: dict[str, tk.Variable] = {}

        self.summary_var = tk.StringVar(value="Config not applied yet.")
        self.general_summary_var = tk.StringVar(value="")
        self.io_summary_var = tk.StringVar(value="")
        self.effects_summary_var = tk.StringVar(value="")

        self._build_ui()
        self._apply_default_configuration()
        self._refresh_dashboard_summary()

    # UI build
    def _build_ui(self):
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill="both", expand=True)

        notebook = ttk.Notebook(main_container)
        notebook.pack(fill="both", expand=True)

        self.dashboard_tab = ttk.Frame(notebook)
        self.effects_tab = ttk.Frame(notebook)
        self.config_tab = ttk.Frame(notebook)

        notebook.add(self.dashboard_tab, text="Dashboard")
        notebook.add(self.effects_tab, text="Effects")
        notebook.add(self.config_tab, text="Configuration")

        self._build_dashboard_tab()
        self._build_effects_tab()
        self._build_config_tab()
        self._build_footer()

    def _build_dashboard_tab(self):
        container = ttk.Frame(self.dashboard_tab)
        container.pack(fill="both", expand=True, padx=8, pady=8)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        general_card = ttk.LabelFrame(container, text="General")
        general_card.grid(row=0, column=0, sticky="nsew", padx=(0, 4), pady=(0, 8))
        ttk.Label(general_card, textvariable=self.general_summary_var, anchor="nw", justify="left", font=("TkFixedFont", 9)).pack(fill="both", expand=True, padx=8, pady=6)

        io_card = ttk.LabelFrame(container, text="I/O")
        io_card.grid(row=0, column=1, sticky="nsew", padx=(4, 0), pady=(0, 8))
        ttk.Label(io_card, textvariable=self.io_summary_var, anchor="nw", justify="left", font=("TkFixedFont", 9)).pack(fill="both", expand=True, padx=8, pady=6)

        effects_card = ttk.LabelFrame(container, text="Effects Chain")
        effects_card.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(0, 8))
        ttk.Label(effects_card, textvariable=self.effects_summary_var, anchor="nw", justify="left", font=("TkFixedFont", 9)).pack(fill="both", expand=True, padx=8, pady=6)

        log_frame = ttk.LabelFrame(container, text="Log")
        log_frame.grid(row=2, column=0, columnspan=2, sticky="nsew")
        container.rowconfigure(2, weight=1)
        self.log_text = tk.Text(log_frame, height=18, state="disabled", wrap="word")
        scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_config_tab(self):
        general_frame = ttk.LabelFrame(self.config_tab, text="General")
        general_frame.pack(fill="x", padx=8, pady=6)

        self._add_labeled_spinbox(general_frame, "Channels", self.channels_var, from_=1, to=8, step=1, row=0)
        self._add_labeled_spinbox(general_frame, "Blocksize", self.blocksize_var, from_=64, to=4096, step=64, row=1)

        # Input
        input_frame = ttk.LabelFrame(self.config_tab, text="Input")
        input_frame.pack(fill="x", padx=8, pady=6)
        self._build_io_section(input_frame, is_input=True)

        # Output
        output_frame = ttk.LabelFrame(self.config_tab, text="Output")
        output_frame.pack(fill="x", padx=8, pady=6)
        self._build_io_section(output_frame, is_input=False)

        ttk.Button(self.config_tab, text="Apply", command=self._apply_configuration).pack(pady=8)

    def _build_io_section(self, parent: ttk.LabelFrame, is_input: bool):
        mode_var = self.input_mode_var if is_input else self.output_mode_var
        path_var = self.input_path_var if is_input else self.output_path_var
        device_var = self.input_device_var if is_input else self.output_device_var
        samplerate_var = self.input_samplerate_var if is_input else None

        radio_row = ttk.Frame(parent)
        radio_row.pack(fill="x", pady=2, padx=4)
        ttk.Radiobutton(radio_row, text="File", value="file", variable=mode_var, command=self._update_io_visibility).pack(side="left", padx=(0, 8))
        ttk.Radiobutton(radio_row, text="Live", value="live", variable=mode_var, command=self._update_io_visibility).pack(side="left")

        # File row
        file_row = ttk.Frame(parent)
        file_row.pack(fill="x", pady=2, padx=4)
        setattr(self, f"{'input' if is_input else 'output'}_file_row", file_row)
        ttk.Label(file_row, text="Path", width=10).pack(side="left")
        ttk.Entry(file_row, textvariable=path_var).pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(file_row, text="...", width=4, command=lambda: self._browse_file(path_var, is_input=is_input)).pack(side="left")

        # Live rows
        live_frame = ttk.Frame(parent)
        live_frame.pack(fill="x", pady=2, padx=4)
        setattr(self, f"{'input' if is_input else 'output'}_live_frame", live_frame)

        ttk.Label(live_frame, text="Device", width=10).pack(side="left")
        combo = ttk.Combobox(live_frame, textvariable=device_var, state="readonly")
        combo.pack(side="left", fill="x", expand=True, padx=4)
        devices = self.engine.list_input_devices() if is_input else self.engine.list_output_devices()
        device_names = [f"{idx}: {name}" for idx, name in devices]
        combo["values"] = device_names
        if device_names:
            device_var.set(device_names[0])

        if samplerate_var is not None:
            sr_frame = ttk.Frame(parent)
            sr_frame.pack(fill="x", pady=2, padx=4)
            setattr(self, "input_sr_frame", sr_frame)
            ttk.Label(sr_frame, text="Samplerate", width=10).pack(side="left")
            sr_combo = ttk.Combobox(sr_frame, textvariable=samplerate_var, values=STANDARD_SAMPLERATES, state="readonly")
            sr_combo.pack(side="left", fill="x", expand=True, padx=4)

        self._update_io_visibility()

    def _add_labeled_spinbox(self, parent, label, var, from_, to, step, row):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
        frame.columnconfigure(1, weight=1)
        ttk.Label(frame, text=label, width=10).grid(row=0, column=0, sticky="w")
        ttk.Spinbox(frame, from_=from_, to=to, increment=step, textvariable=var).grid(row=0, column=1, sticky="ew")

    def _build_effects_tab(self):
        add_row = ttk.Frame(self.effects_tab)
        add_row.pack(fill="x", padx=8, pady=6)
        ttk.Label(add_row, text="Add effect").pack(side="left")
        add_combo = ttk.Combobox(add_row, textvariable=self.effect_add_var, values=self.available_effects, state="readonly")
        add_combo.pack(side="left", fill="x", expand=True, padx=4)
        ttk.Button(add_row, text="Add", command=self._add_effect).pack(side="left")

        list_frame = ttk.Frame(self.effects_tab)
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)

        self.effects_listbox = tk.Listbox(list_frame, height=10)
        self.effects_listbox.pack(side="left", fill="both", expand=True)
        self.effects_listbox.bind("<<ListboxSelect>>", lambda *_: self._render_effect_params())

        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side="left", fill="y", padx=4)
        ttk.Button(btn_frame, text="Up", command=lambda: self._move_effect(-1)).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Down", command=lambda: self._move_effect(1)).pack(fill="x", pady=2)
        ttk.Button(btn_frame, text="Remove", command=self._remove_effect).pack(fill="x", pady=2)

        params_frame = ttk.LabelFrame(self.effects_tab, text="Parameters")
        params_frame.pack(fill="both", expand=True, padx=8, pady=6)
        self.params_container = ttk.Frame(params_frame)
        self.params_container.pack(fill="both", expand=True)

    def _build_footer(self):
        footer = ttk.Frame(self.root, padding=(10, 5, 10, 10))
        footer.pack(side="bottom", fill="x")

        controls = ttk.Frame(footer)
        controls.pack(side="left")
        ttk.Button(controls, text="Start", command=self._start_engine).pack(side="left", padx=(0, 6))
        ttk.Button(controls, text="Stop", command=self._stop_engine).pack(side="left")
        ttk.Label(controls, textvariable=self.status_var, foreground="#2b2b2b").pack(side="left", padx=8)

        ttk.Label(footer, text="by cataliiin").pack(side="right")

    # Actions

    # for showing and hiding IO config (file vs live)
    def _update_io_visibility(self):
        for name in ["input_file_row", "output_file_row", "input_live_frame", "output_live_frame", "input_sr_frame"]:
            widget = getattr(self, name, None)
            if widget is None:
                continue
            widget.pack_forget()

        # Input
        if self.input_mode_var.get() == "file":
            if hasattr(self, "input_file_row"):
                self.input_file_row.pack(fill="x", pady=2, padx=4)
        else:
            if hasattr(self, "input_live_frame"):
                self.input_live_frame.pack(fill="x", pady=2, padx=4)
            if hasattr(self, "input_sr_frame"):
                self.input_sr_frame.pack(fill="x", pady=2, padx=4)

        # Output
        if self.output_mode_var.get() == "file":
            if hasattr(self, "output_file_row"):
                self.output_file_row.pack(fill="x", pady=2, padx=4)
        else:
            if hasattr(self, "output_live_frame"):
                self.output_live_frame.pack(fill="x", pady=2, padx=4)

    def _browse_file(self, var: tk.StringVar, is_input: bool):
        if is_input:
            path = filedialog.askopenfilename()
        else:
            path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("Wave", "*.wav"), ("All", "*.*")])
        if path:
            var.set(path)

    def _apply_default_configuration(self):
        try:
            self.engine.configure_input(
                "live",
                samplerate=self.engine.samplerate,
                channels=self.engine.channels,
                blocksize=self.engine.blocksize,
                device=None,
            )
            self.engine.configure_output("live", blocksize=self.engine.blocksize, device=None)
            self._log("Default configuration applied (default devices).")
        except Exception as exc:
            self._log(f"Failed to apply default config: {exc}")

    def _apply_configuration(self):
        try:
            self.engine.channels = int(self.channels_var.get())
            self.engine.blocksize = int(self.blocksize_var.get())

            # Input config
            if self.input_mode_var.get() == "file":
                path = self.input_path_var.get().strip()
                self.engine.configure_input("file", path=path)
            else:
                device = self._parse_device(self.input_device_var.get())
                sr = int(self.input_samplerate_var.get())
                self.engine.samplerate = sr
                self.engine.configure_input(
                    "live",
                    samplerate=sr,
                    channels=int(self.channels_var.get()),
                    blocksize=int(self.blocksize_var.get()),
                    device=device,
                )

            # Output config
            if self.output_mode_var.get() == "file":
                out_path = self.output_path_var.get().strip()
                self.engine.configure_output("file", path=out_path, samplerate=None, channels=self.engine.channels)
            else:
                device = self._parse_device(self.output_device_var.get())
                self.engine.configure_output("live", blocksize=self.engine.blocksize, device=device)

            self._refresh_dashboard_summary()
            self._log("Configuration applied.")
        except Exception as exc:
            messagebox.showerror("Configuration error", str(exc))
            self._log(f"Configuration failed: {exc}")

    def _parse_device(self, device_label: str) -> int | None:
        if not device_label:
            return None
        try:
            idx_str = device_label.split(":", 1)[0]
            return int(idx_str)
        except (ValueError, IndexError):
            return None

    def _add_effect(self):
        name = self.effect_add_var.get()
        if not name:
            return
        try:
            self.engine.add_effect(name)
            self._log(f"Effect added: {name}")
            self._refresh_effects_list()
        except Exception as exc:
            messagebox.showerror("Add effect", str(exc))
            self._log(f"Failed to add effect {name}: {exc}")

    def _remove_effect(self):
        sel = self._current_effect_index()
        if sel is None:
            return
        self.engine.remove_effect(sel)
        self._log(f"Effect removed at index {sel}")
        self._refresh_effects_list()

    def _move_effect(self, direction: int):
        sel = self._current_effect_index()
        if sel is None:
            return
        new_idx = sel + direction
        self.engine.reorder_effects(sel, new_idx)
        self._refresh_effects_list(select_index=new_idx)
        self._log(f"Effect moved to {new_idx}")

    def _current_effect_index(self) -> int | None:
        sel = self.effects_listbox.curselection()
        if not sel:
            return None
        return int(sel[0])

    def _refresh_effects_list(self, select_index: int | None = None):
        self.effects_listbox.delete(0, tk.END)
        for idx, eff in enumerate(self.engine.get_effects()):
            label = eff.__class__.__name__
            self.effects_listbox.insert(tk.END, f"{idx}: {label}")
        if select_index is not None and 0 <= select_index < self.effects_listbox.size():
            self.effects_listbox.selection_set(select_index)
        self._render_effect_params()
        self._refresh_dashboard_summary()

    def _render_effect_params(self):
        for child in self.params_container.winfo_children():
            child.destroy()
        self.effect_param_vars.clear()

        idx = self._current_effect_index()
        if idx is None:
            ttk.Label(self.params_container, text="Select an effect to edit.").pack(anchor="w", padx=4, pady=4)
            return

        effect = self.engine.get_effects()[idx]
        params = effect.params()

        for row, (name, value) in enumerate(params.items()):
            var = tk.StringVar(value=str(value))
            self.effect_param_vars[name] = var
            frame = ttk.Frame(self.params_container)
            frame.grid(row=row, column=0, sticky="ew", padx=4, pady=2)
            frame.columnconfigure(1, weight=1)
            ttk.Label(frame, text=name, width=12).grid(row=0, column=0, sticky="w")
            ttk.Entry(frame, textvariable=var).grid(row=0, column=1, sticky="ew")

        ttk.Button(self.params_container, text="Apply parameters", command=lambda: self._apply_effect_params(effect)).grid(row=len(params), column=0, sticky="w", padx=4, pady=6)

    def _apply_effect_params(self, effect):
        for name, var in self.effect_param_vars.items():
            new_val = var.get()
            current = getattr(effect, name, None)
            converted = self._transform_value(new_val, current)
            setattr(effect, name, converted)
        self._log(f"Params updated for {effect.__class__.__name__}")

    def _transform_value(self, value: str, current):
        if isinstance(current, bool):
            return value.lower() in {"1", "true", "yes", "on"}
        if isinstance(current, int):
            try:
                return int(float(value))
            except ValueError:
                return current
        if isinstance(current, float):
            try:
                return float(value)
            except ValueError:
                return current
        if isinstance(current, list):
            try:
                import ast
                parsed = ast.literal_eval(value)
                if isinstance(parsed, list):
                    return parsed
            except (ValueError, SyntaxError):
                return current
        return value

    def _refresh_dashboard_summary(self):
        input_cfg = self.engine.get_input_configuration()
        output_cfg = self.engine.get_output_configuration()
        self.summary_var.set("")
        sr_display = "(from file)" if input_cfg and input_cfg.get("kind") == "file" else str(self.engine.samplerate)
        general_lines = [
            f"Samplerate: {sr_display}",
            f"Channels:   {self.engine.channels}",
            f"Blocksize:  {self.engine.blocksize}",
        ]
        io_lines = []
        if input_cfg:
            if input_cfg.get("kind") == "file":
                io_lines.append(f"Input: File")
                io_lines.append(f"  Path: {input_cfg.get('path', 'N/A')}")
            else:
                io_lines.append(f"Input: Live")
                device = input_cfg.get('device')
                io_lines.append(f"  Device: {device if device is not None else 'Default'}")
                io_lines.append(f"  SR: {input_cfg.get('samplerate', 'N/A')}")
        else:
            io_lines.append("Input: Not configured")
        
        io_lines.append("")
        
        if output_cfg:
            if output_cfg.get("kind") == "file":
                io_lines.append(f"Output: File")
                io_lines.append(f"  Path: {output_cfg.get('path', 'N/A')}")
            else:
                io_lines.append(f"Output: Live")
                device = output_cfg.get('device')
                io_lines.append(f"  Device: {device if device is not None else 'Default'}")
        else:
            io_lines.append("Output: Not configured")
        
        effects = [eff.__class__.__name__ for eff in self.engine.get_effects()]
        if effects:
            effects_lines = ["; ".join(effects)]
        else:
            effects_lines = ["(empty)"]

        self.general_summary_var.set("\n".join(general_lines))
        self.io_summary_var.set("\n".join(io_lines))
        self.effects_summary_var.set("\n".join(effects_lines))

    def _start_engine(self):
        if self._running_thread and self._running_thread.is_alive():
            return

        def runner():
            try:
                self.engine.start()
                self._log("Engine stopped.")
                self.status_var.set("Stopped")
            except Exception as exc:
                self._log(f"Engine error: {exc}")
                self.status_var.set("Error")

        try:
            self.engine.build()
            self._log("Engine built.")
            self._running_thread = threading.Thread(target=runner, daemon=True)
            self._running_thread.start()
            self._log("Engine started.")
            self.status_var.set("Running")
        except Exception as exc:
            messagebox.showerror("Start error", str(exc))
            self._log(f"Failed to start: {exc}")
            self.status_var.set("Error")

    def _stop_engine(self):
        if self.engine.is_running():
            self.engine.stop()
            self._log("Stop requested.")
            self.status_var.set("Stopping")
        else:
            self.status_var.set("Stopped")

    def _log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    gui = AudioEngineGUI()
    gui.run()
