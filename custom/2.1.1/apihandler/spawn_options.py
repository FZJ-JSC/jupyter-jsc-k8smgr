from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.scopes import needs_scope
from tornado import web


class SpawnUpdateOptionsAPIHandler(APIHandler):
    @needs_scope("access:servers")
    async def post(self, name, server_name=''):
        user = self.find_user(name)
        if user is None:
            # no such user
            raise web.HTTPError(404)
        if server_name not in user.spawners:
            # user has no such server
            raise web.HTTPError(404)
        orm_user = user.orm_user
        spawner = orm_user.orm_spawners[server_name]
        # Save new options
        new_user_options = self.get_json_body()
        try:
            self._check_keys(user, new_user_options)
        except KeyError as err:
            self.set_header("Content-Type", "text/plain")
            self.write(f"Bad Request - {str(err)}")
            self.set_status(400)
            return
        spawner.user_options = new_user_options
        self.db.commit()
        self.set_status(204)

    def _check_keys(self, user, data):
        keys = data.keys()
        custom_config = user.authenticator.custom_config
        unicore_systems = custom_config.get("systems").get("UNICORE")

        required_keys = {"options_input", "system_input"}
        if data.get("systems") in unicore_systems:
            required_keys = required_keys | {"account_input", "project_input", "partition_input"}
        allowed_keys = required_keys | {"resercation_input", "resource_nodes", "resource_gpus", "resource_runtime"}

        if not required_keys <= keys:
            raise KeyError(f"Keys must include {required_keys}, but got {keys}.")
        if not keys <= allowed_keys:
            raise KeyError(f"Got keys {keys}, but only {allowed_keys} are allowed.")
