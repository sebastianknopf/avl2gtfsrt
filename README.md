# avl2gtfsrt
Matching of raw AVL (Automatic Vehicle Location) data to GTFS-RT [vehicle positions](https://gtfs.org/documentation/realtime/reference/#message-vehicleposition) and [trip updates](https://gtfs.org/documentation/realtime/reference/#message-tripupdate) in realtime.

## Basic Idea
Vehicle positions in public GTFS-RT feeds are interpolated using nominal and realtime data most times. While this is sufficient for simple use cases, it can quickly result in incorrect positions being displayed, which passengers perceive as unreliable. 

The package avl2gtfsrt acts as a backend service to receive actual AVL data directly from sensors or small clients on the vehicles and match it to the correct trip. To work with a reproducable and standardized setup, avl2gtfsrt uses communication defined for [IoM (Internet Of Mobility)](https://www.vdv.de/leitmotif-ki.aspx) aka VDV435 for the AVL data transmission and exposes the results as two GTFS-RT feeds (vehicle positions and trip updates).

## Installation
To run the avl2gtfsrt service, simply clone this repository to your destination:

```bash
git clone https://github.com/sebastianknopf/avl2gtfsrt.git
cd avl2gtfsrt
```

Then, configure the `.env` file to your requirements:

```env
A2G_DEBUG=false

A2G_ORGANISATION_ID=yourorganisation
A2G_ITCS_ID=1

A2G_MONGODB_USERNAME=username
A2G_MONGODB_PASSWORD=password

A2G_WORKER_MQTT_HOST=mqtt.yourdomain.com
A2G_WORKER_MQTT_PORT=1883
A2G_WORKER_MQTT_USERNAME=username
A2G_WORKER_MQTT_PASSWORD=password

A2G_NOMINAL_ADAPTER_TYPE=otp
A2G_NOMINAL_ADAPTER_CONFIG={"endpoint": "https://otp.yourdomain.com/otp/transmodel/v3", "username": "username", "password": "password"}
A2G_NOMINAL_CACHING_ENABLED=true

A2G_SERVER_TIMEZONE=Europe/Berlin
A2G_SERVER_PORT=9000
```

After successful configuration, simply start the service with:

```bash
docker compose up -d
```

Afterwards, you can open `http://localhost:9000/vehicle-positions.pbf?debug` oder `http://localhost:9000/trip-updates.pbf?debug` in your browser for seeing the JSON representation of the GTFS-RT data.

## Configuration
Configuration of the avl2gtfsrt service is done using an `.env` file. See [default.env](default.env) for reference.

Following configuration variables are available:

| Name | Description |
|----------|----------|
| A2G_DEBUG | _(optional)_ Enables extended logging. Default is `false`.  |
| A2G_ORGANISATION_ID | _(required)_ Your organisation ID at the VDV435 broker. |
| A2G_ITCS_ID | _(required)_ Your service ID at the VDV435 broker. |
| A2G_MONGODB_USERNAME | _(internal)_ Username for accessing the local MongoDB container. Changing this value has no effect outside the container network. |
| A2G_MONGODB_PASSWORD | _(internal)_ Password for accessing the local MongoDB container. Changing this value has no effect outside the container network. |
| A2G_WORKER_MQTT_HOST | _(required)_ Hostname or IP address for the VDV435 broker. |
| A2G_WORKER_MQTT_PORT | _(optional)_ Port for the VDV435 broker. Default is `1883`. |
| A2G_WORKER_MQTT_USERNAME | _(optional)_ Username for the VDV435 broker. Required if the broker enforces authentication. |
| A2G_WORKER_MQTT_PASSWORD | _(optional)_ Password for the VDV435 broker. Required if the broker enforces authentication. |
| A2G_NOMINAL_ADAPTER_TYPE | _(optional)_ Adapter type for loading nominal data. Default is `otp`. Currently supported adapter types: `otp`. |
| A2G_NOMINAL_ADAPTER_CONFIG | _(required)_ JSON configuration string for the nominal adapter. Requires at least the `endpoint` key, other keys depend on the adapter used. |
| A2G_NOMINAL_CACHING_ENABLED | _(optional)_ Enables caching of the nominal data. Default is `false`. **Not implemented yet!** |
| A2G_SERVER_TIMEZONE | _(optional)_ Timezone the GTFS-RT server is running in. Default is `Europe/Berlin`. |
| A2G_SERVER_PORT | _(optional)_ Port the GTFS-RT server is listening to on the host. Default is `9000`. |

## License
This project is licensed under the Apache License. See [LICENSE](LICENSE.md) for more information.