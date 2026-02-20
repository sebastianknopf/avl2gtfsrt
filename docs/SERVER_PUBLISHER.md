# GTFS-RT Operation Modes
The official [GTFS-RT spec](https://gtfs.org/documentation/realtime/reference/) describes publishing GTFS-RT data using a regular server which sends ProtoBuf encoded GTFS-RT dumps to the client in their response. This dumps always contain every existing trip or vehicle update in the system, hence we're talking about the `FULL_DATASET` incrementality.

However, the official GTFS-RT spec also provides the option `DIFFERENTIAL` for the incrementality of a FeedMessage. There's no official spec for the GTFS-RT differential support, but there some [ongoing discussions and best practices](https://github.com/derhuerst/gtfs-rt-differential-to-full-dataset/issues/1) anyway.

`avl2gtfsrt` uses docker compose profiles to provide both operation modes without dependency in between both and without the requirement to run the full setup at all. Please refer to the [main page](../README.md) for seeing the options configurable in ENV variables.

## GTFS-RT Server
To startup a GTFS-RT server, simply use the option `--profile server` option in docker compose command as follows:

```bash
docker compose --profile server up [--build] [-d]
```

After that, you can find the endpoint for vehicle positions at `http://localhost:9000/vehicle-positions.pbf` and the endpoint for trip updates at `http://localhost:9000/trip-updates.pbf`. By adding the query parameter `debug`, the server will response with JSON output instead of encoded ProtoBuf. A value for the `debug` query parameter is not required.

## GTFS-RT Publisher
Additionally to the regular server, there's a publisher available. The publisher is useful, if you want to publish GTFS-RT in realtime to other systems. There're different methods configurable. Currently, following methods are available:

- MQTT (method name in config: `mqtt`)

The publisher receives an event over the integrated `redis` container and then triggers a GTFS-RT export of the current database and publishes the data to the configured endpoint.

To startup in publisher mode, run:

```bash
docker compose --profile publisher up [--build] [-d]
```

### MQTT Publishing (Differential)
For using MQTT publishing, following keys are available in for the `A2G_PUBLISHER_CONFIG` JSON string:

- `endpoint`: Address of the MQTT broker to connect with
- `port`: Port for the MQTT broker to connect with
- `topic`: Topic for publishing the GTFS-RT data. Following placeholders are available: 
    - `{organisationId}`: Value of `A2G_ORGANISATION_ID`, always transformed to lower case
    - `{dataType}`: Either `tripupdates` or `vehiclepositions`
    - `{vehicleId}`: Vehicle ID as-it-is 
- `username`: _(optional)_ Username for the MQTT broker
- `password`: _(optional)_ Password for the MQTT broker
- `debug`: _(optional)_ Enables publishing of JSON instead of encoded ProtoBuf. Default is `False`
