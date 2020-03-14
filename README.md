# prometheus_dyson
Prometheus client for DysonLink fans (e.g; Pure Hot+Cool).

This code only supports Pure Hot+Cool fans at the moment. It should be trivial
to extend to other fan types (I just don't have one to test).

## Dependencies

```
pip install libpurecool
pip install prometheus_client
```
## Metrics

### Environmental

Name | Type | Description
---- | ---- | -----------
humidity | gauge | relative humidity percentage
temperature | gauge | ambient temperature in celsius
voc | gauge | volatile organic compounds (range 0-10?)
dust | gauge | dust level (range 0-10?)

### Operational

Name | Type | Description
---- | ---- | -----------
fan_mode | enum | AUTO, FAN (what the fan is set to)
fan_state | enum | FAN, OFF (what the fan is actually doing)
fan_speed | gauge | 0-10 (or -1 if on AUTO)
oscillation | enum | ON, OFF
focus_mode | enum | ON, OFF
heat_mode | enum | HEAT, OFF (OFF means "in cooling mode")
heat_state | enum | HEAT, OFF (what the fan is actually doing)
heat_target | gauge | target temperature (celsius)
quality_target | gauge | air quality target (1, 3, 5?)
filter_life | gauge | hours of filter life remaining

## Usage

### Configuration

This script reads `config.ini` (or another file, specified with `--config`)
for your DysonLink login credentials.

### Args
```
% ./prometheus_dyson.py --help
usage: ./prometheus_dyson.py [-h] [--port PORT] [--config CONFIG]

optional arguments:
  -h, --help       show this help message and exit
  --port PORT      HTTP server port
  --config CONFIG  Configuration file (INI file)
```

### Scrape Frequency

I scrape at 15s intervals. Metrics are updated at approximately 30 second
intervals by `libpurecool`.

### Other Notes

`libpurecool` by default uses a flavour of mDNS to automatically discover
the Dyson fan. This is overridable (but this script doesn't at the moment).
The mDNS dependency makes Dockerising this script somewhat challenging at
the moment.

## Dashboard

I've provided a sample Grafana dashboard in `grafana.json`.
