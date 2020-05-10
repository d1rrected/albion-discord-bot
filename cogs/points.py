from __future__ import print_function

import discord
from discord.ext import commands
import configparser
import os
import os.path
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

officer_role = "@yoba_admin"

class MemberPoints(commands.Cog):
    """Cog that add and remove alliance member points

    Commands:
        - reward
            Add or remove member points

    Functions:
    """


    def __init__(self, client):
        self.client = client

        # Load config.ini and get configs
        currentPath = os.path.dirname(os.path.realpath(__file__))
        configs = configparser.ConfigParser()
        configs.read(os.path.dirname(currentPath) + "/config.ini")

        debugChannel = int(configs["Channels"]["debugChannelID"])
        workChannel = [
            int(ID) for ID in configs["Channels"]["workChannelID"].split(", ")
        ]
        self.debugChannel = client.get_channel(debugChannel)
        self.workChannel = workChannel

        self.onlyWork = configs["General"].getboolean("onlyWork")
        self.debug = configs["General"].getboolean("debug")

        # API URLs
        self.SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file",
                       "https://www.googleapis.com/auth/drive"]
        self.CREDS = json.loads(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
        with open('gcreds.json', 'w') as fp:
            json.dump(self.CREDS, fp)
        creds = ServiceAccountCredentials.from_json_keyfile_name('gcreds.json', self.SCOPES)
        glient = gspread.authorize(creds)

        self.SHEET = glient.open("albion_choppers_member_points").sheet1
        self.MEMBERS_LIST = self.SHEET.get_all_records()

    @commands.command(
        aliases=["add", "reward"]
    )
    async def add_points(self, ctx, *, name):
        """Fetch current prices from Data Project API.

        - Usage: <commandPrefix> price <item name>
        - Item name can also be its ID
        - Uses difflib for item name recognition.
        - Outputs as Discord Embed with thumbnail.
        - Plots 7 days historical prices.
        """

        # Get command (price or quick)
        command = ctx.message.content.split()

        # Debug message
        if self.debug:
            await self.debugChannel.send(f"Check user {ctx.author} roles")

            needed_role = discord.utils.find(lambda r: r.name == officer_role, ctx.message.guild.roles)
            await self.debugChannel.send(f"needed_role {needed_role}")

            user_roles = ctx.message.author.roles
            await self.debugChannel.send(f"user_roles {user_roles}")


            await self.debugChannel.send(f"Author roles: {ctx.message.author.roles}")
            await self.debugChannel.send(f"{ctx.author} -> {ctx.message.content} {name}")
            await self.debugChannel.send(f"{self.MEMBERS_LIST}")

        # Check if in workChannel
        if self.onlyWork:
            if ctx.channel.id not in self.workChannel:
                return

        await ctx.channel.trigger_typing()

        if ctx.message.content:
            await self.workChannel.send(f"End of debug")

        # Create Discord embed
        em = discord.Embed(
            title=f"Member points."
        )

def check_user_access(ctx, user):


def setup(client):
    client.add_cog(MemberPoints(client))
