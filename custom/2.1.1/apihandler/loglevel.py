import json
import os

from jupyterhub.apihandlers import APIHandler
from jupyterhub.utils import admin_only
from tornado.httpclient import HTTPRequest

from custom_utils.backend_services import drf_request
from custom_utils.backend_services import drf_request_properties
from logs import create_logging_handler
from logs import remove_logging_handler
from logs.extra_handlers import default_configurations
from logs.utils import supported_handler_classes
from logs.utils import supported_formatter_classes


valid_handlers = [h for h in supported_handler_classes]
valid_formatters = [f for f in supported_formatter_classes]
valid_levels = [0, 5, 10, 20, 30, 40, 50, 99,
                "NOTSET", "TRACE", "DEBUG", "INFO", "WARN","WARNING", 
                "ERROR",  "FATAL","CRITICAL","DEACTIVATE"]


def get_config():
    try:
        with open(os.environ.get("LOGGING_CONFIG_FILE", "logging.json"), "r") as f:
            config = json.load(f)
    except:
        config = default_configurations
    return config


class JHubLogLevelAPIHandler(APIHandler):
    def validate_data(self, data):
        pass

    @admin_only
    async def get(self, handler=''):
        current_config = get_config()
        try:
            if handler:
                log_config = current_config.get(handler)
                data = {
                    "handler": handler,
                    "configuration": log_config
                }
            else:
                data = []
                for handler in current_config:
                    data.append({
                        "handler": handler,
                        "configuration": current_config.get(handler)
                    })
            self.write(json.dumps(data))
            self.set_status(200)
        except:
            self.set_status(400)

    @admin_only
    async def post(self):
        current_config = get_config()
        data = self.get_json_body()
        handler = data.get("handler")
        handler_config = data.get("configuration")
        if handler in current_config:
            self.set_status(400)
            return
        try:
            self.validate_data(handler_config)
        except:
            self.set_status(400)
            return
        create_logging_handler(current_config, handler, **handler_config)
        self.log.info(f"Created {handler} log handler", extra={"data": data})
        self.set_status(200)

    @admin_only
    async def patch(self, handler):
        current_config = get_config()
        if handler not in current_config:
            self.set_status(400)
            return
        data = self.get_json_body()
        handler = data.get("handler")
        handler_config = data.get("configuration")
        try:
            self.validate_data(handler_config)
        except:
            self.set_status(400)
            return

        remove_logging_handler(current_config, handler)
        create_logging_handler(current_config, handler, **handler_config)
        self.log.info(f"Updated {handler} log handler", extra={"data": data})
        self.set_status(200)

    @admin_only
    async def delete(self, handler):
        current_config = get_config()
        if handler not in current_config:
            self.set_status(400)
            return
        remove_logging_handler(current_config, handler)
        self.log.info(f"Removed {handler} log handler")
        self.set_status(200)
        

class DRFServiceLogLevelAPIHandler(APIHandler):
    async def _drf_request(self, service, handler="", method="GET", body=None):
        custom_config = self.authenticator.custom_config
        req_prop = drf_request_properties(
            service, custom_config, self.log, None
        )
        log_url = req_prop.get("urls", {}).get("logs", "None")
        if handler:
            log_url = log_url + handler + "/"
        req = HTTPRequest(
            log_url ,
            method=method,
            headers=req_prop["headers"],
            request_timeout=req_prop["request_timeout"],
            validate_cert=req_prop["validate_cert"],
            ca_certs=req_prop["ca_certs"],
        )
        if body:
            req.body = json.dumps(body)
        resp = await drf_request(
            req,
            self.log,
            self.authenticator.fetch,
            parse_json=True,
            raise_exception=True,
        )
        return resp

    @admin_only
    async def get(self, service, handler=''):
        resp = await self._drf_request(service, handler)
        self.write(json.dumps(resp))
        self.set_status(200)

    @admin_only
    async def post(self, service):
        await self._drf_request(service, method="POST", body=self.get_json_body())
        self.set_status(200)

    @admin_only
    async def patch(self, service, handler):
        if not handler:
            self.set_status(400)
            return
        await self._drf_request(service, handler, method="PUT", body=self.get_json_body())
        self.set_status(200)

    @admin_only
    async def delete(self, service, handler):
        if not handler:
            self.set_status(400)
            return
        await self._drf_request(service, handler, method="DELETE")
        self.set_status(200)