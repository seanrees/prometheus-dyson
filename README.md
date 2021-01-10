# prometheus_dyson
Prometheus client for DysonLink fans (e.g; Pure Hot+Cool and Pure Cool).

This code supports Dyson Pure Cool and Pure Hot+Cool fans. This supports both
the V1 model (reports VOC and Dust) and the V2 models (those that report
PM2.5, PM10, NOx, and VOC). Other Dyson fans may work out of the box or with
minor modifications.

## Build

```
% bazel build :main
```

If you'd like a Debian package:
```
% bazel build :main-deb
```

### Without Bazel

Tip: a [Python virtual environment](https://docs.python.org/3/tutorial/venv.html) is a very useful
tool for keeping dependencies local to the project (rather than system-wide or in your home
directory). This is _optional_ and not required.

You'll need these dependencies:

```
% pip install libpurecool
% pip install prometheus_client
```


## Metrics

### Environmental

Name | Type | Availability | Description
---- | ---- | ------------ | -----------
dyson_humidity_percent | gauge | all | relative humidity percentage
dyson_temperature_celsius | gauge | all | ambient temperature in celsius
dyson_volatile_organic_compounds_units | gauge | all | volatile organic compounds (range 0-10)
dyson_dust_units | gauge | V1 fans only | dust level (range 0-10)
dyson_pm25_units | gauge | V2 fans only | PM2.5 units (µg/m^3 ?)
dyson_pm10_units | gauge | V2 fans only | PM10 units (µg/m^3 ?)
dyson_nitrogen_oxide_units | gauge | V2 fans only | Nitrogen Oxide (NOx) levels (range 0-10)


### Operational

Name | Type | Availability | Description
---- | ---- | ------------ | -----------
dyson_fan_mode | enum | all |  AUTO, FAN, OFF (what the fan is set to)
dyson_fan_power | enum | all | ON if the fan is powered on, OFF otherwise
dyson_auto_mode | enum | all | ON if the fan is in auto mode, OFF otherwise
dyson_fan_state | enum | all |  FAN, OFF (what the fan is actually doing)
dyson_fan_speed_units | gauge | all | 0-10 (or -1 if on AUTO)
dyson_oscillation_mode | enum | all |  ON if the fan is oscillating, OFF otherwise
dyson_oscillation_angle_low_degrees | gauge | V2 fans only | low angle of oscillation in degrees
dyson_oscillation_angle_high_degrees | gauge | V2 fans only | high angle of oscillation in degrees
dyson_night_mode | enum | all | ON if the fan is in night mode, OFF otherwise
dyson_night_mode_speed | gauge | V2 fans only | maximum speed of the fan in night mode
dyson_heat_mode | enum | all heating fans | HEAT, OFF (OFF means "in cooling mode")
dyson_heat_state | enum | all heating fans | only HEAT, OFF (what the fan is actually doing)
dyson_heat_target_celsius | gauge | all heating fans | target temperature (celsius)
dyson_focus_mode | enum | V1 heating only | ON if the fan is providing a focused stream, OFF otherwise
dyson_quality_target_units | gauge | V1 fans only | air quality target (1, 3, 5?)
dyson_filter_life_seconds | gauge | V1 fans only | seconds of filter life remaining
dyson_carbon_filter_life_percent | gauge | V2 fans only | percent remaining of the carbon filter
dyson_hepa_filter_life_percent | gauge | V2 fans only | percent remaining of the HEPA filter
dyson_continuous_monitoring_mode | gauge | V2 fans only | continuous monitoring of air quality (ON, OFF)

## Usage

### Configuration

This script reads `config.ini` (or another file, specified with `--config`)
for your DysonLink login credentials.

### Args
```
% ./prometheus_dyson.py --help
usage: ./prometheus_dyson.py [-h] [--port PORT] [--config CONFIG] [--log_level LOG_LEVEL] [--include_inactive_devices]

optional arguments:
  -h, --help            show this help message and exit
  --port PORT           HTTP server port
  --config CONFIG       Configuration file (INI file)
  --log_level LOG_LEVEL
                        Logging level (DEBUG, INFO, WARNING, ERROR)
  --include_inactive_devices
                        Monitor devices marked as inactive by Dyson (default is only active)
```

### Scrape Frequency

Metrics are updated at approximately 30 second intervals by `libpurecool`.
Fan state changes (e.g; FAN -> HEAT) are published ~immediately on change.

### Other Notes

`libpurecool` by default uses a flavour of mDNS to automatically discover
the Dyson fan. If automatic discovery isn't available on your network, it is possible
to specify IP addresses mapped to device serial numbers in config.ini - see
`config-sample.ini` for usage.

## Dashboard

I've provided a sample Grafana dashboard in `grafana.json`.
