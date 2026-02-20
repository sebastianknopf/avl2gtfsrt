import click
import logging

from avl2gtfsrt.common.env import is_debug
from avl2gtfsrt.worker import Worker
from avl2gtfsrt.server import GtfsRealtimeServer
from avl2gtfsrt.publisher import GtfsRealtimePublisher


def run_worker():
    try:
        worker: Worker = Worker()
        worker.run()
    except Exception as ex:
        if is_debug():
            logging.exception(ex)
        else:
            logging.error(str(ex)) 

def run_server():
    try:
        server: GtfsRealtimeServer = GtfsRealtimeServer()
        server.run()
    except Exception as ex:
        if is_debug():
            logging.exception(ex)
        else:
            logging.error(str(ex)) 

def run_publisher():
    try:
        publisher: GtfsRealtimePublisher = GtfsRealtimePublisher()
        publisher.run()
    except Exception as ex:
        if is_debug():
            logging.exception(ex)
        else:
            logging.error(str(ex))


@click.group()
def cli():
    pass

@cli.command()
def worker():

    # set logging default configuration
    logging.basicConfig(format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO)

    # run the worker
    run_worker()

@cli.command()
def server():

    # set logging default configuration
    logging.basicConfig(format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO)

    # run the server
    run_server()

@cli.command()
def publisher():

    # set logging default configuration
    logging.basicConfig(format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO)

    # run the publisher
    run_publisher()


if __name__ == '__main__':
    cli()