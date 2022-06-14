import logging
import os

import requests
from django.apps import AppConfig
from jupyterjsc_k8smgr.settings import LOGGER_NAME
from services.utils import _config

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class K8SServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"

    def _get_tunnel_k8smgr_hostname(self, config, logs_extra={}):
        log.trace("Retrieve tunnel k8smgr hostname", extra=logs_extra)
        k8smgr_hostname = config.get("tunnel", {}).get("k8smgr_hostname", "")
        return k8smgr_hostname

    def _get_tunnel_url(self, config, logs_extra={}):
        log.trace("Retrieve tunnel url", extra=logs_extra)
        tunnel_url = config.get("tunnel", {}).get("restart_url", "")
        return tunnel_url

    def _get_tunnel_credentials(self, config, logs_extra={}):
        log.trace("Retrieve tunnel credentials", extra=logs_extra)
        env_name = config.get("tunnel", {}).get("credentials_env_name", "TUNNEL_BASIC")
        log.trace(f"Looking for secret at {env_name}", extra=logs_extra)
        cred = os.environ.get(env_name, "")
        if not cred:
            log.trace("Credentials not found. Look in config.", extra=logs_extra)
            cred_config = config.get("tunnel", {}).get("credentials_basic64", "")
            if cred_config:
                log.critical(
                    "Credentials found in config file. You should use secrets with env variables instead.",
                    extra=logs_extra,
                )
                cred = cred_config
        return cred

    def restart_tunnels(self):
        config = _config()
        logs_extra = {"uuidcode": "StartUp"}
        tunnel_restart_url = self._get_tunnel_url(config, logs_extra=logs_extra)
        tunnel_cred = self._get_tunnel_credentials(config, logs_extra=logs_extra)
        tunnel_k8smgr_hostname = self._get_tunnel_k8smgr_hostname(
            config, logs_extra=logs_extra
        )
        tunnel_timeout = config.get("tunnel", {}).get("timeout", 10)
        tunnel_verify = config.get("tunnel", {}).get("certificate_path", False)
        if not tunnel_restart_url or not tunnel_cred:
            log.critical(
                f"Tunnel url ({tunnel_restart_url}) or tunnel credential ({tunnel_cred}) is missing. Cannot restart tunnels.",
                extra=logs_extra,
            )
            return
        headers = {
            "Content-Type": "application/json",
            "Authorization": tunnel_cred,
        }
        data = {"hostname": tunnel_k8smgr_hostname}
        log.debug(
            f"Call Tunnel service with POST {tunnel_restart_url} ...", extra=logs_extra
        )
        r = requests.post(
            url=tunnel_restart_url,
            headers=headers,
            json=data,
            timeout=tunnel_timeout,
            verify=tunnel_verify,
        )
        r.raise_for_status()
        log.debug(
            f"Call Tunnel service with POST {tunnel_restart_url} ... done",
            extra=logs_extra,
        )

    def create_user(self, username, passwd, groups=[], superuser=False, mail=""):
        from django.contrib.auth.models import Group
        from django.contrib.auth.models import User

        if User.objects.filter(username=username).exists():
            return
        log.info(f"Create user {username}", extra={"uuidcode": "StartUp"})
        if superuser:
            User.objects.create_superuser(username, mail, passwd)
            return
        else:
            user = User.objects.create(username=username)
            user.set_password(passwd)
            user.save()
        for group in groups:
            if not Group.objects.filter(name=group).exists():
                Group.objects.create(name=group)
            _group = Group.objects.filter(name=group).first()
            user.groups.add(_group)

    def setup_logger(self):
        from logs.models import HandlerModel

        data = {
            "handler": "stream",
            "configuration": {
                "level": 10,
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
        }
        HandlerModel(**data).save()

    def setup_db(self):
        user_groups = {
            "jupyterhub": ["access_to_webservice", "access_to_logging"],
        }

        superuser_name = "admin"
        superuser_mail = os.environ.get("SUPERUSER_MAIL", "admin@example.com")
        superuser_pass = os.environ["SUPERUSER_PASS"]
        self.create_user(
            superuser_name, superuser_pass, superuser=True, mail=superuser_mail
        )

        for username, groups in user_groups.items():
            userpass = os.environ.get(f"{username.upper()}_USER_PASS", None)
            if userpass:
                self.create_user(username, userpass, groups=groups)

    def ready(self):
        if os.environ.get("GUNICORN_START", "false").lower() == "true":
            self.setup_logger()
            self.setup_db()
            try:
                self.restart_tunnels()
            except:
                log.exception("Unexpected error during startup")

        return super().ready()
