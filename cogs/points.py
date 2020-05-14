from __future__ import print_function

import discord
from discord.ext import commands
import configparser
import os
import os.path
import json
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials

officer_role = "@ОФИЦЕР"
user_start_points = 800


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

    @commands.command(
        aliases=["register", "reg", ""]
    )
    async def register_user(self, ctx):
        name_change = str(ctx.message.author.name)

        if await self.check_member(name_change):
            await ctx.send(f"{name_change} уже в базе")
        else:
            user_points = user_start_points
            self.SHEET.append_row([name_change, "Member", user_points])
            await ctx.send(f"Ля какой - {name_change} - {user_points} очков")
            
    @commands.command(
        aliases=["add", "remove", "reward", "отсыпь", "штраф", "корректировочка"]
    )
    async def process_user(self, ctx, *, message):
        """Fetch current prices from Data Project API.

        - Usage: <commandPrefix> price <item name>
        - Item name can also be its ID
        - Uses difflib for item name recognition.
        - Outputs as Discord Embed with thumbnail.
        - Plots 7 days historical prices.
        """

        await ctx.channel.trigger_typing()

        # Get command (price or quick)
        user_access = self.check_role(ctx)

        names_for_change = self.get_mentioned_users(ctx)

        points_change = re.search(r"[\+\-].\d*", message).group()
        points_change_num = points_change[1:]

        for name_change in names_for_change:
            member_found = await self.check_member(name_change)
            if member_found is False:
                await ctx.send(f"{name_change} левый пассажир")
                return

            if user_access:
                if points_change[0] == '+':
                    self.add_user_points(name_change, points_change_num)
                if points_change[0] == '-':
                    self.remove_points(name_change, points_change_num)
                new_points = self.get_user_points(name_change)
                await ctx.send(f"Ля какой - {name_change} - {new_points} очка")

        # Check if in workChannel
        if self.onlyWork:
            if ctx.channel.id not in self.workChannel:
                return


    @commands.command(
        aliases=["get", "покажи", "show"]
    )
    async def get_points(self, ctx, *, message):
        name_change = message.split(' ')[0]
        member_found = await self.check_member(name_change)
        if member_found is False:
            await ctx.send(f"{name_change} левый пассажир")
            return
        user_points = self.get_user_points(name_change)
        await ctx.send(f"Ля какой - {name_change} - {user_points} очков")


    @commands.command(
        aliases=["my", "чё как", "my points", "points", "очки"]
    )
    async def get_my_points(self, ctx):
        name_change = str(ctx.message.author)
        user_points = self.get_user_points(name_change)
        await ctx.send(f"Ля какой - {name_change} - {user_points} очков")

    def get_mentioned_users(self, ctx):
        mentions = ctx.message.mentions
        names = [str(mention.name) for mention in mentions]
        return names

    async def inv_obj(self, object):
        await self.debugChannel.send(f"object: {object}, type: {type(object)}")

    async def check_member(self, name):
        member_list = self.SHEET.get_all_records()
        user_name = str(name).replace("@", "")
        member_found = list(filter(lambda person: str(person['Name']) == user_name, member_list))
        if not member_found:
            return False
        else:
            return True


    def get_member(self, name):
        member_list = self.SHEET.get_all_records()
        member = list(filter(lambda person: person['Name'] == name, member_list))
        return member[0]


    def get_user_points(self, name):
        member = self.get_member(name)
        return member["Points"]


    def get_all_members(self):
        member_list = self.SHEET.get_all_records()
        return member_list


    def add_user_points(self, name, points):
        cell = self.SHEET.find(name)
        current_points = int(self.SHEET.cell(cell.row, cell.col+2).value)
        new_points = current_points + int(points)
        self.SHEET.update_cell(cell.row, cell.col+2, new_points)


    def remove_points(self, name, points):
        cell = self.SHEET.find(name)
        current_points = int(self.SHEET.cell(cell.row, cell.col+2).value)
        new_points = current_points - int(points)
        self.SHEET.update_cell(cell.row, cell.col+2, new_points)


    def check_role(self, ctx):
        needed_role = discord.utils.find(lambda r: r.name == officer_role, ctx.message.guild.roles)
        user_roles = ctx.message.author.roles
        access = any(str(role.name) == str(needed_role) for role in user_roles)
        return access

def setup(client):
    client.add_cog(MemberPoints(client))
