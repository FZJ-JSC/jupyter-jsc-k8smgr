import json
import os

from jupyterhub.apihandlers import APIHandler
from jupyterhub.utils import admin_only

from logs import create_logging_handler
from logs import remove_logging_handler
from logs.utils import supported_handler_classes
from logs.utils import supported_formatter_classes

valid_handlers = [h for h in supported_handler_classes]
valid_formatters = [f for f in supported_formatter_classes]
valid_levels = [0, 5, 10, 20, 30, 40, 50, 99,
                "NOTSET", "TRACE", "DEBUG", "INFO", "WARN","WARNING", 
                "ERROR",  "FATAL","CRITICAL","DEACTIVATE"]

class LogLevelAPIHandler(APIHandler):
    def validate_data(self, data):
        pass

    @admin_only
    async def get(self, handler=''):
        with open(os.environ.get("LOGGING_CONFIG_FILE", "logging.json"), "r") as f:
            config = json.load(f)

        try:
            if handler:
                log_info = config.get(handler)
            else:
                log_info = config
            self.write(json.dumps(log_info))
            self.set_status(200)
        except:
            self.set_status(400)

    @admin_only
    async def post(self, handler):
        with open(os.environ.get("LOGGING_CONFIG_FILE", "logging.json"), "r") as f:
            config = json.load(f)

        if handler in config:
            self.set_status(400)
            return

        data = self.request.body.decode("utf8")
        if type(data) != dict:
            try:
                data = json.loads(data)
            except:
                self.log.exception(
                    "Incoming data not correct",
                    extra={"class": self.__class__.__name__, "data": data},
                )
                self.set_status(400)
                return

        try:
            self.validate_data(data)
        except:
            self.set_status(400)
            return

        create_logging_handler(config, handler, **data)
        self.log.info(f"Updated {handler} log handler", extra={"data": data})
        self.set_status(200)

    @admin_only
    async def patch(self, handler):
        with open(os.environ.get("LOGGING_CONFIG_FILE", "logging.json"), "r") as f:
            config = json.load(f)

        if handler not in config:
            self.set_status(400)
            return

        data = self.request.body.decode("utf8")
        if type(data) != dict:
            try:
                data = json.loads(data)
            except:
                self.log.exception(
                    "Incoming data not correct",
                    extra={"class": self.__class__.__name__, "data": data},
                )
                self.set_status(400)
                return

        try:
            self.validate_data(data)
        except:
            self.set_status(400)
            return

        remove_logging_handler(config, handler)
        create_logging_handler(config, handler)
        self.set_status(200)

    @admin_only
    async def delete(self, handler):
        with open(os.environ.get("LOGGING_CONFIG_FILE", "logging.json"), "r") as f:
            config = json.load(f)

        if handler not in config:
            self.set_status(400)
            return

        remove_logging_handler(config, handler)
        self.log.info(f"Removed {handler} log handler")
        self.set_status(200)
        
    