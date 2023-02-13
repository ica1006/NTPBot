from json import load

class Config():

    message_read_delay: int

    # Telegram
    # documentation: https://core.telegram.org/bots/api
    telegram_bot_api_key: str
    telegram_base_url: str
    chat_id: str

    # Emby
    # documentation: http://swagger.emby.media/?staticview=true
    emby_api_key: str
    emby_base_url: str

    # QBittorrent
    # documentation: https://qbittorrent-api.readthedocs.io/en/latest/apidoc/
    qbtHost: str
    qbtUser: str
    qbtPass: str

    # Proxmox
    # documentation: https://pve.proxmox.com/pve-docs/api-viewer/index.html
    #                https://pve.proxmox.com/wiki/Main_Page
    pmx_host: str
    pmx_pass: str
    pmx_user: str
    vms: list

    # TheMovieDataBase
    # documentation: https://developers.themoviedb.org/3/
    tmdb_api_key: str
    tmdb_main_api_url: str
    tmdb_poster_url: str
    tmdb_lang: str

    # Detect down services
    hosts: list
    time_between_comprobations: int

    # Weatherbit
    weatherbit_url: str
    weatherbit_default_pcode: str
    weatherbit_api_country: str

    # Overseerr
    overseerr_api_key: str
    overseerr_url: str

    # MagicHome
    mhome_led_ip: str
    ping_timeout: int
    
    def __init__(self, path='config.json') -> None:
        with open(path, encoding='UTF-8') as json_file:
            data = load(json_file)
        
        self.telegram_bot_api_key = data['telegram_bot_api_key']
        self.telegram_base_url = '{}{}/'.format(data['telegram_base_url'], self.telegram_bot_api_key)
        self.chat_id = data['chat_id']
        self.emby_api_key = data['emby_api_key']
        self.emby_base_url = data['emby_base_url']
        self.qbtHost = data['qbtHost']
        self.qbtUser = data['qbtUser']
        self.qbtPass = data['qbtPass']
        self.pmx_host = data['pmx_host']
        self.pmx_user = data['pmx_user']
        self.pmx_pass = data['pmx_pass']
        self.vms = data['vms']
        self.tmdb_api_key = data['tmdb_api_key']
        self.tmdb_poster_url = data['tmdb_poster_url']
        self.tmdb_main_api_url = data['tmdb_main_api_url']
        self.tmdb_lang = data['tmdb_lang']
        self.hosts = data['hosts']
        self.ping_timeout = data['ping_timeout']
        self.time_between_comprobations = data['time_between_comprobations']
        self.weatherbit_url = '{}?key={}&lang={}'.format(data['weatherbit_base_url'], data['weatherbit_api_key'], data['weatherbit_api_lang'])
        self.weatherbit_api_country = data['weatherbit_api_country']
        self.weatherbit_default_pcode = data['weatherbit_api_default_postal_code']
        self.overseerr_api_key = data['overseerr_api_key']
        self.overseerr_url = data['overseerr_base_url']
        self.mhome_led_ip = data['magichome_led_device_ip']
        self.message_read_delay = data['message_read_delay']

config = Config('data.json')