import json
import os

from datetime import datetime
from lxml.etree import fromstring
from lxml.etree import tostring

class Datalog:

    @classmethod
    def cleanup(cls, directory: str, ttl_hours: int = 24) -> None:
        if not os.path.exists(directory) or not os.path.isdir(directory):
            os.makedirs(directory)

        # look for old datalog files and remove them
        # for speed up, check for the filename not beginning with today instead of ressource consuming difference calculation
        today = datetime.now().strftime('%Y-%m-%d')
        for datalog_file in os.listdir(directory):

            # proceed only if the datalogfile is not from today
            if not datalog_file.startswith(today):
                datalog_timestamp = datalog_file.split('_')[0]
                datalog_timestamp = datetime.strptime(datalog_timestamp, '%Y-%m-%d-%H.%M.%S-%f')

                difference = (datetime.now() - datalog_timestamp).total_seconds()
                if difference > 60 * 60 * ttl_hours:
                    datalog_file = os.path.join(directory, datalog_file)
                    os.remove(datalog_file)
    @classmethod
    def create(cls, directory: str, data: str, meta: dict, *args) -> None:
        cls.cleanup(directory)
        
        if not os.path.exists(directory) or not os.path.isdir(directory):
            os.makedirs(directory)

        # generate new datalog file
        datalog_timestamp = datetime.now().strftime('%Y-%m-%d-%H.%M.%S-%f')
        datalog_filename = f"{datalog_timestamp}_{'-'.join([str(a) for a in args])}.xml"

        with open(os.path.join(directory, datalog_filename), 'wb') as datalog_file:
                try:
                    xml = tostring(fromstring(data), pretty_print=True)
                    datalog_file.write(xml)
                    datalog_file.write(cls._comment(meta))
                except Exception:
                    datalog_file.write(data)
                    datalog_file.write(cls._comment(meta))
                finally:
                    datalog_file.close()

    @classmethod
    def _comment(cls, metadata: dict) -> str:
        comment = "<!--\n"
        comment += "This message is created by datalog module - See https://gist.github.com/sebastianknopf/677d9ae9f213389e1c3f9aeb0b5e4055\n"
        comment += "\n"
        comment += "Request Meta Data:\n"
        comment += json.dumps(metadata, indent=4) + "\n"
        comment += "-->"

        return comment.encode('utf-8')