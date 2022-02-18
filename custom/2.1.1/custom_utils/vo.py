def get_vos(auth_state, user):
    used_authenticator = auth_state.get('oauth_user', {}).get(
        'used_authenticator_attr', 'unknown'
    )
    vo_config = user.authenticator.custom_config.get('vos', {})

    vos_with_weight = []
    for vo_name, vo_infos in vo_config.items():
        if (
            used_authenticator in vo_infos.get('authenticators', [])
            or user.name in vo_infos.get('usernames', [])
            or (user.admin and vo_infos.get('admin', False))
        ):
            vos_with_weight.append((vo_name, vo_infos.get('weight', 99)))
    vos_with_weight.sort(key=lambda x: x[1])

    vo_available = []
    for x in vos_with_weight:
        vo_available.append(x[0])
        if vo_config.get(x[0], {}).get('exclusive', False):
            vo_available = [x[0]]
            break

    vo_active = auth_state.get('vo_active', None)
    if not vo_active or vo_active not in vo_available:
        vo_active = vo_available[0]
    return vo_active, vo_available
