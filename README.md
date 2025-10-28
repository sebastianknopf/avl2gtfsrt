# avl2gtfsrt
Matching of raw AVL (Automatic Vehicle Location) data to GTFS-RT [vehicle positions](https://gtfs.org/documentation/realtime/reference/#message-vehicleposition) and [trip updates](https://gtfs.org/documentation/realtime/reference/#message-tripupdate) in realtime.

## Basic Idea
Vehicle positions in public GTFS-RT feeds are interpolated using nominal and realtime data most times. While this is sufficient for simple use cases, it can quickly result in incorrect positions being displayed, which passengers perceive as unreliable. 

The package `avl2gtfsrt` acts as a backend service to receive actual AVL data directly from sensors or small clients on the vehicles and match it to the correct trip. To work with a reproducable and standardized setup, `avl2gtfsrt` uses communication defined for [IoM (Internet Of Mobility)](https://www.vdv.de/leitmotif-ki.aspx) aka VDV435 for the AVL data transmission and exposes the results as two GTFS-RT feeds (vehicle positions and trip updates).

See more [details about how it works](docs/HOW_IT_WORKS.md) under the hood.

## Installation

### Additional Requirements
The `avl2gtfsrt` backend service requires a MQTT broker for the VDV435 communication and a nominal data service for fetching possible trip candidates. This service can be running locally on the host or on a remote server.

For loading nominal data, adapters can be implemented which load and prepare the data of the remote service. Currently, following adapters are implemented:

- **OpenTripPlanner**: Uses the Transmodel V3 API to load nominal data. Adapter type is `otp`.

### Usage
To run the `avl2gtfsrt` service, simply clone this repository to your destination:

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
docker compose up --build -d
```

Afterwards, you can open `http://localhost:9000/vehicle-positions.pbf?debug` oder `http://localhost:9000/trip-updates.pbf?debug` in your browser for seeing the JSON representation of the GTFS-RT data.

## Configuration
Configuration of the `avl2gtfsrt` service is done using an `.env` file. See [default.env](default.env) for reference.

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
| A2G_WORKER_MQTT_CLIENT_SUFFIX | _(optional)_ Suffix added to the client ID `avl2gtfsrt-IoM-{suffix}`. If not specified, a 6-char random value is used. |
| A2G_NOMINAL_ADAPTER_TYPE | _(optional)_ Adapter type for loading nominal data. Default is `otp`. Currently supported adapter types: `otp`. |
| A2G_NOMINAL_ADAPTER_CONFIG | _(required)_ JSON configuration string for the nominal adapter. Requires at least the `endpoint` key, other keys depend on the adapter used. |
| A2G_NOMINAL_CACHING_ENABLED | _(optional)_ Enables caching of the nominal data. Default is `false`. **Not implemented yet!** |
| A2G_SERVER_TIMEZONE | _(optional)_ Timezone the GTFS-RT server is running in. Default is `Europe/Berlin`. |
| A2G_SERVER_PORT | _(optional)_ Port the GTFS-RT server is listening to on the host. Default is `9000`. |

## Client Integration
For `avl2gtfsrt` to work, you will need some clients sending MQTT data based on VDV435 standard. Those clients are rarely implemented in on-board units in some buses or public transport vehicles. However, most times proprietary protocols and system internal communication networks are used to transmit the actual vehicle position meaning that they cannot simply be used by third-party services.

Alternatively, you have following options:
- Use an Android app which is sending the data according to VDV435. Possible devices could be tablets mounted in the vehicle or drivers working cell phone.
- Use GNSS locations updates of other devices mounted in the vehicle, like dashcams or passenger WLAN routers.
- Use a GNSS tracker or any other arbitrary tracking device which is sending its position over network.

For using the latter two options, you will need a converter for converting the raw GNSS data to VDV435 MQTT messages. See [avl2gtfsrt-integration](https://github.com/sebastianknopf/avl2gtfsrt-integration) which is designed to provide an adapter service for every known GNSS tracker service APIs.

## Known Limitations
As `avl2gtfsrt` only processes raw AVL data without any meta information (like route ID, agency ID or trip ID), the matching can always only be an estimation. In general, `avl2gtfsrt` is developed to generate no match than a wrong match. This means, the technology used has also some known limitations:

- Matching can take quite long or generate some mismatches in transit networks with many lines travelling running in parallel and in close timing.
- Nominal data need to contain a valid shape. This is a geographical polyline representing the way which should be used by the vehicle. Data without a shape cannot be considered as matching candidate.
- As `avl2gtfsrt` performs also temporal matching before a trip is finally matched, vehicles running on a trip with too much delay (~ 15min) cannot be matched.
- All parameters are configured internally to the tested and best matching values. However, there may be some differences for optimal parameters depending on the mode (bus, tram, railway) and other special cases.
- For spatial calculations, simple projections are used. This can lead to problems with trips including several loops and visiting the same station twice or more.

If you get in confrontation with one of those limitations and have an idea for an improvement, feel free to open up an issue and describe your problem.

## License
This project is licensed under the Apache License. See [LICENSE](LICENSE.md) for more information.