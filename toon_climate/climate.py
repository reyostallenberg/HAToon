"""
Support for Eneco's Toon thermostats.
Only the rooted version.

configuration.yaml

climate:
  - platform: toon_climate
    name: Toon Thermostat
    host: IP_ADDRESS
    port: 10080
    scan_interval: 10
"""
import logging
import json
import voluptuous as vol

from homeassistant.components.climate import (ClimateDevice, PLATFORM_SCHEMA)
from homeassistant.components.climate.const import (SUPPORT_TARGET_TEMPERATURE, SUPPORT_OPERATION_MODE)
from homeassistant.const import (CONF_NAME, CONF_HOST, CONF_PORT,
                                 TEMP_CELSIUS, ATTR_TEMPERATURE)
import homeassistant.helpers.config_validation as cv

import requests

SUPPORT_FLAGS = SUPPORT_TARGET_TEMPERATURE | SUPPORT_OPERATION_MODE

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'Toon Thermostat'
DEFAULT_TIMEOUT = 5
BASE_URL = 'http://{0}:{1}{2}'

ATTR_MODE = 'mode'
STATE_MANUAL = 'manual'
STATE_UNKNOWN = 'unknown'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Required(CONF_HOST): cv.string,
    vol.Optional(CONF_PORT, default=10800): cv.positive_int,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Toon thermostat."""
    add_devices([ThermostatDevice(config.get(CONF_NAME), config.get(CONF_HOST),
                            config.get(CONF_PORT))])

# pylint: disable=abstract-method
# pylint: disable=too-many-instance-attributes
class ThermostatDevice(ClimateDevice):
    """Representation of a Toon thermostat."""

    def __init__(self, name, host, port):
        """Initialize the thermostat."""
        self._data = None
        self._name = name
        self._host = host
        self._port = port
        self._current_temp = None
        self._current_setpoint = None
        self._current_state = -1
        self._current_operation = ''
        self._set_state = None
        self._operation_list = ['Comfort', 'Home', 'Sleep', 'Away', 'Holiday']
        _LOGGER.debug("Init called")
        self.update()

    @staticmethod
    def do_api_request(url):
        """Does an API request."""
        req = requests.get(url, timeout=DEFAULT_TIMEOUT)
        if req.status_code != requests.codes.ok:
            _LOGGER.exception("Error doing API request")
        else:
            _LOGGER.debug("API request ok %d", req.status_code)

        """Fixes invalid JSON output by TOON"""
        reqinvalid = req.text
        reqvalid = reqinvalid.replace('",}', '"}')

        return json.loads(req.text)

    @property
    def should_poll(self):
        """Polling needed for thermostat."""
        _LOGGER.debug("Should_Poll called")
        return True

    def update(self):
        """Update the data from the thermostat."""
        self._data = self.do_api_request(BASE_URL.format(
            self._host,
            self._port,
            '/happ_thermstat?action=getThermostatInfo'))
        self._current_setpoint = int(self._data['currentSetpoint'])/100
        self._current_temp = int(self._data['currentTemp'])/100
        self._current_state = int(self._data['activeState'])
        _LOGGER.debug("Update called")

    @property
    def supported_features(self):
        """Return the list of supported features."""
        return SUPPORT_FLAGS

    @property
    def name(self):
        """Return the name of the thermostat."""
        return self._name

    @property
    def device_state_attributes(self):
        """Return the device specific state attributes."""
        return {
            ATTR_MODE: self._current_state
        }

    @property
    def temperature_unit(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temp

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._current_setpoint

    @property
    def current_operation(self):
        """Return the current state of the thermostat."""
        state = self._current_state
        if state in (0, 1, 2, 3, 4):
            return self._operation_list[state]
        elif state == -1:
            return STATE_MANUAL
        else:
            return STATE_UNKNOWN

    @property
    def operation_list(self):
        """List of available operation modes."""
        return self._operation_list

    def set_operation_mode(self, operation_mode):
        """Set HVAC mode (comfort, home, sleep, away, holiday)."""
        if operation_mode == "Comfort":
            mode = 0
        elif operation_mode == "Home":
            mode = 1
        elif operation_mode == "Sleep":
            mode = 2
        elif operation_mode == "Away":
            mode = 3
        elif operation_mode == "Holiday":
            mode = 4

        self._data = self.do_api_request(BASE_URL.format(
            self._host,
            self._port,
            '/happ_thermstat?action=changeSchemeState'
            '&state=2&temperatureState='+str(mode)))
        _LOGGER.debug("Set operation mode=%s(%s)", str(operation_mode),
                      str(mode))

    def set_temperature(self, **kwargs):
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)*100
        if temperature is None:
            return
        else:
            self._data = self.do_api_request(BASE_URL.format(
                self._host,
                self._port,
                '/happ_thermstat?action=setSetpoint'
                '&Setpoint='+str(temperature)))
            _LOGGER.debug("Set temperature=%s", str(temperature))
