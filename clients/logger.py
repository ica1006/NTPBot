import logging, os, datetime, re

MAX_LOGS = 5

class Logger():

    def __init__(self, filename="log", logs_dir='./logs') -> None:

        if not os.path.exists(logs_dir):
            os.makedirs(logs_dir)

        # Creamos una lista con todos los ficheros .txt ordenada de más antiguos a más nuevos
        list_dir = os.listdir(f'{logs_dir}')
        for index in range(0,len(list_dir)):
            list_dir[index] = f'{logs_dir}/{list_dir[index]}'

        ordered_list_dir = sorted(filter(os.path.isfile, list_dir), key=os.path.getmtime)
        regex = re.compile('.+\.txt')
        ordered_list_dir = [i for i in ordered_list_dir if regex.match(i)]

        # Nos aseguramos de que no exista ya un archivo con el mismo nombre
        filename = f'{filename} {datetime.datetime.now().strftime(f"%d-%m-%Y %Hh%Mm")}.txt'
        if filename in os.listdir(logs_dir):
            os.remove(f'{logs_dir}/{filename}')

        # Nos aseguramos de no sobrecargar el directorios de ficheros logs
        while len(ordered_list_dir) >= MAX_LOGS:
            os.remove(f'{ordered_list_dir.pop(0)}')

        logging.basicConfig(handlers=[logging.FileHandler(filename=f'{logs_dir}/{filename}', encoding='utf-8', mode='w')], 
                                                            level=logging.INFO, format='%(asctime)s - %(message)s')
    
    def logEntry(self, entry):
        """ Method that logs actions into the file

        Args:
            entry (string): log entry
        """    
        logging.info(entry)
        print(entry)

logger = Logger('log')