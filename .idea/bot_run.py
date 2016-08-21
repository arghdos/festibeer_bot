from bot import bot
import sys
import logging

def run_bot(filename):
    b = bot(filename)
    b()

if __name__ == '__main__':
    import logging

    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s",
                                     datefmt='%m/%d/%Y %I:%M:%S %p')

    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)
    fileHandler = logging.FileHandler("festibeer.log")
    fileHandler.setFormatter(logFormatter)
    rootLogger.addHandler(fileHandler)

    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    rootLogger.addHandler(consoleHandler)

    run_bot('lockn2016.txt')