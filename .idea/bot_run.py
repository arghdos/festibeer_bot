from bot import bot
import sys
import logging

def run_bot(filename):
    b = bot(filename)
    b()

if __name__ == '__main__':
    import logging
    logging.basicConfig(filename='festibeer.log', level=logging.INFO,
                        format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
                        stream=sys.stdout)

    run_bot('lockn2016.txt')