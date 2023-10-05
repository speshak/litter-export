import prometheus_client
from prometheus_client import start_http_server, Gauge, Enum, Info, Histogram, REGISTRY
from pylitterbot import Account
import asyncio
import logging
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("litter-exporter")


# Set email and password for initial authentication.
username = os.environ.get('LITTERBOT_USERNAME')
password = os.environ.get('LITTERBOT_PASSWORD')

# Disable the default collectors
prometheus_client.REGISTRY.unregister(prometheus_client.GC_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PLATFORM_COLLECTOR)
prometheus_client.REGISTRY.unregister(prometheus_client.PROCESS_COLLECTOR)

class LitterbotCollector:
    def __init__(self, username: str, password: str):
        self.account = Account()
        self.username = username
        self.password = password

        # Define metrics.
        self.robot_info = Info('litterbot_info', 'Robot info', ['serial'])
        self.online_enum = Enum('litterbot_online_state', 'Robot online state',
                           ['serial'], states=['online', 'offline'])
        self.power_status = Enum('litterbot_power_state', 'Robot power state',
                           ['serial'], states=['AC', 'DC', 'NC'])
        self.litter_level = Gauge('litterbot_litter_level', 'Level of litter',
                             ['serial'])
        self.waste_level = Gauge('litterbot_waste_level', 'Level of waste', ['serial'])
        self.cycle_count = Gauge('litterbot_cycle_count',
                            'Number of cycles since last reset', ['serial'])
        self.cycle_count_after_full = Gauge('litterbot_cycle_after_full_count',
                            'Number of cycles since the drawer was reported as full', ['serial'])
        self.cycle_capacity = Gauge('litterbot_cycle_capacity',
                            'Predicted number of cycles before full', ['serial'])
        self.weight = Histogram('litterbot_weight', 'Weight of pet(s)', ['serial'],
                           buckets=tuple(range(2, 20)))
        self.night_light_level = Gauge('litterbot_night_light_level', "Brightness of night light", ['serial'])
        self.ave_cycles = Gauge('litterbot_average_cycles', "Average number of cycles per day", ['serial'])


    async def login(self):
        # Connect to the API and load robots.
        logger.info("Connecting to the API")
        await self.account.connect(
            username=self.username,
            password=self.password,
            load_robots=True)


    async def collect(self):
        await self.login()

        await asyncio.gather(
            self.collect_metrics(),
            self.collect_insights()
        )


    async def collect_metrics(self):
        while True:
            try:
                # Refresh isn't implemented for LitterRobot4, so instead we
                # just reload the robots. If it ever gets implemented, we can
                # switch to refresh_robots()
                await self.account.load_robots()

                logger.info(f"Found {len(self.account.robots)} robots")
                for robot in self.account.robots:
                    logger.info(f"Gather metrics for robot '{robot.name}' "
                                f"({robot.serial})")
                    self.robot_info.labels(robot.serial).info({
                        'name': robot.name,
                        'model': robot.model,
                    })

                    # Update the metrics values
                    self.online_enum.labels(robot.serial).state(
                        'online' if robot.is_online else 'offline')

                    self.waste_level.labels(robot.serial).set(robot.waste_drawer_level)
                    self.litter_level.labels(robot.serial).set(robot.litter_level)
                    self.cycle_count.labels(robot.serial).set(robot.cycle_count)
                    self.cycle_count_after_full.labels(robot.serial).set(robot.cycles_after_drawer_full)
                    self.cycle_capacity.labels(robot.serial).set(robot.cycle_capacity)
                    self.weight.labels(robot.serial).observe(robot.pet_weight)
                    self.night_light_level.labels(robot.serial).set(robot.night_light_level)
                    self.power_status.labels(robot.serial).state(robot.power_status)

            finally:
                logger.info(f"Sleeping metrics gathering for 10 minutes")
                await asyncio.sleep(600)


    async def collect_insights(self):
        """
        Get the insights data. This isn't updated as often, and hitting it too
        hard trips rate limiting.
        """
        while True:
            try:
                # Refresh isn't implemented for LitterRobot4, so instead we
                # just reload the robots. If it ever gets implemented, we can
                # switch to refresh_robots()
                await self.account.load_robots()

                for robot in self.account.robots:
                    logger.info(f"Gather insights for robot '{robot.name}' "
                                f"({robot.serial})")
                    # Unpack the insights metrics
                    insights = await robot.get_insight()
                    self.ave_cycles.labels(robot.serial).set(insights.average_cycles)

            finally:
                # Insights aren't updated very often, so we can sleep for a while so we
                # don't trip the rate limit
                logger.info(f"Sleeping insights gathering for 3 hours")
                await asyncio.sleep(60 * 60 * 3)


if __name__ == "__main__":
    if username is None:
        logger.error("LITTERBOT_USERNAME environment variable not set")
        exit(1)

    if password is None:
        logger.error("LITTERBOT_PASSWORD environment variable not set")
        exit(1)

    start_http_server(8000)

    collector = LitterbotCollector(username, password)
    asyncio.run(collector.collect())
