# prometheus_dyson
Prometheus client for DysonLink fans (e.g; Pure Hot+Cool and Pure Cool).

This code supports Dyson Pure Cool and Pure Hot+Cool fans. This supports both
the V1 model (reports VOC and Dust) and the V2 models (those that report
PM2.5, PM10, NOx, and VOC). Other Dyson fans may work out of the box or with
minor modifications.

## Help! It stopped working!

_(Updated: 7th March 2021)_

Hi! If you use this and it's not working now (but it was before), you're likely
affected by etheralm/libpurecool#37. The long-and-short of it is that Dyson
changed their _unpublished_ online API, which broke `libpurecool` which we
rely on. You won't notice this breakage until you try to restart
prometheus-dyson.

There is an _experimental_ fix in the libdyson branch. This begins a process
of switching this exporter over toto shenxn/libdyson (which should provide for
long-term stability against this type of problem).

To give it a go (once you've checked out the most recent source):

1. Build from the `libdyson` branch
1. Run the binary with `--create_device_cache`, follow the prompts
   and add the generated configuration to your prometheus-dyson.ini.
1. Restart the service as normal.

Rough set of steps:
```
% git clone https://github.com/seanrees/prometheus-dyson.git prometheus-dyson
% cd prometheus-dyson
% git checkout libdyson
% bazel run :main -- --config=path-to-your-config.ini --create_device_cache
```

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
dyson_oscillation_mode | enum | all |  ON if the fan in oscillation mode, OFF otherwise
dyson_oscillation_state | enum | all | ON, OFF, IDLE. ON means the fan is currently oscillating, IDLE means the fan is in auto mode and the fan is paused
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
