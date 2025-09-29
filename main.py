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

class OBSConnectionContainer():
    def __init__(self):
        self.client = None


class PyFTC(tk.Tk):
    def __init__(self):
        super().__init__()
        self.config_manager = config_manager.ConfigurationManager('config.ini')

        self.title("PyFTC")
        self.iconbitmap("pyftc.ico")

        self.geometry('600x600')
        self.minsize(400, 500)

        self.log_text = tk.Text(self, state='disabled', height=6)
        self.log_text.pack(padx=10, pady=(10, 5))
        self.logger = logging.getLogger("PyFTC")
        self.logger.setLevel(logging.DEBUG)
        self.logger_handler = TextHandler(self.log_text)
        self.logger_handler.setFormatter(logging.Formatter(
            "[%(asctime)s] %(message)s",
            "%H:%M:%S"
        ))
        self.logger.addHandler(self.logger_handler)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill='both', padx=10, pady=10, expand=True)

        self.obs = OBSConnectionContainer()

        self.scene_handler = ftc_scene.FTCSceneHandler(self.config_manager, self.notebook, self.obs, self.logger)
        self.start_ws_thread()
        self.reconnect_obs_ws()


    def handle_message(self, ws, message: str):
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

        try:
            self.scene_handler.handle_message(message_dec)
        except OBSWebSocketException:
            self.logger.error("Failed to handle scorekeeper event: OBS WebSocket unavailable")
        except Exception as e:
            self.logger.critical("Failed to handle scorekeeper event: %s", type(e).__name__)

    def reconnect_obs_ws(self):
        try:
            self.obs.client = obs.ReqClient(
                host=self.config_manager.get_obs_ws_host(),
                port=self.config_manager.get_obs_ws_port(),
                password=self.config_manager.get_obs_ws_pw(),
                timeout=1
            )
        except Exception as e:
            self.logger.error("Couldn't connect to OBS WebSocket: %s", type(e).__name__)

    def start_ws_thread(self):
        websocket.setdefaulttimeout(1)
        self.ws_app = websocket.WebSocketApp(
            self.config_manager.get_scorekeeper_ws(),
            on_message=self.handle_message,
        )
        self.ws_thread = threading.Thread(target=self.run_ws)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def run_ws(self):
        try:
            self.ws_app.run_forever()
            self.logger.error("Scorekeeper WebSocket disconnected")
        except Exception:
            self.logger.error("Scorekeeper WebSocket disconnected")

if __name__ == '__main__':
    root = PyFTC()
    root.mainloop()
