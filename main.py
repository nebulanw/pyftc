import json
import logging
import threading
import tkinter as tk
from tkinter import ttk

import obsws_python as obs
import websocket

import libraries.config_manager as config_manager
from handlers import ftc_chapter, ftc_scene
from libraries.exceptions import OBSWebSocketException
from libraries.text_handler import TextHandler
from libraries.url_frame import URLFrame

class OBSConnectionContainer():
    def __init__(self):
        self.client: obs.ReqClient = None


class PyFTC(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_manager = config_manager.ConfigurationManager('config.ini')

        self.title("PyFTC")
        self.iconbitmap("pyftc.ico")

        self.geometry('600x820') # TODO: make the view scrollable
        self.minsize(600, 820)

        self.log_text = tk.Text(self, state='disabled', height=6)
        self.log_text.pack(padx=10, pady=(10, 5))
        self.logger = logging.getLogger("PyFTC")
        # self.logger.setLevel(logging.DEBUG)
        self.logger.setLevel(logging.INFO)
        self.logger_handler = TextHandler(self.log_text)
        self.logger_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(message)s",
            "%H:%M:%S"
        ))
        self.logger.addHandler(self.logger_handler)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', padx=10, pady=10, expand=True)

        self.obs = OBSConnectionContainer()

        self.scorekeeper_connected = False
        self.obs_connected = False

        self.scorekeeper_status_var = tk.StringVar()
        self.obs_status_var = tk.StringVar()
        self.scorekeeper_url_var = tk.StringVar(value=self.config_manager.get_scorekeeper_ws())
        self.obs_url_var = tk.StringVar(value=self.config_manager.get_obs_ws_host())
        self.obs_port_var = tk.IntVar(value=self.config_manager.get_obs_ws_port())
        self.obs_pw_var = tk.StringVar(value=self.config_manager.get_obs_ws_pw())

        self.set_up_tab()
        self.update_status_labels()
        self.scene_handler = ftc_scene.FTCSceneHandler(self.config_manager, self.notebook, self.obs, self.logger)
        self.clipper_handler = ftc_chapter.FTCChapterHandler(self.config_manager, self.notebook, self.obs, self.logger)

        # NOTE: OBS connection must happen first on init.
        # If it's second it breaks the scorekeeper thread. No idea why.
        self.reconnect_obs_ws()
        self.start_ws_thread()

    def update_status_labels(self):
        self.scorekeeper_status_var.set(f"Status: {'Connected' if self.scorekeeper_connected else 'Disconnected'}")
        self.obs_status_var.set(f"Status: {'Connected' if self.obs_connected else 'Disconnected'}")

    def set_up_tab(self):
        self.frame = ttk.Frame(self.notebook)

        self.scorekeeper_frame = ttk.Labelframe(self.frame, text='Scorekeeper')
        self.scorekeeper_status_frame = ttk.Frame(self.scorekeeper_frame)

        self.scorekeeper_lbl = ttk.Label(self.scorekeeper_status_frame, textvariable=self.scorekeeper_status_var)
        self.scorekeeper_lbl.pack(side='left', padx=5, pady=5)

        self.scorekeeper_btn = ttk.Button(self.scorekeeper_status_frame, text='Reconnect', command=self.reconnect_ws_thread)
        self.scorekeeper_btn.pack(side='left')

        self.scorekeeper_status_frame.pack(anchor='nw', fill='x', expand=True)

        self.scorekeeper_url_frame = URLFrame('WebSocket URL:', self.scorekeeper_url_var, self.scorekeeper_frame)
        self.scorekeeper_frame.pack(fill='x', padx=5, pady=5)

        self.obs_frame = ttk.Labelframe(self.frame, text='OBS Studio')
        self.obs_status_frame = ttk.Frame(self.obs_frame)

        self.obs_lbl = ttk.Label(self.obs_status_frame, textvariable=self.obs_status_var)
        self.obs_lbl.pack(side='left', padx=5, pady=5)

        self.obs_btn = ttk.Button(self.obs_status_frame, text='Reconnect', command=self.reconnect_obs_ws)
        self.obs_btn.pack(side='left')

        self.obs_status_frame.pack(anchor='nw', fill='x', expand=True)

        self.obs_url_frame = URLFrame('Host:', self.obs_url_var, self.obs_frame)
        self.obs_port_frame = URLFrame('Port:', self.obs_port_var, self.obs_frame)
        self.obs_pw_frame = URLFrame('Pass:', self.obs_pw_var, self.obs_frame)

        self.obs_frame.pack(fill='x', padx=5, pady=5)

        self.save_btn = ttk.Button(self.frame, text='Save', command=self.save_config)
        self.save_btn.pack()

        self.frame.pack(fill='x', padx=5, pady=5)
        self.notebook.add(self.frame, text='General')

    def save_config(self):
        self.config_manager.set_scorekeeper_ws(self.scorekeeper_url_var.get())
        self.config_manager.set_obs_ws_host(self.obs_url_var.get())
        self.config_manager.set_obs_ws_port(self.obs_port_var.get())
        self.config_manager.set_obs_ws_pw(self.obs_pw_var.get())
        self.config_manager.save_config()

    def handle_message(self, ws, message: str):
        if not self.obs_connected:
            return

        # ignore pong
        try:
            message_dec = json.loads(message)
        except json.JSONDecodeError:
            return
        
        # ignore flood of init messages on connection
        if 'init' in message_dec and message_dec['init'] is True:
            return

        if 'type' not in message_dec:
            return

        # self.logger.debug("Received valid message %s", message_dec)

        try:
            self.scene_handler.handle_message(message_dec)
            self.clipper_handler.handle_message(message_dec)
        except OBSWebSocketException:
            self.logger.error("Failed to handle scorekeeper event: OBS WebSocket unavailable")
        except Exception as e:
            self.logger.critical("Failed to handle scorekeeper event: %s", type(e).__name__)
            # self.logger.critical("%s", e)

    def reconnect_obs_ws(self):
        self.obs_conn_thread = threading.Thread(target=self.reconnect_obs_ws_thread)
        self.obs_conn_thread.daemon = True
        self.obs_conn_thread.start()

    def reconnect_obs_ws_thread(self):
        try:
            if self.obs.client is not None:
                self.obs.client.disconnect()
            self.obs_connected = False
            self.update_status_labels()
            self.obs.client = obs.ReqClient(
                host=self.config_manager.get_obs_ws_host(),
                port=self.config_manager.get_obs_ws_port(),
                password=self.config_manager.get_obs_ws_pw(),
                timeout=1
            )
            try:
                self.obs.client.get_version() # equivalent to ping
                self.obs_connected = True
                self.update_status_labels()
                self.logger.info("Connected to OBS WebSocket")
            except Exception as e:
                self.obs_connected = False
                self.update_status_labels()
                self.logger.error("Couldn't connect to OBS WebSocket: %s", type(e).__name__)

        except Exception as e:
            self.obs_connected = False
            self.update_status_labels()
            self.logger.error("Couldn't connect to OBS WebSocket: %s", type(e).__name__)

    def start_ws_thread(self):
        self.scorekeeper_connected = False
        self.update_status_labels()
        self.ws_app = websocket.WebSocketApp(
            self.config_manager.get_scorekeeper_ws(),
            on_open=self.on_ws_open,
            on_message=self.handle_message,
            on_error=self.on_ws_error
        )
        self.ws_thread = threading.Thread(target=self.run_ws)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        self.logger.info("Connecting to scorekeeper WebSocket...")

    def reconnect_ws_thread(self):
        try:
            self.ws_app.keep_running = False
            self.ws_app.close()
        except Exception:
            pass

        threading.Timer(0.5, self.start_ws_thread).start()

    def run_ws(self):
        try:
            self.ws_app.run_forever()
            self.logger.error("Disconnected from scorekeeper WebSocket")
            self.scorekeeper_connected = False
            self.update_status_labels()
        except Exception as e:
            self.logger.error("Failed to connect to scorekeeper WebSocket: %s", type(e).__name__)
            self.scorekeeper_connected = False
            self.update_status_labels()

    def on_ws_open(self, ws):
        self.scorekeeper_connected = True
        self.update_status_labels()
        self.logger.info("Connected to scorekeeper WebSocket")
    
    def on_ws_error(self, ws: websocket.WebSocket):
        self.scorekeeper_connected = False
        self.update_status_labels()
        self.logger.error("Unknown scorekeeper WebSocket error")

if __name__ == '__main__':
    websocket.setdefaulttimeout(1)
    root = PyFTC()
    root.mainloop()
