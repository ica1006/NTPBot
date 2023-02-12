import requests, os
from clients.logger import logger
from models.config import Config

class TelegramClient():
    config: Config
    update_offset = 1

    def __init__(self, config_path) -> None:
        self.config = Config(config_path)

    def getMessages(self) -> list:
        rq = requests.get(f'{self.config.telegram_base_url}getUpdates?offset={self.update_offset}')
        if rq.status_code == requests.codes.ok:
            data = rq.json()
            messages = data['result']
            return messages
    
    def setUpdateOffset(self, new_offset: int):
        self.update_offset = new_offset

    def incrementUpdateOffset(self):
        self.update_offset += 1

    def sendMessage(self, message):
        """ Method that sends a message to the user

        Args:
            message (string): message to be send
        """        
        if len(message) < 4096:
            rq = requests.get(f'{self.config.telegram_base_url}sendMessage?chat_id={self.config.chat_id}&text={message}')
            if rq.status_code == requests.codes.ok:
                logger.logEntry(f'message sent: {message}')
            else:
                logger.logEntry(f'error while sending message {message}')
                logger.logEntry(rq)
        else:
            textFile = open('message.txt', 'w')
            textFile.write(message)
            textFile.close()
            self.sendFile('message.txt')
            os.remove('message.txt')

    def sendFile(self, filePath):
        """ Method that sends a file to the telegram conversation

        Args:
            filePath (string): file path
        """        
        file = open(filePath, 'rb')
        file_bytes = file.read()
        file.close()
        response = {
            'document': (file.name, file_bytes)
        }
        requests.post(url=f'{self.config.telegram_base_url}sendDocument?chat_id={self.config.chat_id}', files=response)
        logger.logEntry(f'File {file.name} sent')
    
    def sendPhoto(self, filePath):
        img = open(filePath, 'rb')
        rq = requests.post(f'{self.config.telegram_base_url}sendPhoto?chat_id={self.config.chat_id}', files={'photo':img})
        img.close()
        if rq.status_code == requests.codes.ok:
            logger.logEntry(f'Photo sent')
        else:
            logger.logEntry('Error while sending the photo')


telegramClient = TelegramClient('data.json')