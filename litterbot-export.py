from prometheus_client import start_http_server, Summary, Gauge, Enum, Info
from pylitterbot import Account
import asyncio
import logging
import os
import time

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("litter-exporter")


# Set email and password for initial authentication.
username = os.environ.get('LITTERBOT_USERNAME')
password = os.environ.get('LITTERBOT_PASSWORD')


async def main():
    start_http_server(8000)

    # Create an account.
    account = Account()

    # Define metrics.
    robot_info = Info('litterbot_info', 'Robot info', ['serial'])
    online_enum = Enum('litterbot_online_state', 'Robot online state',
        ['serial'], states=['online', 'offline'])
    litter_level = Gauge('litterbot_litter_level', 'Level of litter', ['serial'])
    waste_level = Gauge('litterbot_waste_level', 'Level of waste', ['serial'])
    cycle_count = Gauge('litterbot_cycle_count', 'Number of cycles since last reset', ['serial'])

    while True:
        try:
            # Connect to the API and load robots.
            logger.info("Connecting to the API")
            await account.connect(username=username, password=password, load_robots=True)

            # Print robots associated with account.
            logger.info(f"Found {len(account.robots)} robots")
            for robot in account.robots:
                logger.info(f"Gather info for robot '{robot.name}' ({robot.serial})")
                robot_info.labels(robot.serial).info({
                    'name': robot.name,
                    'model': robot.model,
                })

                # Update the metrics values
                online_enum.labels(robot.serial).state('online' if robot.is_online else 'offline')

                waste_level.labels(robot.serial).set(robot.waste_drawer_level)
                litter_level.labels(robot.serial).set(robot.litter_level)
                cycle_count.labels(robot.serial).set(robot.cycle_count)

                #print(await robot.get_insight())
                #print(await robot.get_activity_history())

        finally:
            time.sleep(600)

if __name__ == "__main__":
    if username is None:
        logger.error("LITTERBOT_USERNAME environment variable not set")
        exit(1)

    if password is None:
        logger.error("LITTERBOT_PASSWORD environment variable not set")
        exit(1)

    asyncio.run(main())
