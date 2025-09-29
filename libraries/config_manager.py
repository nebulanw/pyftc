import configparser

class ConfigurationManager():
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)
        self.set_default_config()

    def save_config(self):
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def set_default_config(self):
        # only settings in the "General" tab are set here since that's not a "real" handler
        # each module under `handlers` has its own set_default_config()
        # this goes for getters and setters as well

        if self.get_scorekeeper_ws() is None:
            self.set_scorekeeper_ws('ws://localhost/stream/display/command/?code=uswaspm1')
        if self.get_obs_ws_host() is None:
            self.set_obs_ws_host('localhost')
        if self.get_obs_ws_port() is None:
            self.set_obs_ws_port(4455)
        if self.get_obs_ws_pw() is None:
            self.set_obs_ws_pw('')

        self.save_config()

    def get_value(self, section: str, key: str):
        if section not in self.config:
            return None
        if key not in self.config[section]:
            return None
        
        return self.config[section][key]

    def set_value(self, section: str, key: str, value):
        if section not in self.config:
            self.config[section] = {}

        self.config.set(section, key, str(value))

    def get_scorekeeper_ws(self):
        return self.get_value('main', 'scorekeeper_url')

    def set_scorekeeper_ws(self, value: str):
        self.set_value('main', 'scorekeeper_url', value)

    def get_obs_ws_host(self):
        return self.get_value('main', 'obs_ws_host')

    def set_obs_ws_host(self, value: str):
        self.set_value('main', 'obs_ws_host', value)

    def get_obs_ws_port(self):
        value = self.get_value('main', 'obs_ws_port')
        try:
            return int(value)
        except Exception:
            return None

    def set_obs_ws_port(self, value: int):
        self.set_value('main', 'obs_ws_port', value)

    def get_obs_ws_pw(self):
        return self.get_value('main', 'obs_ws_pw')

    def set_obs_ws_pw(self, value: str):
        self.set_value('main', 'obs_ws_pw', value)
