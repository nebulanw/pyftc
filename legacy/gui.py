import os
import json
import threading
import logging
import tkinter as tk
from tkinter import messagebox
import websocket
import obsws_python as obs

# Default configuration
CONFIG_FILE = 'config.json'
DEFAULT_URI = "ws://localhost/stream/display/command/?code=uswatelt"
DEFAULT_OBS = {
    'host': 'localhost',
    'port': 4456,
    'password': 'placeholder'
}
DEFAULT_SCENE_MAPPINGS = {
    'SHOW_PREVIEW': "Matches - Score",
    'SHOW_MATCH_F1': "Matches - Left Field",
    'SHOW_MATCH_F2': "Matches - Right Field",
    'SHOW_RESULTS': "Matches - Score"
}
match_update_types = ['SHOW_PREVIEW', 'SHOW_MATCH', 'SHOW_RESULTS']

class TextHandler(logging.Handler):
    """
    This handler allows logging to a Tkinter Text widget.
    """
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.configure(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.configure(state='disabled')
        self.text_widget.after(0, append)

class SceneSwitcherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.resizable(False, False)
        self.title("OBS Scene Switcher")
        self.protocol("WM_DELETE_WINDOW", self.on_quit)
        # Start disabled until both connections are live
        self.switch_active = False
        self.obs_connected = False
        self.ws_connected = False
        # Chapter marker feature
        self.chapter_active = False
        
        self._load_config()
        self._create_widgets()
        self._setup_logging()
        self._connect_obs()
        self._start_ws_thread()
        self._update_status_labels()

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                self.uri = data.get('uri', DEFAULT_URI)
                self.obs_host = data.get('obs_host', DEFAULT_OBS['host'])
                self.obs_port = data.get('obs_port', DEFAULT_OBS['port'])
                self.obs_password = data.get('obs_password', DEFAULT_OBS['password'])
                self.scene_mappings = data.get('scene_mappings', DEFAULT_SCENE_MAPPINGS)
            except Exception:
                self._set_defaults()
        else:
            self._set_defaults()
        self.valid_scenes = list(self.scene_mappings.values())

    def _set_defaults(self):
        self.uri = DEFAULT_URI
        self.obs_host = DEFAULT_OBS['host']
        self.obs_port = DEFAULT_OBS['port']
        self.obs_password = DEFAULT_OBS['password']
        self.scene_mappings = DEFAULT_SCENE_MAPPINGS

    def _save_config(self):
        data = {
            'uri': self.uri,
            'obs_host': self.obs_host,
            'obs_port': self.obs_port,
            'obs_password': self.obs_password,
            'scene_mappings': self.scene_mappings
        }
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            self.logger.info("Configuration saved to %s", CONFIG_FILE)
        except Exception as e:
            self.logger.error("Failed to save config: %s", e)

    def _create_widgets(self):
        # Log display
        self.log_text = tk.Text(self, state='disabled', height=10, width=80)
        self.log_text.pack(padx=10, pady=(10,5))

        # Status bar
        status_frame = tk.Frame(self)
        status_frame.pack(fill='x', padx=10)
        self.obs_status_var = tk.StringVar()
        self.ws_status_var = tk.StringVar()
        self.switch_status_var = tk.StringVar()
        self.chapter_status_var = tk.StringVar()
        tk.Label(status_frame, textvariable=self.obs_status_var).pack(side='left', padx=5)
        tk.Label(status_frame, textvariable=self.ws_status_var).pack(side='left', padx=5)
        tk.Label(status_frame, textvariable=self.switch_status_var).pack(side='left', padx=5)
        tk.Label(status_frame, textvariable=self.chapter_status_var).pack(side='left', padx=5)

        # Control buttons
        btn_frame = tk.Frame(self)
        btn_frame.pack(padx=10, pady=(5,10))
        toggle_text = "Disable Switch" if self.switch_active else "Enable Switch"
        self.toggle_btn = tk.Button(btn_frame, text=toggle_text, command=self._toggle_switch)
        self.toggle_btn.grid(row=0, column=0, padx=5)
        chapter_text = "Disable Chapters" if self.chapter_active else "Enable Chapters"
        self.chapter_btn = tk.Button(btn_frame, text=chapter_text, command=self._toggle_chapters)
        self.chapter_btn.grid(row=0, column=1, padx=5)
        self.obs_btn = tk.Button(btn_frame, text="Reconnect OBS", command=self._reconnect_obs)
        self.obs_btn.grid(row=0, column=2, padx=5)
        self.ws_btn = tk.Button(btn_frame, text="Reconnect WS", command=self._reconnect_ws)
        self.ws_btn.grid(row=0, column=3, padx=5)
        self.config_btn = tk.Button(btn_frame, text="Configure", command=self._configure)
        self.config_btn.grid(row=0, column=4, padx=5)
        self.quit_btn = tk.Button(btn_frame, text="Quit", command=self.on_quit)
        self.quit_btn.grid(row=0, column=5, padx=5)

    def _setup_logging(self):
        self.logger = logging.getLogger("SceneSwitcher")
        self.logger.setLevel(logging.INFO)
        handler = TextHandler(self.log_text)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        self.logger.addHandler(handler)
        self.logger.info("Application started.")

    def _update_feature_buttons(self, switch_enabled, chapters_enabled):
        self.switch_active = switch_enabled
        self.chapter_active = chapters_enabled
        text = "Disable Switch" if self.switch_active else "Enable Switch"
        self.toggle_btn.config(text=text)
        self.logger.info("Scene switching %s.", 'enabled' if self.switch_active else 'disabled')
        text = "Disable Chapters" if self.chapter_active else "Enable Chapters"
        self.chapter_btn.config(text=text)
        self.logger.info("Chapter markers %s.", 'enabled' if self.chapter_active else 'disabled')

    def _update_status_labels(self):
        self.obs_status_var.set(f"OBS: {'Connected' if self.obs_connected else 'Disconnected'}")
        self.ws_status_var.set(f"WS: {'Connected' if self.ws_connected else 'Disconnected'}")
        self.switch_status_var.set(f"Switch: {'On' if self.switch_active else 'Off'}")
        self.chapter_status_var.set(f"Chapters: {'On' if self.chapter_active else 'Off'}")

    def _connect_obs(self):
        try:
            self.obs_client = obs.ReqClient(host=self.obs_host, port=self.obs_port, password=self.obs_password, timeout=3)
            self.obs_connected = True
            self.logger.info("Connected to OBS WebSocket at %s:%s", self.obs_host, self.obs_port)
        except Exception as e:
            self.obs_connected = False
            self.logger.error("OBS connection failed: %s", e)
            self.switch_active = False
            self.chapter_active = False
            
        self._update_status_labels()

    def _reconnect_obs(self):
        self.logger.info("Reconnecting to OBS WebSocket...")
        self._connect_obs()

    def _start_ws_thread(self):
        self.ws_app = websocket.WebSocketApp(
            self.uri,
            on_open=self._on_ws_open,
            on_message=self._on_message,
            on_error=self._on_ws_error,
            on_close=self._on_ws_close
        )
        self.ws_thread = threading.Thread(target=self._run_ws)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        self.logger.info("WebSocket listener thread started.")

    def _run_ws(self):
        try:
            self.ws_app.run_forever()
        except Exception as e:
            self.ws_connected = False
            self.logger.error("WebSocket run failed: %s", e)
            self._update_feature_buttons(False, False)
            self._update_status_labels()

    def _on_ws_open(self, ws):
        self.ws_connected = True
        self.logger.info("WebSocket connected: %s", self.uri)
        self._update_status_labels()

    def _reconnect_ws(self):
        self.logger.info("Reconnecting to WebSocket %s...", self.uri)
        try:
            self.ws_app.keep_running = False
            self.ws_app.close()
        except Exception:
            pass
        self.ws_connected = False
        self._update_status_labels()
        threading.Timer(0.5, self._start_ws_thread).start()

    def _on_ws_error(self, ws, error):
        self.ws_connected = False
        self.logger.error("WebSocket error: %s", error)
        self._update_feature_buttons(False, False)
        self._update_status_labels()

    def _on_ws_close(self, ws, close_status_code, close_msg):
        self.ws_connected = False
        self.logger.warning("WebSocket closed: %s - %s", close_status_code, close_msg)
        # self._update_feature_buttons(False, False)
        self._update_status_labels()

    def _on_message(self, ws, message):
        # Parse message
        try:
            data = json.loads(message)
        except json.JSONDecodeError:
            return

        # Chapter marker logic (independent of switch)
        if data.get('type') == 'SHOW_PREVIEW' and self.chapter_active:
            match_name = data.get('params', {}).get('matchName')
            if match_name:
                try:
                    self.obs_client.call_vendor_request(
                        vendor_name="streamup-chapter-manager",
                        request_type="setChapterMarker",
                        request_data={"chapterName": match_name}
                    )
                    self.logger.info("Chapter marker set: %s", match_name)
                except Exception as e:
                    self.logger.error("Failed to set chapter marker: %s", e)
                    self.chapter_active = False
                    self.chapter_btn.config(text="Enable Chapters")
                    self._update_status_labels()

        # Scene switching logic
        if not self.switch_active:
            return
        if data.get('init') is True:
            return
        event_type = data.get('type')
        if event_type not in match_update_types:
            return
        if event_type == 'SHOW_MATCH':
            field = data['params'].get('field')
            event_type = f"{event_type}_F{field}"
        if event_type not in self.scene_mappings:
            return
        new_scene = self.scene_mappings[event_type]
        try:
            current = self.obs_client.get_current_program_scene().scene_name

            if current in self.valid_scenes:
                if current != new_scene:
                    self.obs_client.set_current_program_scene(new_scene)
                    self.logger.info("Switched to scene: %s", new_scene)
                else:
                    self.logger.info("Not switching scenes as new scene is the same.")
            else:
                self.logger.info("Not switching scenes as current scene is not recognized.")
        except Exception as e:
            # On OBS failure, mark disconnected, disable features
            self.obs_connected = False
            self.switch_active = False
            self.chapter_active = False
            self.toggle_btn.config(text="Enable Switch")
            self.chapter_btn.config(text="Enable Chapters")
            self.logger.error("Failed to switch scene: %s", e)
            self._update_status_labels()

    def _toggle_switch(self):
        new_state = not self.switch_active
        if new_state and (not self.obs_connected or not self.ws_connected):
            messagebox.showerror("Cannot enable", "Both OBS and WS must be connected to enable scene switching.")
            return
        self.switch_active = new_state
        text = "Disable Switch" if self.switch_active else "Enable Switch"
        self.toggle_btn.config(text=text)
        self.logger.info("Scene switching %s.", 'enabled' if self.switch_active else 'disabled')
        self._update_status_labels()

    def _toggle_chapters(self):
        new_state = not self.chapter_active
        if new_state and (not self.obs_connected or not self.ws_connected):
            messagebox.showerror("Cannot enable", "Both OBS and WS must be connected to enable chapter markers.")
            return
        self.chapter_active = new_state
        text = "Disable Chapters" if self.chapter_active else "Enable Chapters"
        self.chapter_btn.config(text=text)
        self.logger.info("Chapter markers %s.", 'enabled' if self.chapter_active else 'disabled')
        self._update_status_labels()

    def _configure(self):
        """Open a dialog to edit URI, OBS connection, and scene mappings."""
        cfg_win = tk.Toplevel(self)
        cfg_win.resizable(False, False)
        cfg_win.title("Configure Settings")

        # URI
        tk.Label(cfg_win, text="WebSocket URI:").grid(row=0, column=0, sticky='e')
        uri_var = tk.StringVar(value=self.uri)
        tk.Entry(cfg_win, textvariable=uri_var, width=60).grid(row=0, column=1, padx=5, pady=5)

        # OBS connection
        tk.Label(cfg_win, text="OBS Host:").grid(row=1, column=0, sticky='e')
        host_var = tk.StringVar(value=self.obs_host)
        tk.Entry(cfg_win, textvariable=host_var, width=30).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        tk.Label(cfg_win, text="OBS Port:").grid(row=2, column=0, sticky='e')
        port_var = tk.IntVar(value=self.obs_port)
        tk.Entry(cfg_win, textvariable=port_var, width=10).grid(row=2, column=1, sticky='w', padx=5, pady=2)
        tk.Label(cfg_win, text="OBS Password:").grid(row=3, column=0, sticky='e')
        pass_var = tk.StringVar(value=self.obs_password)
        tk.Entry(cfg_win, textvariable=pass_var, width=30).grid(row=3, column=1, sticky='w', padx=5, pady=2)

        # Scene mappings
        tk.Label(cfg_win, text="Scene Mappings:").grid(row=4, column=0, sticky='ne')
        map_frame = tk.Frame(cfg_win)
        map_frame.grid(row=4, column=1, sticky='w')
        entry_vars = {}
        for i, (key, val) in enumerate(self.scene_mappings.items()):
            tk.Label(map_frame, text=key).grid(row=i, column=0, sticky='e')
            var = tk.StringVar(value=val)
            tk.Entry(map_frame, textvariable=var, width=40).grid(row=i, column=1, padx=2, pady=2)
            entry_vars[key] = var

        def apply_changes():
            self.uri = uri_var.get()
            self.obs_host = host_var.get()
            self.obs_port = port_var.get()
            self.obs_password = pass_var.get()
            for k, v in entry_vars.items():
                self.scene_mappings[k] = v.get()
            self.valid_scenes = list(self.scene_mappings.values())
            self._save_config()
            cfg_win.destroy()

        btn_frame = tk.Frame(cfg_win)
        btn_frame.grid(row=5, column=1, pady=10)
        tk.Button(btn_frame, text="Apply", command=apply_changes).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Cancel", command=cfg_win.destroy).pack(side='left', padx=5)

    def on_quit(self):
        if messagebox.askokcancel("Quit", "Are you sure you want to quit? This will stop all connections."):
            self.logger.info("Exiting application.")
            try:
                self.ws_app.keep_running = False
                self.ws_app.close()
            except Exception:
                pass
            self.destroy()
            os._exit(0)

if __name__ == '__main__':
    app = SceneSwitcherApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        os._exit(0)
