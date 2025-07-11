import os
import click
import logging

from itcs435.common.env import is_debug
from itcs435.worker import IomWorker

def run():
    
    try:
        mqtt_host = os.getenv('ITCS435_WORKER_MQTT_HOST', 'test.mosquitto.org')
        mqtt_port = os.getenv('MQTT_PORT', '1883')
        mqtt_username = os.getenv('MQTT_USERNAME', None)
        mqtt_password = os.getenv('MQTT_PASSWORD', None)

        worker: IomWorker = IomWorker(
            mqtt_host=mqtt_host,
            mqtt_port=mqtt_port,
            mqtt_username=mqtt_username,
            mqtt_password=mqtt_password
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