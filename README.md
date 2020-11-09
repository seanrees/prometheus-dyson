# prometheus_dyson
Prometheus client for DysonLink fans (e.g; Pure Hot+Cool and Pure Cool).

This code only supports Pure Hot+Cool and Pure Cool fans at the moment. It should be trivial
to extend to other fan types (I just don't have one to test).

## Build

```
% bazel build :main
```

If you'd like a Debian package:
```
% baze build :main-deb
```

### Without Bazel

You'll need these dependencies:

```
pip install libpurecool
pip install prometheus_client
```

## Metrics

### Environmental

Name | Type | Description
---- | ---- | -----------
dyson_humidity_percent | gauge | relative humidity percentage
dyson_temperature_celsius | gauge | ambient temperature in celsius
dyson_volatile_organic_compounds_units | gauge | volatile organic compounds (range 0-10?)
dyson_dust_units | gauge | dust level (range 0-10?)

### Operational

Name | Type | Description
---- | ---- | -----------
dyson_fan_mode | enum | AUTO, FAN, OFF (what the fan is set to)
dyson_fan_state | enum | FAN, OFF (what the fan is actually doing)
dyson_fan_speed_units | gauge | 0-10 (or -1 if on AUTO)
dyson_oscillation_mode | enum | ON, OFF
dyson_focus_mode | enum | ON, OFF
dyson_heat_mode | enum | HEAT, OFF (OFF means "in cooling mode")
dyson_heat_state | enum | HEAT, OFF (what the fan is actually doing)
dyson_heat_target_celsius | gauge | target temperature (celsius)
dyson_quality_target_units | gauge | air quality target (1, 3, 5?)
dyson_filter_life_seconds | gauge | seconds of filter life remaining

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
