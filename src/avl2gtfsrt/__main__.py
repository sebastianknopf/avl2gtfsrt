import os
import click
import logging

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.worker import Worker

def run():
    
    try:
        worker: Worker = Worker()
        worker.run()
    except Exception as ex:
        if is_debug():
            logging.exception(ex)
        else:
            logging.error(str(ex)) 

@click.group()
def cli():
    pass

@cli.command()
def main():

    # set logging default configuration
    logging.basicConfig(format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO)

    # run the server
    run()

if __name__ == '__main__':
    cli()