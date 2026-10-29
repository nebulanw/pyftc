import tkinter as tk
from tkinter import ttk
from libraries.exceptions import OBSWebSocketException
import logging
import time
import threading
import os

import libraries.config_manager as config_manager
from libraries.random_str import randomword
from main import OBSConnectionContainer

SUPPORTED_MESSAGES = {
    "show_preview": 'Match preview (SHOW_PREVIEW)',
    "show_match": 'Show match (SHOW_MATCH)',
    "show_results": 'Match results (SHOW_RESULTS)'
}

class FTCChapterHandler():
    def __init__(self, config: config_manager.ConfigurationManager, n: ttk.Notebook, obs: OBSConnectionContainer, logger: logging.Logger):
        self.config = config
        self.notebook = n
        self.obs = obs
        self.logger = logger
        self.stop_flag = threading.Event()
        self.timer_event = threading.Event()
        self.set_default_config()
        self.set_up_tab()
        self.clipper_thread = None
        self.ss_thread = None


    def handle_message(self, message: dict):
        if not self.get_enabled():
            return

        if self.obs.client is None:
            raise OBSWebSocketException()

        msg_type = str(message['type']).lower()
        # self.logger.info("type %s", msg_type)

        if msg_type not in ["show_preview", "start_match", "abort_match", "show_results"]:
            # self.logger.warning("Unsupported event: %s", msg_type)
            return

        msg_match_name = message['params']['matchName']

        if msg_type == "start_match":
            if self.clipper_thread is not None and self.clipper_thread.is_alive():
                self.stop_flag.set()
                self.clipper_thread.join()
            self.clipper_thread = threading.Thread(target=self.run_clipper_thread, kwargs={'match_name': msg_match_name, 'stop_event': self.stop_flag, 'timeout': 173, 'duration': 188})
            self.clipper_thread.daemon = True
            self.stop_flag.clear()
            self.clipper_thread.start()

        if msg_type == "abort_match":
            if self.clipper_thread is not None and self.clipper_thread.is_alive():
                self.stop_flag.set()
                self.clipper_thread.join()
            self.logger.info("Match aborted; thread stopped")

        if msg_type == "show_results":
            if self.ss_thread is not None and self.ss_thread.is_alive():
                self.stop_flag.set()
                self.clipper_thread.join()
                self.timer_event.set()
                self.ss_thread.join()
            self.ss_thread = threading.Thread(target=self.run_res_ss_thread, kwargs={'match_name': msg_match_name, 'timer_event': self.timer_event})
            self.ss_thread.daemon = True
            self.timer_event.clear()
            self.ss_thread.start()
            self.clipper_thread = threading.Thread(target=self.run_clipper_thread, kwargs={'match_name': msg_match_name, 'stop_event': self.stop_flag, 'timeout': 30, 'duration': 45})
            self.clipper_thread.daemon = True
            self.stop_flag.clear()
            self.clipper_thread.start()

        if msg_type == "show_preview":
            if self.ss_thread is not None and self.ss_thread.is_alive():
                self.timer_event.set()
                self.ss_thread.join()
            self.ss_thread = threading.Thread(target=self.run_prev_ss_thread, kwargs={'match_name': msg_match_name, 'timer_event': self.timer_event})
            self.ss_thread.daemon = True
            self.timer_event.clear()
            self.ss_thread.start()

    def run_clipper_thread(self, match_name: str, stop_event: threading.Event, timeout: int, duration: int):
        if not self.obs.client.get_replay_buffer_status().output_active:
            self.logger.warning("Skipping clipper because replay buffer is not active")
            return
        self.logger.info("Started clipper thread")
        # time.sleep(173) # (8s offset) + 15 pre + 2:38 (158s) match + 15 post = 196 buffer
        # 30 sec AUTO + 8 sec wait + 120 sec TELEOP = 158 sec match
        # 15s pre + 158s + 15s post = 188s clip
        # 158s + 15s post = 173s wait
        stop_event.wait(timeout=timeout)
        
        if stop_event.is_set():
            self.logger.info("Stopping clipper thread for %s early", match_name)
            return
        # another sanity check for good measure
        if not self.obs.client.get_replay_buffer_status().output_active:
            self.logger.warning("Skipping clipper because replay buffer is not active")
            return
        # self.obs.client.save_replay_buffer()
        self.logger.info("Saving replay...")
        self.obs.client.send(
            "CallVendorRequest",
            data={
                "vendorName": "replay-buffer-pro",
                "requestType": "SaveClip",
                "requestData": {"duration": str(duration) + "s"}
            }
        )

        self.logger.info("Saved replay for %s", match_name)
        # This doesn't work consistently
        # replay_fname = self.obs.client.send("GetLastReplayBufferReplay", raw=True)
        # print("Replay file info: %s", replay_fname)

    def run_res_ss_thread(self, match_name: str, timer_event: threading.Event):
        timer_event.wait(timeout=11)
        if timer_event.is_set():
            self.logger.info("Stopping result thread")
            return
        scene = self.obs.client.send("GetCurrentProgramScene", raw=True)['currentProgramSceneName']
        dir = self.obs.client.send("GetRecordDirectory", raw=True)['recordDirectory']
        payload = {"sourceName": scene, "imageFormat": "png", "imageFilePath": dir + '\\' + match_name + "_score-" + randomword(5) + ".png"}
        self.obs.client.send("SaveSourceScreenshot", payload, raw=True)
        self.logger.info("Saved match results for %s", match_name)

    def run_prev_ss_thread(self, match_name: str, timer_event: threading.Event):
        timer_event.wait(timeout=2.5)
        if timer_event.is_set():
            self.logger.info("Stopping preview thread")
            return
        scene = self.obs.client.send("GetCurrentProgramScene", raw=True)['currentProgramSceneName']
        dir = self.obs.client.send("GetRecordDirectory", raw=True)['recordDirectory']
        payload = {"sourceName": scene, "imageFormat": "png", "imageFilePath": dir + '\\' + match_name + "_preview-" + randomword(5) + ".png"}
        self.obs.client.send("SaveSourceScreenshot", payload, raw=True)
        self.logger.info("Saved match preview for %s", match_name)

    def set_default_config(self):
        if self.get_enabled() is None:
            self.set_enabled(True)

        self.config.save_config()

    def save_config(self):
        self.set_enabled(self.enabled.get())

        self.config.save_config()

        if self.enabled.get():
            return

        # stop threads if disabling
        # calling join() blocks the UI thread
        if self.clipper_thread is not None and self.clipper_thread.is_alive():
            self.stop_flag.set()
            # self.clipper_thread.join()

        if self.ss_thread is not None and self.ss_thread.is_alive():
            self.timer_event.set()
            # self.ss_thread.join()

    def set_up_tab(self):
        self.frame = ttk.Frame(self.notebook)

        self.enabled = tk.BooleanVar(value=self.get_enabled())
        self.scene_switcher_cb = ttk.Checkbutton(self.frame, text='Enable clipper (beta)', variable=self.enabled)
        self.scene_switcher_cb.pack(anchor='w', padx=5, pady=5)

        self.save_btn = ttk.Button(self.frame, command=self.save_config, text="Save")
        self.save_btn.pack(anchor='nw', padx=5, pady=5, expand=True)

        self.notebook.add(self.frame, text='Clipper')

    def str_to_bool(self, val: str):
        if val == 'False':
            return False
        return True

    def set_enabled(self, value: bool):
        self.config.set_value('clipper', 'enabled', value)

    def get_enabled(self):
        value = self.config.get_value('clipper', 'enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def get_event_enabled(self, event: str):
        value = self.config.get_value('clipper', event + '_enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def get_event_generic(self, key: str):
        return self.config.get_value('clipper', key)

    def set_event_generic(self, key, value):
        self.config.set_value('clipper', key, value)
