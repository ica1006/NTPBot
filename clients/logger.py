import logging

class Logger():

    def __init__(self, filename="log.txt") -> None:
        logging.basicConfig(handlers=[logging.FileHandler(filename=filename, encoding='utf-8', mode='w')], level=logging.INFO, format='%(asctime)s - %(message)s')
    
    def logEntry(self, entry):
        """ Method that logs actions into the file

        Args:
            entry (string): log entry
        """    
        logging.info(entry)
        print(entry)

logger = Logger('log.txt')