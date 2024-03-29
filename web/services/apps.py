import logging
import os

import requests
from django.apps import AppConfig
from jupyterjsc_k8smgr.settings import LOGGER_NAME
from services.utils import _config
from services.utils.k8s import k8s_delete_userjobs_svc
from services.utils.ssh import cancel
from services.utils.ssh import forward

log = logging.getLogger(LOGGER_NAME)
assert log.__class__.__name__ == "ExtraLoggerClass"


class K8SServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"

    def restart_userjobs_tunnels(self):
        from services.models import UserJobsModel

        logs_extra = {"uuidcode": "StartUp"}
        log.info("Start all tunnels for userjobs saved in database", extra=logs_extra)
        userjobs = UserJobsModel.objects.all()
        for userjob in userjobs:
            try:
                forward(
                    userjob.used_ports,
                    userjob.hostname,
                    userjob.target_node,
                    logs_extra,
                )
            except:
                log.exception("Could not create tunnels for userjob", extra=logs_extra)
                try:
                    cancel(
                        userjob.used_ports,
                        userjob.hostname,
                        userjob.target_node,
                        logs_extra,
                    )
                except:
                    log.exception(
                        "Could not cancel tunnels for userjob", extra=logs_extra
                    )
                try:
                    k8s_delete_userjobs_svc(userjob.service, logs_extra)
                except:
                    log.exception("Could not remove userjob-svc", extra=logs_extra)
                userjob.delete()
        log.info(
            "Start all tunnels for userjobs saved in database done", extra=logs_extra
        )

    def restart_tunnels(self):
        config = _config()
        logs_extra = {"uuidcode": "StartUp"}
        for jhub in config.get("tunnel", []):
            try:
                stage = os.environ.get("STAGE", "").lower()
                restart_url = jhub.get("stage", {}).get(stage, {}).get("restart_url", None)
                if not restart_url:
                    restart_url = jhub.get("restart_url", "")
                restart_hostname = jhub.get("hostname", "")
                # defined in entrypoint.sh
                restart_cred_env_name = jhub.get("cred_env_name", "TUNNEL_BASIC")
                restart_cred = os.environ.get(restart_cred_env_name, "")
                restart_timeout = jhub.get("timeout", 10)
                restart_verify = jhub.get("certificate_path", False)
                if not restart_url or not restart_cred:
                    log.critical(
                        f"Tunnel url ({restart_url}) or tunnel credential ({restart_cred}) is missing. Cannot restart tunnels.",
                        extra=logs_extra,
                    )
                    continue
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": restart_cred,
                    "uuidcode": "StartUp",
                }
                data = {"hostname": restart_hostname}
                log.debug(
                    f"Call Tunnel service with POST {restart_url} ...", extra=logs_extra
                )
                r = requests.post(
                    url=restart_url,
                    headers=headers,
                    json=data,
                    timeout=restart_timeout,
                    verify=restart_verify,
                )
                r.raise_for_status()
                log.debug(
                    f"Call Tunnel service with POST {restart_url} ... done",
                    extra=logs_extra,
                )
            except:
                logs_extra["jhub"] = jhub
                log.exception("Tunnel restart for failed", extra=logs_extra)
                del logs_extra["jhub"]
                continue

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
        config = _config()
        user_groups = config.get("startup", {}).get("create_user", {})

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
            else:
                log.info(
                    f"Do not create user {username} - password is missing",
                    extra={"uuidcode": "StartUp"},
                )

    def ready(self):
        if os.environ.get("GUNICORN_START", "false").lower() == "true":
            self.setup_logger()
            self.setup_db()
            try:
                self.restart_tunnels()
            except:
                log.exception("Unexpected error during startup")
            try:
                self.restart_userjobs_tunnels()
            except:
                log.exception("Unexpected error during startup")

        return super().ready()
