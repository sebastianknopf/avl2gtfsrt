import logging
import sys
import time
import uuid

from datetime import datetime, timezone
from paho.mqtt import client as mqtt


log_on_message: str = """<?xml version="1.0" encoding="utf-8"?>
<TechnicalVehicleLogOnRequestStructure version="1.0" xmlns:netex="http://netex-cen.org">
	<Timestamp>{timestamp}</Timestamp>
	<MessageId>{messageId}</MessageId>
	<netex:VehicleRef version="any">{vehicleRef}</netex:VehicleRef>
</TechnicalVehicleLogOnRequestStructure>
"""

gnss_physical_position_message: str = """<?xml version="1.0" encoding="utf-8"?>
<GnssPhysicalPositionDataStructure version="1.0">
        <Timestamp>{timestamp}</Timestamp>
        <TimestampOfMeasurement>{timestampOfMeasurement}</TimestampOfMeasurement>
        <PublisherId>ITCS435-SIMULATION</PublisherId>
        <GnssPhysicalPosition>
                <WGS84PhysicalPosition>
                        <Latitude>{latitude}</Latitude>
                        <Longitude>{longitude}</Longitude>
                </WGS84PhysicalPosition>
        </GnssPhysicalPosition>
</GnssPhysicalPositionDataStructure>
"""

coordinates: dict =  {
    '2': [  # Line 2, Pforzheim Bahnhofstraße - Pforzheim Sonnenhof
        (48.89369, 8.70415), (48.89357, 8.70395), (48.89341, 8.70373), (48.89349, 8.70197), (48.89352, 8.70145),
        (48.89342, 8.70139), (48.89307, 8.70119), (48.89273, 8.70094), (48.89243, 8.70031), (48.8922, 8.6998),
        (48.89188, 8.69925), (48.89159, 8.69914), (48.89165, 8.69819), (48.89173, 8.69731), (48.89176, 8.69726),
        (48.89177, 8.69722), (48.89198, 8.69606), (48.89186, 8.69548), (48.89169, 8.69525), (48.89139, 8.69516),
        (48.89091, 8.69501), (48.8899, 8.69495), (48.88929, 8.69489), (48.88909, 8.69493), (48.88914, 8.69488),
        (48.88911, 8.69487), (48.88907, 8.69452), (48.88914, 8.69402), (48.88928, 8.69263), (48.88941, 8.69105),
        (48.88949, 8.69001), (48.88946, 8.68934), (48.88931, 8.68774), (48.88931, 8.68768), (48.88921, 8.68693),
        (48.88915, 8.68624), (48.88908, 8.68543), (48.88895, 8.68348), (48.88894, 8.68196), (48.88889, 8.68121),
        (48.88885, 8.68078), (48.88854, 8.67965), (48.88854, 8.67961), (48.88852, 8.67959), (48.88801, 8.67826),
        (48.88757, 8.6775), (48.88717, 8.6768), (48.88684, 8.67616), (48.88652, 8.67525), (48.88615, 8.6744),
        (48.88565, 8.67325), (48.88533, 8.67259), (48.88511, 8.67205), (48.88516, 8.67213), (48.88516, 8.67225),
        (48.88443, 8.6709), (48.88376, 8.66985), (48.88316, 8.66941), (48.88261, 8.66933), (48.88227, 8.66859),
        (48.8816, 8.6677), (48.88075, 8.6669), (48.87932, 8.66628), (48.87909, 8.66623), (48.87893, 8.66626),
        (48.87886, 8.667), (48.87842, 8.668), (48.87768, 8.66825), (48.8765, 8.66739), (48.87588, 8.66682),
        (48.87583, 8.66669), (48.87583, 8.66679), (48.87562, 8.66611), (48.87567, 8.66579), (48.87562, 8.66555),
        (48.87553, 8.66548), (48.87558, 8.66557), (48.8756, 8.66564)
    ]
}


if __name__ == "__main__":

    # set logging default configuration
    logging.basicConfig(format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO)

    # set general publishing data
    vehicle_ref = 'TE-ST3'
    simulation_line_number: str = sys.argv[1]

    logging.info(f'Starting simulation for vehicle {vehicle_ref} on line {simulation_line_number} ...')

    logging.info('Connecting to test.mosquitto.org ...')
    client: mqtt.Client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='itcs435-simulation')
    client.connect("test.mosquitto.org", 1883)
    client.loop_start()    

    # publish technical logon message
    logging.info('Publishing technical logon message ...')
    client.publish(
        'IoM/1.0/DataVersion/2025/Inbox/ItcsInbox/Country/de/any/Organisation/TEST/any/ItcsId/1/CorrelationId/1/RequestData',
        log_on_message.format(
            timestamp=datetime.now(timezone.utc).isoformat(),
            messageId=str(uuid.uuid4()),
            vehicleRef=vehicle_ref
        ),
        qos=2
    )

    for coordinate in coordinates[simulation_line_number]:
        # publish GNSS physical position message
        logging.info('Publishing GNSS physical position message ...')
        client.publish(
            'IoM/1.0/DataVersion/2025/Country/de/any/Organisation/TEST/any/Vehicle/{vehicleId}/any/PhysicalPosition/GnssPhysicalPositionData'.format(vehicleId=vehicle_ref),
            gnss_physical_position_message.format(
                timestamp=datetime.now(timezone.utc).isoformat(),
                timestampOfMeasurement=datetime.now(timezone.utc).isoformat(),
                latitude=coordinate[0],
                longitude=coordinate[1]
            ),
            qos=0,
            retain=True
        )

        # wait for 10s before publishing the next coordinate
        time.sleep(10)

    # Disconnect from the broker
    client.loop_stop()
    client.disconnect()

    logging.info('Simulation trip completed.')