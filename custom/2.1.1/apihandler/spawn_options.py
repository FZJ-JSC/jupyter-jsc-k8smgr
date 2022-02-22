from jupyterhub.apihandlers.base import APIHandler
from jupyterhub.scopes import needs_scope
from tornado import web

from custom_utils import check_formdata_keys

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
        formdata = self.get_json_body()
        try:
            check_formdata_keys(formdata, user.authenticator.custom_config)
        except KeyError as err:
            self.set_header("Content-Type", "text/plain")
            self.write(f"Bad Request - {str(err)}")
            self.set_status(400)
            return
        spawner.user_options = formdata
        self.db.commit()
        self.set_status(204)
