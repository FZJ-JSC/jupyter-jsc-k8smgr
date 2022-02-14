from tornado import web

from jupyterhub.handlers.base import BaseHandler


class LinksHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        html = await self.render_template("links.html", user=user)
        self.finish(html)

     
class TwoFAHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        html = await self.render_template("2FA.html", user=user)
        self.finish(html)


class ImprintHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        html = await self.render_template("imprint.html", user=user)
        self.finish(html)
    

class DPSHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        html = await self.render_template("dps.html", user=user)
        self.finish(html)


class ToSHandler(BaseHandler):
    async def get(self):
        user = self.current_user
        html = await self.render_template("tos.html", user=user)
        self.finish(html)