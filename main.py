import threading
import re
import traceback
import sys
from config import config
from lang import lang
from time import sleep
from fileinput import input
from libraries.utils import funnyCats, pingHosts
from clients.telegram_client import telegramClient
from clients.logger import logger
from clients.emby_client import embyClient
from clients.qbittorrent_client import qbittorentClient
from clients.overseerr_client import overseerrClient
from clients.proxmox_client import proxmoxClient
from clients.weatherbit_client import weatherbitClient
from clients.magic_home_client import magicHomeClient


class Main():
    reading_thread = None
    ping_thread = None
    solicitudes_thread = None
    stop_threads = bool()

    def __init__(self) -> None:
        logger.logEntry('Bot starting in 3 seconds.')
        logger.logEntry('Write \'exit\' to exit \n')
        sleep(3)
        self.startThreads()
        logger.logEntry('Bot started')
        telegramClient.sendMessage(lang.bot_onlime)

    def handleCommands(self, command):
        """Method that handles user commands

        Args:
            command (string): user command
        """
        if command.upper() == "HOLA":
            telegramClient.sendMessage(lang.hello_world)
        elif command.upper() == 'EMBY ACTUALIZADO?':
            embyClient.embyUpToDate()
        elif command.upper() == 'EMBY ONLINE':
            embyClient.embyOnlineUsers()
        elif re.search('QBITTORRENT [A-z]+', command.upper()):
            words = command.split()
            qbittorentClient.qbtGetFromState(words[1])
        elif command.upper() == 'PROXMOX ESTADO':
            proxmoxClient.pmxVmStatus()
        elif command.upper() == 'PING':
            services_down, message = pingHosts(1)
            telegramClient.sendMessage(message)
        elif command.upper() == 'TIEMPO':
            weatherbitClient.weatherRequestHandeler(
                config.weatherbit_default_pcode)
        elif re.search('TIEMPO( ([0-9]+|([A-z ]+(, [A-z]+)?)))?', command.upper()):
            words = command.split()
            words.pop(0)
            argument = ' '.join(words)
            weatherbitClient.weatherRequestHandeler(argument)
        elif command.upper() == 'SOLICITUDES':
            overseerrClient.getPendingSolicitudes()
        elif command.upper() == 'RELOAD':
            config.reload()
            lang.reloadLang()
            telegramClient.sendMessage(lang.config_reloaded)
        elif command.upper() == 'GATO':
            funnyCats()
        elif command.upper() == 'LEDS':
            magicHomeClient.get_all_devices_on_status()
        elif command.upper() == 'LEDS ON':
            magicHomeClient.turn_device_on()
        elif command.upper() == 'LEDS OFF':
            magicHomeClient.turn_device_off()
        elif re.search('LEDS [0-9]+ ON', command.upper()):
            words = command.split()
            device = int(words[1])
            magicHomeClient.turn_device_on(device)
        elif re.search('LEDS [0-9]+ OFF', command.upper()):
            words = command.split()
            device = int(words[1])
            magicHomeClient.turn_device_off(device)
        else:
            telegramClient.sendMessage(lang.command_not_found)

    def startThreads(self):
        self.stop_threads = False
        try:
            self.reading_thread = threading.Thread(
                target=self.readMessagesThread)
            self.reading_thread.start()
            logger.logEntry('Reading thread started')
            self.ping_thread = threading.Thread(target=self.pingHostThread)
            self.ping_thread.start()
            logger.logEntry('Host comprobation thread started')
            self.solicitudes_thread = threading.Thread(
                target=self.solicitudesThread)
            self.solicitudes_thread.start()
            logger.logEntry('Solicitudes thread started')
        except:
            logger.logEntry('Something went wrong starting the threads')

    def stopThreads(self):
        self.stop_threads = True
        if self.reading_thread != None:
            self.reading_thread.join()
        if self.ping_thread != None:
            self.ping_thread.join()
        if self.solicitudes_thread != None:
            self.solicitudes_thread.join()

    def pingHostThread(self):
        notified_down_services = list()
        while self.stop_threads is False:
            down_services, message = pingHosts()

            # Si todos los servicios vuelven a estar online, mandamos el mensaje y vaciamos
            # el historial de servicios caidos y notificados
            if len(down_services) == 0 and len(notified_down_services) != 0:
                telegramClient.sendMessage(message)
                notified_down_services.clear()
            else:
                # Si alguno de los servicios caidos no ha sido notificado, enviamos el
                # mensaje con la lista de todos los servicios caidos
                if not all(service in notified_down_services for service in down_services):
                    telegramClient.sendMessage(message)
                    for service in down_services:
                        if service not in notified_down_services:
                            notified_down_services.append(service)

                # Revisamos por si algun servicio caido ha vuelto a estar operativo
                for notified_down_service in notified_down_services:
                    if notified_down_service not in down_services:
                        back_online_message = '\n{} ha vuelto a estar operativo ✅'.format(
                            notified_down_service['name'])
                        telegramClient.sendMessage(back_online_message)
                        notified_down_services.remove(notified_down_service)

            sleep(config.time_between_automatic_ping_comprobations)

    def solicitudesThread(self):
        current_solicitudes = list()

        for result in overseerrClient.getPendingSolicitudes(print_solicitudes=False):
            current_solicitudes.append(result['id'])

        while not self.stop_threads:
            try:
                solicitudes = overseerrClient.getPendingSolicitudes(
                    print_solicitudes=False)
                for result in solicitudes:
                    if result['id'] not in current_solicitudes:
                        telegramClient.sendMessage(lang.overseerr_messages['new_solicitude_detected'])
                        current_solicitudes.append(result['id'])
                        overseerrClient.getSingleSolicitude(result)
            except:
                pass
            sleep(10)

    def readMessagesThread(self):
        """Method that reads all the messages of the user in a new thread
        """
        while not self.stop_threads:
            try:
                messages = telegramClient.getMessages()
                if type(messages) is list:
                    nMessages = len(messages)
                    if nMessages > 0:
                        last_message = messages[nMessages - 1]['message']
                        if last_message['chat']['id'] == config.chat_id:
                            if 'text' in last_message:
                                logger.logEntry(
                                    'message recipt: {}'.format(last_message['text']))
                                self.handleCommands(last_message['text'])
                            else:
                                logger.logEntry(
                                    'message recipt, but there was not text detected')
                            telegramClient.setUpdateOffset(
                                messages[nMessages - 1]['update_id'] + 1)
                sleep(config.message_read_delay)
            except Exception as e:
                logger.logEntry(f'Excepcion: {e}')
                logger.logEntry(traceback.format_exc())
                logger.logEntry(sys.exc_info()[2])
                telegramClient.incrementUpdateOffset()


if __name__ == '__main__':
    main = Main()

    for line in input():
        if line.rstrip().upper() == 'EXIT':
            main.stopThreads()
            telegramClient.sendMessage(lang.bot_offline)
            break
        else:
            logger.logEntry('stdin not recognized')
