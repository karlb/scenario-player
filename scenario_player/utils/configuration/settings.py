from typing import Callable, Union

import structlog

from scenario_player.constants import GAS_STRATEGIES, TIMEOUT
from scenario_player.exceptions.config import ScenarioConfigurationError, ServiceConfigurationError
from scenario_player.utils.configuration.base import ConfigMapping

log = structlog.get_logger(__name__)


class PFSSettingsConfig(ConfigMapping):
    """UDC Service Settings interface.

    Example scenario yaml::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          ...
          services:
            ...
            pfs:
              url: http://pfs.raiden.network
            ...
    """

    def __init__(self, loaded_yaml: dict):
        super(PFSSettingsConfig, self).__init__(
            loaded_yaml.get("settings").get("services", {}).get("pfs", {})
        )
        self.validate()

    @property
    def url(self):
        return self.get("url")


class UDCSettingsConfig(ConfigMapping):
    """UDC Service Settings interface.

    Example scenario yaml::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          ...
          services:
            ...
            udc:
              enable: True
              address: 0x1000001
              token:
                deposit: True
            ...
    """

    def __init__(self, loaded_yaml: dict):
        services_dict = (loaded_yaml.get("settings") or {}).get("services") or {}
        super(UDCSettingsConfig, self).__init__(services_dict.get("udc", {}))
        self.validate()

    @property
    def enable(self):
        return self.get("enable", False)

    @property
    def address(self):
        return self.get("address")

    @property
    def token(self):
        return self.get("token", {"deposit": False})


class ServiceSettingsConfig(ConfigMapping):
    """Service Configuration Setting interface.

    Does nothing special but delegate attribute-based access
    to raiden service settings.
    """

    CONFIGURATION_ERROR = ServiceConfigurationError

    def __init__(self, loaded_yaml: dict):
        super(ServiceSettingsConfig, self).__init__(
            (loaded_yaml.get("settings") or {}).get("services") or {}
        )
        self.pfs = PFSSettingsConfig(loaded_yaml)
        self.udc = UDCSettingsConfig(loaded_yaml)
        self.validate()


class SettingsConfig(ConfigMapping):
    """Settings Configuration Setting interface and validator.

    Handles default values as well as exception handling on missing settings.

    The configuration present at the given path will automatically be checked for
    critical errors, such as missing or mutually exclusive keys.

    Example scenario yaml::

        >my_scenario.yaml
        version: 2
        ...
        settings:
          timeout: 55
          notify: False
          chain: any
          gas_price: fast
          services:
            <ServicesSettingsConfig>
        ...

    """

    CONFIGURATION_ERROR = ScenarioConfigurationError

    def __init__(self, loaded_yaml: dict) -> None:
        super(SettingsConfig, self).__init__(loaded_yaml.get("settings") or {})
        self.services = ServiceSettingsConfig(loaded_yaml)
        self.validate()

    def validate(self):
        self.assert_option(
            isinstance(self.gas_price, (int, str)),
            f"Gas Price must be an integer or one of "
            f"{list(GAS_STRATEGIES.keys())}, not {self.gas_price}",
        )
        if isinstance(self.gas_price, str):
            self.assert_option(
                self.gas_price in GAS_STRATEGIES,
                f"Gas Price must be an integer or one of "
                f"{list(GAS_STRATEGIES.keys())}, not {self.gas_price}",
            )

    @property
    def timeout(self) -> int:
        """Returns the scenario's set timeout in seconds."""
        return self.get("timeout", TIMEOUT)

    @property
    def notify(self) -> Union[str, None]:
        """Return the email address to which notifications are to be sent.

        If this isn't set, we return None.
        """
        return self.get("notify")

    @property
    def chain(self) -> str:
        """Return the name of the chain to be used for this scenario."""
        return self.get("chain", "any")

    @property
    def gas_price(self) -> str:
        """Return the configured gas price for this scenario.

        This defaults to 'fast'.
        """
        gas_price = self.get("gas_price", "fast")
        if isinstance(gas_price, str):
            return gas_price.upper()
        return gas_price

    @property
    def gas_price_strategy(self) -> Callable:
        """Return the gas price strategy callable requested in :attr:`.gas_price`.

        If the price is an int, the callable will always return :attr:`.gas_price`.

        If the price is a string, we fetch the appropriate callable from :mod:`web3`.

        :raises ValueError: If the strategy cannot be found.
        """
        if isinstance(self.gas_price, int):

            def fixed_gas_price(*_, **__):
                return self.gas_price

            return fixed_gas_price

        try:
            return GAS_STRATEGIES[self.gas_price.upper()]
        except KeyError:
            raise ValueError(f'Invalid gas_price value: "{self.gas_price}"')
