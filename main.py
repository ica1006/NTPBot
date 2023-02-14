import threading
import re
import traceback
import sys
import libraries.magichome as magichome
from config import config
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


stop_threads = False


class Main():

    def readMessagesThread(self):
        """Method that reads all the messages of the user in a new thread
        """
        while not stop_threads:
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

    def handleCommands(self, command):
        """Method that handles user commands

        Args:
            command (string): user command
        """
        if command.upper() == "HOLA":
            telegramClient.sendMessage("Hola, qué tal?")
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
            pingHosts()
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
            telegramClient.sendMessage('Config reloaded ⚙️')
        elif command.upper() == 'GATO':
            funnyCats()
        elif command.upper() == 'LEDS ON':
            controller = magichome.MagicHomeApi(config.mhome_led_ip, 0)
            controller.turn_on()
        elif command.upper() == 'LEDS OFF':
            controller = magichome.MagicHomeApi(config.mhome_led_ip, 0)
            controller.turn_off()
        else:
            telegramClient.sendMessage('Command not found')

    def pingHost_Thread(self):
        down_services = list()
        while stop_threads is False:
            up, services, message = pingHosts(thread=True)
            if up is False:
                for service in services:
                    if service not in down_services:
                        telegramClient.sendMessage(message)
                        down_services.append(service)
            elif len(down_services) != 0:
                telegramClient.sendMessage(
                    f'Todos los servicios han vuelto a estar operativos ✅')
                down_services.clear()

            sleep(config.time_between_comprobations)

    def solicitudesThread(self):
        current_solicitudes = list()

        for result in overseerrClient.getPendingSolicitudes(print_solicitudes=False):
            current_solicitudes.append(result['id'])

        while not stop_threads:
            try:
                solicitudes = overseerrClient.getPendingSolicitudes(
                    print_solicitudes=False)
                for result in solicitudes:
                    if result['id'] not in current_solicitudes:
                        telegramClient.sendMessage('Nueva solicitud detectada')
                        current_solicitudes.append(result['id'])
                        overseerrClient.getSingleSolicitude(result)
            except:
                pass
            sleep(10)


if __name__ == '__main__':
    main = Main()
    logger.logEntry('Bot starting in 3 seconds.')
    logger.logEntry('Write \'exit\' to exit')
    sleep(3)
    print('')

    logger.logEntry('Bot started')
    reading = threading.Thread(target=main.readMessagesThread)
    reading.start()
    logger.logEntry('Reading thread started')
    host_comprobation = threading.Thread(target=main.pingHost_Thread)
    host_comprobation.start()
    logger.logEntry('Host comprobation thread started')
    solicitudes_thread = threading.Thread(target=main.solicitudesThread)
    solicitudes_thread.start()
    logger.logEntry('Solicitudes thread started')

    for line in input():
        if line.rstrip().upper() == 'EXIT':
            stop_threads = True
            reading.join()
            host_comprobation.join()
            solicitudes_thread.join()
            break
        else:
            logger.logEntry('stdin not recognized')
