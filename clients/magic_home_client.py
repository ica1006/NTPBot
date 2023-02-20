import magichue
from config import config
from clients.telegram_client import telegramClient
from clients.logger import logger

class MagicHomeClient():
    devices = list()

    def __init__(self) -> None:
        logger.logEntry('Initializing MagicHome connections')
        for ip in config.magic_home_devices:
            self.devices.append(magichue.LocalLight(ip))
        logger.logEntry('Connections initialized')
    
    def check_if_device_in_list(self, device):
        if device <= len(self.devices) and device > 0:
            return True
        telegramClient.sendMessage('Not valid device')
        return False
    
    def device_is_on(self, device):
        return self.devices[device-1].on

    def turn_device_on(self, device=1):
        if not self.check_if_device_in_list(device):
            return
        self.devices[device-1].on = True
        if self.device_is_on(device):
            telegramClient.sendMessage("Led encendido ☀️")
        else:
            telegramClient.sendMessage("Algo ha salido mal, el led no se ha encendido")
    
    def turn_device_off(self, device=1):
        if not self.check_if_device_in_list(device):
            return
        self.devices[device-1].on = False
        if not self.device_is_on(device):
            telegramClient.sendMessage("Led apagado 🌑")
        else:
            telegramClient.sendMessage("Algo ha salido mal, el led no se ha encendido")

    def get_all_devices_on_status(self):
        message = 'Leds status:\n'
        for device in range(1, len(self.devices)+1):
            self.devices[device-1]._update_status()
            message += f'  Leds {device} {self.devices[device-1].ipaddr} '
            if self.device_is_on(device):
                message += 'on ☀️\n'
            else:
                message += 'off 🌑\n'
        telegramClient.sendMessage(message)

magicHomeClient = MagicHomeClient()
        
