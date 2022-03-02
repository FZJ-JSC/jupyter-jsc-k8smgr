import json
import os


class VoException(Exception):
     def __init__(self, message):
        self.message = message
        super().__init__(message)


def get_vos(auth_state, custom_config, username, admin):
    used_authenticator = auth_state.get("oauth_user", {}).get(
        "used_authenticator_attr", "unknown"
    )
    vo_config = custom_config.get("vos", {})

    vos_with_weight = []
    for vo_name, vo_infos in vo_config.items():
        if (
            used_authenticator in vo_infos.get("authenticators", [])
            or username in vo_infos.get("usernames", [])
            or (admin and vo_infos.get("admin", False))
        ):
            vos_with_weight.append((vo_name, vo_infos.get("weight", 99)))
    vos_with_weight.sort(key=lambda x: x[1])
    
    vo_available = []
    for x in vos_with_weight:
        vo_available.append(x[0])
        if vo_config.get(x[0], {}).get("exclusive", False):
            vo_available = [x[0]]
            break
    if len(vo_available) == 0:
        raise VoException(f"No vo available for user {username}")

    vo_active = auth_state.get("vo_active", None)
    if not vo_active or vo_active not in vo_available:
        vo_active = vo_available[0]
    return vo_active, vo_available


def get_reservations():
    reservations_path = os.environ.get("RESERVATIONS_PATH")
    with open(reservations_path, "r") as f:
        reservations = json.load(f)
    return reservations


def get_maintenance_list():
    maintenance_path = os.environ.get("MAINTENANCE_PATH")
    with open(maintenance_path, "r") as f:
        maintenance_list = json.load(f)
    return maintenance_list