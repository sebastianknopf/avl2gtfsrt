import click
import logging

from itcs435.common.env import is_debug
from itcs435.worker.iom import IomWorker

def run():
    
    try:
        worker: IomWorker = IomWorker(
            mqtt_host='test.mosquitto.org',
            mqtt_port=1883,
            mqtt_username=None,
            mqtt_password=None
        )

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