import logging
import os
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
        (48.89337173640118, 8.701332009494536), (48.89321480624551, 8.701168089642124),
        (48.892800735156754, 8.700961032985902), (48.89257951768997, 8.700664826936674),
        (48.892303467170706, 8.700086793771902), (48.89207279364999, 8.6995864068532),
        (48.89190451475466, 8.699310331311153), (48.891755143125465, 8.699195299836049),
        (48.89166438546232, 8.699074516786226), (48.89166438546232, 8.698623018244774),
        (48.8917097697649, 8.698053602580643), (48.89171355133388, 8.697973080547797),
        (48.89171355133388, 8.697901185876503), (48.891715442118254, 8.697849421712476),
        (48.89178351031177, 8.697029822447945), (48.89191019253636, 8.696359764103335),
        (48.891989605110325, 8.695968657086183), (48.89202742057725, 8.695770227790263),
        (48.89204254675619, 8.6956206868729), (48.89201229439416, 8.695537289052027),
        (48.89169653427038, 8.695387748134635), (48.89078705744211, 8.695013901846039),
        (48.88985298324869, 8.695034035319566), (48.88927437831674, 8.694927634533599),
        (48.8892327790108, 8.694927634533599), (48.8892006340692, 8.694930510321626),
        (48.88917227086773, 8.694930510321626), (48.88914201676894, 8.69492475874685),
        (48.88912042146853, 8.69438762085386), (48.88927547359933, 8.693082013605675),
        (48.889354890415774, 8.691704511767995), (48.88944565178494, 8.690223481176616),
        (48.88944754265512, 8.68988413832352), (48.88944754265512, 8.68978060999541),
        (48.88944754265512, 8.689743224766431), (48.88944565178494, 8.689705839537396),
        (48.88930032260072, 8.688113469787766), (48.88920010608419, 8.686937272949677),
        (48.889082869194795, 8.685746696492743), (48.88896752513776, 8.684357691424935),
        (48.8889096254768, 8.683118628515189), (48.88890584369571, 8.681663480349528),
        (48.888746508925806, 8.680425230022252), (48.88852338261549, 8.679643015988034),
        (48.888513928088855, 8.679611382332496), (48.88850069174873, 8.679582624463706),
        (48.88849123721741, 8.679550990806916), (48.88822908723924, 8.678828641338555),
        (48.88770908255776, 8.677810612779382), (48.88717772673334, 8.676815590515446),
        (48.88673881241647, 8.675895087225769), (48.88637196237926, 8.674888561813589),
        (48.88580655421589, 8.67360596086192), (48.88526004669444, 8.672426886575437),
        (48.88511443728345, 8.672053034280054), (48.88508796279959, 8.6720098974763),
        (48.885072834516706, 8.671975388033985), (48.88505581519303, 8.671929375443455),
        (48.88503123171529, 8.671886238639644), (48.88501421237751, 8.671831598688868),
        (48.88498773784059, 8.671791337673028), (48.88450262393013, 8.670991887845872),
        (48.884071461030146, 8.67032182950129), (48.88370837359969, 8.669815691009063),
        (48.883402016529914, 8.669502230238038), (48.88311078714776, 8.669430334981797),
        (48.88282144650677, 8.669427459195049), (48.882537777586776, 8.669266415129385),
        (48.882225673808534, 8.668579006156534), (48.88176234155435, 8.667891693090098),
        (48.88118305773477, 8.667259584943992), (48.88068756540764, 8.666874229500422),
        (48.88006346503337, 8.666601029745124), (48.87911964498903, 8.666215610286287),
        (48.87902886439085, 8.666195479777741), (48.87896456136778, 8.666356523844655),
        (48.878907823337244, 8.666992072747007), (48.87813996167475, 8.66857088102094),
        (48.87804728799736, 8.668674409349023), (48.877644439201134, 8.66817689821707),
        (48.877623634714865, 8.668139512988034), (48.87759526494733, 8.668099251971),
        (48.87703046220463, 8.667646047576454), (48.87627213485416, 8.667239375555056),
        (48.876013016711454, 8.667052449407407), (48.875644196602536, 8.666275986947909),
        (48.87545883982847, 8.665697953783138), (48.87544749143237, 8.665669195913097),
        (48.8750831109312, 8.665087102652706), (48.87461971251125, 8.664825406045708),
        (48.87407686890293, 8.664954816455833), (48.87341864149721, 8.665811797459469),
        (48.87290037420567, 8.665814673007276), (48.872883350739755, 8.665797418285507),
        (48.87272446477914, 8.665877940318325), (48.87249571058513, 8.666478978563674),
        (48.872484361516456, 8.666513488007212), (48.87209281891495, 8.667370464690578),
        (48.87139910802901, 8.668357660315166), (48.87076873927586, 8.669279722047435),
        (48.8703246110677, 8.670252606079032), (48.869933010882164, 8.670993159596208),
        (48.86935515622986, 8.671254531425944), (48.86886325892627, 8.671000421038173),
        (48.86854805956861, 8.670717268222148), (48.86842388957902, 8.670143702263374),
        (48.868643574734904, 8.669780685833388), (48.868543283805195, 8.66968630156137),
        (48.86848119884297, 8.669700822218658)
    ]
}


if __name__ == "__main__":

    # set logging default configuration
    logging.basicConfig(format="[%(levelname)s] %(asctime)s %(message)s", level=logging.INFO)

    # set general publishing data
    vehicle_ref = 'TE-ST3'
    simulation_line_number: str = sys.argv[1]

    logging.info(f'Starting simulation for vehicle {vehicle_ref} on line {simulation_line_number} ...')

    client: mqtt.Client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, protocol=mqtt.MQTTv5, client_id='itcs435-simulation')

    mqtt_username: str = os.getenv('ITCS435_WORKER_MQTT_USERNAME', None)
    mqtt_password: str = os.getenv('ITCS435_WORKER_MQTT_PASSWORD', None)
    if mqtt_username is not None and mqtt_password is not None:
        client.username_pw_set(username=mqtt_username, password=mqtt_password)

    # connect to MQTT broker
    mqtt_host: str = os.getenv('ITCS435_WORKER_MQTT_HOST', 'test.mosquitto.org')
    mqtt_port: str = os.getenv('ITCS435_WORKER_MQTT_PORT', '1883')

    logging.info(f'Connecting to {mqtt_host}:{mqtt_port} ...')
    client.connect(mqtt_host, int(mqtt_port))
    client.loop_start()    

    # publish technical logon message
    logging.info('Publishing technical logon message ...')
    client.publish(
        'IoM/1.0/DataVersion/2025/Inbox/ItcsInbox/Country/de/any/Organisation/TEST/any/ItcsId/1/CorrelationId/1/RequestData',
        log_on_message.format(
            timestamp=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
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
                timestampOfMeasurement=datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
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