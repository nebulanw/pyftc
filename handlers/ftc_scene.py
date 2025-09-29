import tkinter as tk
from tkinter import ttk
from libraries.exceptions import OBSWebSocketException
import logging

import libraries.config_manager as config_manager

# TODO: stop hardcoding individual events; use below constant
SUPPORTED_MESSAGES = ["show_preview", "show_match", "show_results"]

class EventConfigControls(ttk.Labelframe):
    def __init__(self, frame: ttk.Frame, state_enabled: tk.BooleanVar, state_scene_f1: tk.StringVar, state_scene_f2: tk.StringVar, event_text: str):
        self.parent_frame = frame

        self.frame = ttk.Labelframe(self.parent_frame, text=event_text)

        self.handle_cb = ttk.Checkbutton(self.frame, text='Handle event', variable=state_enabled)
        self.handle_cb.pack(anchor='w', padx=5, pady=5)

        self.scene_f1_frame = ttk.Frame(self.frame)
        self.scene_f1_lbl = ttk.Label(self.scene_f1_frame, text='Scene name (field 1)')
        self.scene_f1_lbl.pack(anchor='w', side='left', padx=5, pady=5)
        self.scene_f1_name = ttk.Entry(self.scene_f1_frame, textvariable=state_scene_f1)
        self.scene_f1_name.pack(side='left', fill='x', padx=(0, 5), expand=True)
        self.scene_f1_frame.pack(side='top', fill='x', expand=True)

        self.scene_f2_frame = ttk.Frame(self.frame)
        self.scene_f2_lbl = ttk.Label(self.scene_f2_frame, text='Scene name (field 2)')
        self.scene_f2_lbl.pack(anchor='w', side='left', padx=5, pady=5)
        self.scene_f2_name = ttk.Entry(self.scene_f2_frame, textvariable=state_scene_f2)
        self.scene_f2_name.pack(side='left', fill='x', padx=(0, 5), expand=True)
        self.scene_f2_frame.pack(side='top', fill='x', expand=True)

        self.frame.pack(fill='x', padx=5, pady=5)

class FTCSceneHandler():
    def __init__(self, config: config_manager.ConfigurationManager, n: ttk.Notebook, obs, logger: logging.Logger):
        self.config = config
        self.notebook = n
        self.obs = obs
        self.logger = logger
        self.set_default_config()
        self.set_up_tab()


    def handle_message(self, message: dict):
        if not self.get_enabled():
            return

        if self.obs.client is None:
            raise OBSWebSocketException()

        msg_type = str(message['type']).lower()

        # silently fail if field param is unsupported. applies to PIT_UPDATE
        if 'params' not in message or 'field' not in message['params']:
            return

        # if we magically have a 3-field event this is a problem
        msg_type += '_f' + str(message['params']['field'])

        try:
            current_scene = self.obs.client.get_current_program_scene().scene_name
            print(current_scene)
        except Exception:
            raise OBSWebSocketException()

        match msg_type:
            case 'show_preview_f1':
                if self.get_show_preview_enabled():
                    self.logger.info(f"Switching to {self.get_show_preview_f1_name()}")
                    self.obs.set_current_program_scene(self.get_show_preview_f1_name())
            case 'show_preview_f2':
                if self.get_show_preview_enabled():
                    self.logger.info(f"Switching to {self.get_show_preview_f2_name()}")
                    self.obs.client.set_current_program_scene(self.get_show_preview_f2_name())
            case 'show_match_f1':
                if self.get_show_match_enabled():
                    self.logger.info(f"Switching to {self.get_show_match_f1_name()}")
                    self.obs.client.set_current_program_scene(self.get_show_match_f1_name())
            case 'show_match_f2':
                if self.get_show_match_enabled():
                    self.logger.info(f"Switching to {self.get_show_match_f2_name()}")
                    self.obs.client.set_current_program_scene(self.get_show_match_f2_name())
            case 'show_results_f1':
                if self.get_show_results_enabled():
                    self.logger.info(f"Switching to {self.get_show_results_f1_name()}")
                    self.obs.client.set_current_program_scene(self.get_show_results_f1_name())
            case 'show_results_f2':
                if self.get_show_results_enabled():
                    self.logger.info(f"Switching to {self.get_show_results_f2_name()}")
                    self.obs.client.set_current_program_scene(self.get_show_results_f2_name())
            case _:
                print(f"Unsupported message type: {msg_type}")

    def set_default_config(self):
        if self.get_enabled() is None:
            self.set_enabled(True)

        if self.get_show_preview_enabled() is None:
            self.set_show_preview_enabled(True)

        if self.get_show_preview_f1_name() is None:
            self.set_show_preview_f1_name('show_preview_f1_name')

        if self.get_show_preview_f2_name() is None:
            self.set_show_preview_f2_name('show_preview_f2_name')

        if self.get_show_match_enabled() is None:
            self.set_show_match_enabled(True)

        if self.get_show_match_f1_name() is None:
            self.set_show_match_f1_name('show_match_f1_name')

        if self.get_show_match_f2_name() is None:
            self.set_show_match_f2_name('show_match_f2_name')

        if self.get_show_results_enabled() is None:
            self.set_show_results_enabled(True)

        if self.get_show_results_f1_name() is None:
            self.set_show_results_f1_name('show_results_f1_name')

        if self.get_show_results_f2_name() is None:
            self.set_show_results_f2_name('show_results_f2_name')
        self.config.save_config()

    def save_config(self):
        self.set_enabled(self.enabled.get())
        self.set_show_preview_enabled(self.show_preview_enabled.get())
        self.set_show_preview_f1_name(self.show_preview_f1_name.get())
        self.set_show_preview_f2_name(self.show_preview_f2_name.get())
        self.set_show_match_enabled(self.show_match_enabled.get())
        self.set_show_match_f1_name(self.show_match_f1_name.get())
        self.set_show_match_f2_name(self.show_match_f2_name.get())
        self.set_show_results_enabled(self.show_results_enabled.get())
        self.set_show_results_f1_name(self.show_results_f1_name.get())
        self.set_show_results_f2_name(self.show_results_f2_name.get())
        self.config.save_config()

    def set_up_tab(self):
        self.frame = ttk.Frame(self.notebook)

        self.enabled = tk.BooleanVar(value=self.get_enabled())
        self.scene_switcher_cb = ttk.Checkbutton(self.frame, text='Enable scene switching', variable=self.enabled)
        self.scene_switcher_cb.pack(anchor='w', padx=5, pady=5)

        self.show_preview_enabled = tk.BooleanVar(value=self.get_show_preview_enabled())
        self.show_preview_f1_name = tk.StringVar(value=self.get_show_preview_f1_name())
        self.show_preview_f2_name = tk.StringVar(value=self.get_show_preview_f2_name())
        self.show_preview_controls = EventConfigControls(self.frame, self.show_preview_enabled, self.show_preview_f1_name, self.show_preview_f2_name, 'Match preview (SHOW_PREVIEW)')

        self.show_match_enabled = tk.BooleanVar(value=self.get_show_match_enabled())
        self.show_match_f1_name = tk.StringVar(value=self.get_show_match_f1_name())
        self.show_match_f2_name = tk.StringVar(value=self.get_show_match_f2_name())
        self.show_match_controls = EventConfigControls(self.frame, self.show_match_enabled, self.show_match_f1_name, self.show_match_f2_name, 'Show match (SHOW_MATCH)')

        self.show_results_enabled = tk.BooleanVar(value=self.get_show_results_enabled())
        self.show_results_f1_name = tk.StringVar(value=self.get_show_results_f1_name())
        self.show_results_f2_name = tk.StringVar(value=self.get_show_results_f2_name())
        self.show_results_controls = EventConfigControls(self.frame, self.show_results_enabled, self.show_results_f1_name, self.show_results_f2_name, 'Show results (SHOW_RESULTS)')

        self.save_btn = tk.Button(self.frame, command=self.save_config, text="Save")
        self.save_btn.pack(anchor='nw', padx=5, pady=5, expand=True)

        self.notebook.add(self.frame, text='Scenes')

    def str_to_bool(self, val: str):
        if val == 'False':
            return False
        return True

    def set_enabled(self, value: bool):
        self.config.set_value('scene', 'enabled', value)

    def get_enabled(self):
        value = self.config.get_value('scene', 'enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def set_show_preview_enabled(self, value: bool):
        self.config.set_value('scene', 'show_preview_enabled', value)

    def get_show_preview_enabled(self):
        value = self.config.get_value('scene', 'show_preview_enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def get_show_preview_f1_name(self):
        return self.config.get_value('scene', 'show_preview_f1_name')

    def set_show_preview_f1_name(self, value: str):
        self.config.set_value('scene', 'show_preview_f1_name', value)

    def get_show_preview_f2_name(self):
        return self.config.get_value('scene', 'show_preview_f2_name')

    def set_show_preview_f2_name(self, value: str):
        self.config.set_value('scene', 'show_preview_f2_name', value)

    def set_show_match_enabled(self, value: bool):
        self.config.set_value('scene', 'show_match_enabled', value)

    def get_show_match_enabled(self):
        value = self.config.get_value('scene', 'show_match_enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def get_show_match_f1_name(self):
        return self.config.get_value('scene', 'show_match_f1_name')

    def set_show_match_f1_name(self, value: str):
        self.config.set_value('scene', 'show_match_f1_name', value)

    def get_show_match_f2_name(self):
        return self.config.get_value('scene', 'show_match_f2_name')

    def set_show_match_f2_name(self, value: str):
        self.config.set_value('scene', 'show_match_f2_name', value)

    def set_show_results_enabled(self, value: bool):
        self.config.set_value('scene', 'show_results_enabled', value)

    def get_show_results_enabled(self):
        value = self.config.get_value('scene', 'show_results_enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def get_show_results_f1_name(self):
        return self.config.get_value('scene', 'show_results_f1_name')

    def set_show_results_f1_name(self, value: str):
        self.config.set_value('scene', 'show_results_f1_name', value)

    def get_show_results_f2_name(self):
        return self.config.get_value('scene', 'show_results_f2_name')

    def set_show_results_f2_name(self, value: str):
        self.config.set_value('scene', 'show_results_f2_name', value)
