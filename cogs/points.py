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
from cogs.search import Search

officer_roles = "@ОФИЦЕР, @Управление"
alliance = "ARCH4"
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

        self.SEARCH_CLASS = Search(client)

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
        aliases=["register", "reg"]
    )
    async def register_user(self, ctx):
        await ctx.channel.trigger_typing()
        name_change = self.member_name_with_tag(str(ctx.message.author.display_name))
        search_user = await self.SEARCH_CLASS.get_user(name_change)
        if str(search_user.alliance) == alliance:
            if await self.check_member(name_change):
                user_points = self.get_user_points(name_change)
                await ctx.send(f"Ля какой - {name_change} - {user_points} очков")
            else:
                user_points = user_start_points
                self.SHEET.append_row([name_change, "Member", user_points])
                await ctx.send(f"Ля какой - {name_change} - {user_points} очков")
        else:
            await ctx.send(f"{name_change} не в альянсе")
            return
            
    @commands.command(
        aliases=["add", "remove", "reward", "отсыпь", "штраф", "корректировочка"]
    )
    async def process_user(self, ctx, *, message):

        await ctx.channel.trigger_typing()

        # Get command (price or quick)
        user_access = await self.check_role(ctx)

        names_for_change = self.get_mentioned_users(ctx)

        points_change = re.search(r"[\+\-].\d*", message).group()
        points_change_num = points_change[1:]

        for name_change in names_for_change:
            member_found = await self.check_member(name_change)
            if member_found is False:
                await ctx.send(f"{name_change} не найден")
                return

            if user_access:
                if points_change[0] == '+':
                    self.add_user_points(name_change, points_change_num)
                if points_change[0] == '-':
                    self.remove_points(name_change, points_change_num)
                new_points = self.get_user_points(name_change)
                await ctx.send(f"Ля какой - {name_change} - {new_points} очков")
            else:
                await ctx.send(f"Ты не офицер, я тебя не знаю.")

        # Check if in workChannel
        if self.onlyWork:
            if ctx.channel.id not in self.workChannel:
                return

    @commands.command(
        aliases=["get", "покажи", "show"]
    )
    async def get_points(self, ctx, *, message):
        names_change_list = self.get_mentioned_users(ctx)
        for name_change in names_change_list:
            member_found = await self.check_member(name_change)
            if member_found is False:
                await ctx.send(f"{name_change} не найден, регистрируем..")
                await self.register_user(ctx)
                return
            user_points = self.get_user_points(name_change)
            await ctx.send(f"Ля какой - {name_change} - {user_points} очков")


    @commands.command(
        aliases=["my", "чё как", "me", "points", "очки"]
    )
    async def get_my_points(self, ctx):
        name_change = self.member_name_with_tag(str(ctx.message.author.display_name))
        member_found = await self.check_member(name_change)
        if member_found is False:
            await ctx.send(f"{name_change} не найден, регистрируем..")
            await self.register_user(ctx)
            return

        user_points = self.get_user_points(name_change)
        await ctx.send(f"Ля какой - {name_change} - {user_points} очков")

    def get_mentioned_users(self, ctx):
        mentions = ctx.message.mentions
        names = [self.member_name_with_tag(str(mention.display_name)) for mention in mentions]
        if names.count == 1:
            return names[0]
        return names


    async def inv_obj(self, object):
        await self.debugChannel.send(f"object: {object}, type: {type(object)}")

    async def check_member(self, name):
        member_list = self.SHEET.get_all_records()
        user_name = self.member_name_with_tag(str(name))
        if self.debug:
            await self.debugChannel.send(f"UserName = {user_name}")
        member_found = list(filter(lambda person: str(person['Name']).lower == user_name.lower, member_list))
        if not member_found:
            return False
        else:
            return True

    def get_member(self, name):
        member_list = self.SHEET.get_all_records()
        member = list(filter(lambda person: str(person['Name']).lower == name.lower, member_list))
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

    def member_name_with_tag(self, name):
        name = re.sub(r'\(.*?\)', '', name).replace(" ", "").replace("@", "")
        return name

    def remove_points(self, name, points):
        cell = self.SHEET.find(name)
        current_points = int(self.SHEET.cell(cell.row, cell.col+2).value)
        new_points = current_points - int(points)
        self.SHEET.update_cell(cell.row, cell.col+2, new_points)

    async def check_role(self, ctx):
        needed_role = discord.utils.find(lambda r: r.name in officer_roles, ctx.message.guild.roles)
        user_roles = ctx.message.author.roles
        if self.debug:
            await self.debugChannel.send(f"user_roles: {user_roles}")
            await self.debugChannel.send(f"officer_roles: {officer_roles}")
        access = any(str(role.name) == str(needed_role) for role in user_roles)
        return access

def setup(client):
    client.add_cog(MemberPoints(client))
