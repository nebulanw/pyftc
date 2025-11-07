import tkinter as tk
from tkinter import ttk
from libraries.exceptions import OBSWebSocketException
import logging

import libraries.config_manager as config_manager

SUPPORTED_MESSAGES = {
    "show_preview": 'Match preview (SHOW_PREVIEW)',
    "show_random": 'Randomization (SHOW_RANDOM)',
    "show_match": 'Show match (SHOW_MATCH)',
    "start_match": 'Start match (START_MATCH)', # added as a last resort for funny edgecases
    "show_results": 'Match results (SHOW_RESULTS)'
}

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
        self.valid_scenes = []
        self.set_default_config()
        self.valid_scenes = self.enumerate_all_valid_scenes()
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
        msg_field = '_f' + str(message['params']['field'])

        try:
            current_scene = self.obs.client.get_current_program_scene().scene_name
        except Exception:
            # self.logger.info("unexpected error")
            raise OBSWebSocketException()

        if msg_type not in SUPPORTED_MESSAGES.keys():
            self.logger.debug("Unsupported event: %s", msg_type)
            return


        msg_scene = self.get_event_generic(msg_type + msg_field + '_name')
        if current_scene not in self.valid_scenes:
            self.logger.debug("Unrecognized scene: %s", current_scene)
            return
        if current_scene == msg_scene:
            self.logger.debug("Not transitioning as new scene is the same")
            return
        self.obs.client.set_current_program_scene(msg_scene)
        self.logger.info("Switched to scene \"%s\" on event %s", msg_scene, msg_type + msg_field)

    def enumerate_all_valid_scenes(self):
        scenes = []
        for event in SUPPORTED_MESSAGES:
            if not self.get_event_enabled(event):
                continue
            scenes.append(self.get_event_generic(event + '_f1_name'))
            scenes.append(self.get_event_generic(event + '_f2_name'))
        return scenes

    def set_default_config(self):
        if self.get_enabled() is None:
            self.set_enabled(True)

        for event in SUPPORTED_MESSAGES:
            if self.get_event_enabled(event) is None:
                self.set_event_generic(event + '_enabled', True)
            if self.get_event_generic(event + '_f1_name') is None:
                self.set_event_generic(event + '_f1_name', event)
            if self.get_event_generic(event + '_f2_name') is None:
                self.set_event_generic(event + '_f2_name', event)

        self.config.save_config()

    def save_config(self):
        self.set_enabled(self.enabled.get())
        for event in SUPPORTED_MESSAGES:
            self.set_event_generic(event + '_enabled', self.events[event]['enabled'].get())
            self.set_event_generic(event + '_f1_name', self.events[event]['f1_name'].get())
            self.set_event_generic(event + '_f2_name', self.events[event]['f2_name'].get())

        self.valid_scenes = self.enumerate_all_valid_scenes()
        self.config.save_config()

    def set_up_tab(self):
        self.frame = ttk.Frame(self.notebook)

        self.enabled = tk.BooleanVar(value=self.get_enabled())
        self.scene_switcher_cb = ttk.Checkbutton(self.frame, text='Enable scene switching', variable=self.enabled)
        self.scene_switcher_cb.pack(anchor='w', padx=5, pady=5)

        # self.scene_override_cb = ttk.Checkbutton(self.frame, text='Allow overriding unrecognized scenes')

        self.events = {}
        for event, desc in SUPPORTED_MESSAGES.items():
            self.events[event] = {
                "enabled": tk.BooleanVar(value=self.get_event_enabled(event)),
                "f1_name": tk.StringVar(value=self.get_event_generic(event + '_f1_name')),
                "f2_name": tk.StringVar(value=self.get_event_generic(event + '_f2_name'))
            }
            self.events[event]['controls'] = EventConfigControls(
                self.frame,
                self.events[event]['enabled'],
                self.events[event]['f1_name'],
                self.events[event]['f2_name'],
                desc
            )

        self.save_btn = ttk.Button(self.frame, command=self.save_config, text="Save")
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

    def get_event_enabled(self, event: str):
        value = self.config.get_value('scene', event + '_enabled')
        if value is None:
            return None
        return self.str_to_bool(value)

    def get_event_generic(self, key: str):
        return self.config.get_value('scene', key)

    def set_event_generic(self, key, value):
        self.config.set_value('scene', key, value)
