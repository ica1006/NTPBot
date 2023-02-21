from config import config
from json import load

class Lang():
    app_lang: str

    hello_world: str
    bot_onlime: str
    bot_offline: str
    config_reloaded: str
    command_not_found: str

    emby_messages: dict()
    overseerr_messages: dict()
    magic_home_messages: dict()
    qbittorrent_messages: dict()
    weatherbit_messages: dict()

    def __init__(self) -> None:
        self.app_lang = config.app_lang
        self.loadMessages()
    
    def loadMessages(self):
        with open(f'lang/{self.app_lang}.json', encoding='UTF-8') as json_file:
            data = load(json_file)
        self.hello_world = data['hello_world']
        self.bot_onlime = data['bot_online']
        self.bot_offline = data['bot_offline']
        self.config_reloaded = data['config_reloaded']
        self.command_not_found = data['command_not_found']

        self.emby_messages = data['emby_messages']
        self.overseerr_messages = data['overseerr_messages']
        self.magic_home_messages = data['magic_home_messages']
        self.qbittorrent_messages = data['qbittorrent_messages']
        self.weatherbit_messages = data['weatherbit_messages']
    
    def reloadLang(self, new_lang=config.app_lang):
        print(f'New lang {new_lang}')
        self.app_lang = new_lang
        self.loadMessages()

lang = Lang()