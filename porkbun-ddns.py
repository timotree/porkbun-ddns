"""A very, very basic DDNS for Porkbun using their direct API.

Assumptions:
1. There is already an existing 'A' record for the subdomain.
2. Only IPv4 supported.
3. IP address is determined for by icanhazip, with no manual override.
4. Zero error handling.
5. Very minimal logging, with optional output to a file.

API documentation: https://porkbun.com/api/json/v3/documentation
"""
import json
import logging
from typing import Any

import requests

CONFIG_FILE: str = "config.json"


def create_logger(logger_name: str, filename: str = None) -> logging.Logger:
    """Creates a logger object that logs at the info level.

    If a filename is provided then a file output stream will be added.

    Parameters
    ----------
    logger_name : str
        Name of the logger
    filename : str, optional
        Filename for output

    Returns
    -------
    logging.Logger
        Logger object
    """
    logger: logging.Logger = logging.getLogger(logger_name)
    level: int = logging.INFO
    logger.setLevel(level)

    log_format: str = "%(asctime)s - %(levelname)s - %(message)s"
    formatter: logging.Formatter = logging.Formatter(log_format)

    # Console handlers if they don't already exist
    if not logger.hasHandlers():
        # Create a stream handler for the console
        stream: logging.StreamHandler = logging.StreamHandler()
        stream.setLevel(level)
        stream.setFormatter(formatter)
        logger.addHandler(stream)

        # Create the optional file stream handler if requested
        if filename:
            file: logging.FileHandler = logging.FileHandler(filename, mode="w")
            file.setLevel(level)
            file.setFormatter(formatter)
            logger.addHandler(file)

    return logger


def edit_record(domain: str, data: dict[str, any]) -> bool:
    """Edit the existing 'A' record for the domain.

    Parameters
    ----------
    domain : str
        Domain name
    data : dict[str, any]
        Payload data

    Returns
    -------
    bool
        Result of edit request
    """
    api_base_url: str = "https://api-ipv4.porkbun.com/api/json/v3"
    url: str = f"{api_base_url}/dns/editByNameType/{domain}/A/"
    response: requests.Response = requests.post(url, data=json.dumps(data))

    return response.status_code == 200


def get_ip() -> str:
    """Ping icanhazip to retrieve our current IP address.

    Returns
    -------
    str
        IP address
    """
    response: requests.Response = requests.get("https://www.icanhazip.com/")

    # Strip the trailing newline character
    return response.text.rstrip()


def read_config() -> dict[str, any]:
    """Read configuration data from file.

    Return
    ------
    dict[str, any]
        Configuration data
    """
    with open(CONFIG_FILE) as file:
        config: dict[str, any] = json.load(file)

    return config


def save_config(config: dict[str, any]):
    """Save configuration data with the new IP.

    Parameters
    ----------
    config : dict[str, any]
        Configuration data
    """
    # Pretty print with indentation
    data: str = json.dumps(config, indent=2)
    with open(CONFIG_FILE, "w") as file:
        file.write(data)


def ping_healthchecks(uuid: str, body: str = None):
    """Pings your Healthchecks.io UUID.

    API documentation: https://healthchecks.io/docs/http_api/

    Parameters
    ----------
    uuid : str
        Unique identifier
    data : str, optional
        Additional diagnostic information
    """
    requests.post(f"https://hc-ping.com/{uuid}", data=body)


def main() -> int:
    """Main entry point.

    Return
    ------
    int
        Non-zero on error
    """
    logger: logging.Logger = create_logger(__name__, "porkbun_ddns.log")

    config: dict[str, Any] = read_config()
    uuid: str = config["healthchecksUUID"]
    domain: str = config["domain"]
    last_ip: str = config["lastIP"]

    logger.info("Getting current IP")
    current_ip: str = get_ip()

    logger.info(f"Last IP: {last_ip}")
    logger.info(f"Current IP: {current_ip}")

    # Only update if necessary. Porkbun will throw an error if the value is the same anyway.
    if current_ip != last_ip:
        data: dict[str, any] = {
            "apikey": config["apikey"],
            "secretapikey": config["secretapikey"],
            "content": current_ip,
            "ttl": 600,  # Default and minimum time (10 mins)
        }

        body = f"Updating 'A' record for {domain} with {current_ip}"
        logger.info(body)
        if not edit_record(domain, data):
            logger.error("Error updating record")
            # Ping won't be reached if edit_record() fails
            return 1

        logger.info("Update successful, saving config data")
        config["lastIP"] = current_ip
        save_config(config)
    else:
        body = "No change"
        logger.info(body)

    # Only ping Healthchecks if a UUID is provided
    if uuid:
        logger.info("Pinging Healthchecks.io")
        ping_healthchecks(uuid, body)

    logger.info("Finished")
    return 0


if __name__ == "__main__":
    main()
