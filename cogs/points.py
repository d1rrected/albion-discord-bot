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
import services.albionapi

officer_roles = "@ОФИЦЕР,@управление"
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

        self.albionapi = services.albionapi.AlbionApi()
        self.SHEET = glient.open("albion_choppers_member_points").sheet1

    @commands.command(
        aliases=["register", "reg"]
    )
    async def register_user(self, ctx):
        await ctx.channel.trigger_typing()
        await self.find_or_create_record(ctx, ctx.message.author.display_name)
            
    @commands.command(
        aliases=["ш", "д", "+", "-", "add", "remove", "reward", "отсыпь", "штраф", "корректировочка"]
    )
    async def process_user(self, ctx, *, message):
        await ctx.channel.trigger_typing()

        # Get command (price or quick)
        user_access = await self.check_role(ctx)

        message_text = ctx.message.content.replace("!", "")

        names_for_change = self.get_mentioned_users(ctx)
        points_change = re.search(r"[\+\-].\d*", message_text).group()
        points_change_num = points_change[1:]
        if user_access:
            for name_change in names_for_change:
                member_found = await self.check_member(name_change)
                if member_found is False:
                    await ctx.send(f"{name_change} не найден, регистрируем..")
                    await self.find_or_create_record(ctx, name_change, False)

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
                await self.find_or_create_record(ctx, name_change)
                return
            else:
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
            await self.find_or_create_record(ctx, name_change)
            return
        else:
            user_points = self.get_user_points(name_change)
            await ctx.send(f"Ля какой - {name_change} - {user_points} очков")

    async def find_or_create_record(self, ctx, username, send_output=True):
        name_change = self.member_name_with_tag(username)

        if await self.check_member(name_change):
            user_points = self.get_user_points(name_change)
            if send_output:
                await ctx.send(f"Ля какой - {name_change} - {user_points} очков")
        else:
            search_user = await self.SEARCH_CLASS.get_user(name_change)
            if search_user is None:
                await ctx.send(f"{name_change} не найден.")
                await ctx.send(f"Что-то пошло не так. Проверьте имя в discord или попробуйте позже.")
                return
            if str(search_user.alliance) == alliance:
                user_points = user_start_points
                self.SHEET.append_row([name_change, "Member", user_points])
                if send_output:
                    await ctx.send(f"Ля какой - {name_change} - {user_points} очков")
            else:
                await ctx.send(f"{name_change} не в альянсе.")
                return

    async def check_user_in_alliance(self, username):
        name = self.clean_name(username)

    async def inv_obj(self, object):
        await self.debugChannel.send(f"object: {object}, type: {type(object)}")

    async def check_member(self, name):
        member_list = self.SHEET.get_all_records()
        user_name = self.member_name_with_tag(str(name))
        if self.debug:
            await self.debugChannel.send(f"Check user = {user_name}")

        member_found = list(filter(lambda person: str(person['Name']).lower() == user_name.lower(), member_list))
        if not member_found:
            return False
        else:
            return True


    def get_member(self, name):
        member_list = self.SHEET.get_all_records()
        member = list(filter(lambda person: str(person['Name']).lower() == name.lower(), member_list))
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
        name = re.sub(r'\(.*?\)', '', name).replace("@", "").strip()
        return name

    def clean_name(self, member_name):
        name_with_tag = self.member_name_with_tag(member_name)
        name = re.sub(r'\[.*?\]', '', name_with_tag)
        name = name.strip()
        return name

    def remove_points(self, name, points):
        cell = self.SHEET.find(name)
        current_points = int(self.SHEET.cell(cell.row, cell.col+2).value)
        new_points = current_points - int(points)
        self.SHEET.update_cell(cell.row, cell.col+2, new_points)

    async def check_role(self, ctx):
        needed_role = discord.utils.find(lambda r: r.name in officer_roles, ctx.message.guild.roles)
        user_roles = ctx.message.author.roles
        access = any(str(role.name) == str(needed_role) for role in user_roles)
        return access
    
    @commands.command(
        aliases=["test"]
    )
    async def add_or_remove_points(self, ctx, *, message):
        await ctx.channel.trigger_typing()
        user_access = await self.check_user_access(ctx)
        if user_access is False:
            return await ctx.send(f"Ты не офицер, я тебя не знаю.")

        message_text = ctx.message.content.replace("!", "")
        names_for_change = self.get_mentioned_users(ctx)
        points_change = re.search(r"[\+\-].\d*", message_text).group()
        points_change_num = points_change[1:]

    def get_alliance_members(self):
        alliance_members_names = self.albionapi.get_all_alliance_member_names()
        return alliance_members_names

    def get_mentioned_users(self, ctx):
        mentions = ctx.message.mentions
        names = [self.member_name_with_tag(str(mention.display_name)) for mention in mentions]
        if names.count == 1:
            return names[0]
        return names

    async def check_user_access(self, ctx):
        needed_roles = officer_roles.split(',') 
        user_roles = ctx.message.author.roles
        for needed_role_name in needed_roles:
            for user_role in user_roles:
                need_role = str(needed_role_name).strip().lower().replace('@','')
                check_role = str(user_role.name).lower().replace('@','')
                if check_role == need_role:
                    return True
                #else:
                    #if self.debug:
                    #    await self.debugChannel.send(f"Checkrole. check_role = {check_role} ({type(check_role)}) not equal need_role = {need_role} ({type(need_role)})")
        return False

    def chunks(self, lst, n):
        """Yield successive n-sized chunks from lst."""
        for i in range(0, len(lst), n):
            yield lst[i:i + n]

    async def remove_member_roles(self, ctx, count, isTest=True):
        server_members = []
        for guild in self.client.guilds:
            for member in guild.members:
                server_members.append(member)
        
        alliance_members_names = self.get_alliance_members()
        # member_len = len(alliance_members_names)
        # (f"alliance_members_names is {alliance_members_names}, count is {member_len}")
        alliance_members_lower = [name.lower() for name in alliance_members_names]
        # chunks = self.chunks(alliance_members_lower, 150)
        
        #print(alliance_members_lower)
        for server_member in server_members[:count]:
            check_name = server_member.display_name
            member_found = False
            server_member_roles = server_member.roles
            roles_list = [role.name for role in server_member_roles]
            roles_list.remove("@everyone")
            # await self.inv_obj(roles_list)
            #for chunk in chunks:
            #    await self.debugChannel.send(f"alliance_members_lower = {chunk}")
            if len(roles_list) == 0:
                continue
            clean_name = self.clean_name(check_name.lower())
            print(f"Check {clean_name}")
            for ally_member in alliance_members_lower:
                if ally_member == clean_name:
                    member_found = True
                    if self.debug:
                        print(f"ally_member {ally_member} IS EQUAL clean_name {clean_name}")
            if not member_found:
                member_id = server_member.id
                print(f"member {clean_name} not found in alliance.")
                print(f"server_member is {server_member}")
                print(f"member_id is {member_id}")

                member = guild.get_member(member_id)
                print(f"member is {member}")
                if not isTest:
                    for role in server_member_roles:
                        await ctx.send(f"WE REMOVE ROLES FOR {check_name}. Remove role {role}")
                        await server_member.remove_roles(role)
                await ctx.send(f"{check_name} NOT in alliance. Remove roles: {roles_list}.")

    @commands.command(
        aliases=["rt"]
    )
    async def remove_roles(self, ctx, *, message):
        await ctx.channel.trigger_typing()
        user_access = await self.check_user_access(ctx)
        if user_access is False:
            return await ctx.send(f"Ты не офицер, я тебя не знаю.")

        message_text = ctx.message.content.replace("!", "")
        count = [int(s) for s in message_text.split() if s.isdigit()][0]

        await self.remove_member_roles(ctx, count)

    @commands.command(
        aliases=["sync"]
    )
    async def sync_members(self, ctx):
        await ctx.channel.trigger_typing()
        user_access = await self.check_user_access(ctx)
        if user_access is False:
            return await ctx.send(f"Ты не офицер, я тебя не знаю.")

        server_members = []
        for guild in self.client.guilds:
            for member in guild.members:
                server_members.append(member)
        
        alliance_members_names = self.get_alliance_members()
        # member_len = len(alliance_members_names)
        # (f"alliance_members_names is {alliance_members_names}, count is {member_len}")
        alliance_members_lower = [name.lower() for name in alliance_members_names]
        # chunks = self.chunks(alliance_members_lower, 150)
        
        #print(alliance_members_lower)
        for server_member in server_members:
            check_name = server_member.display_name
            member_found = False
            server_member_roles = server_member.roles
            roles_list = [role.name for role in server_member_roles]
            roles_list.remove("@everyone")
            # await self.inv_obj(roles_list)
            #for chunk in chunks:
            #    await self.debugChannel.send(f"alliance_members_lower = {chunk}")
            if len(roles_list) == 0:
                continue
            clean_name = self.clean_name(check_name.lower())
            print(f"Check {clean_name}")
            for ally_member in alliance_members_lower[:2]:
                if ally_member == clean_name:
                    member_found = True
                    if self.debug:
                        print(f"ally_member {ally_member} IS EQUAL clean_name {clean_name}")
            if not member_found:
                member_id = server_member.id
                member = guild.get_member(member_id)
                for role in server_member_roles:
                    await member.remove_roles(role)
                await ctx.send(f"{check_name} NOT in alliance. Roles is {roles_list}. Remove all roles.")



            #await self.debugChannel.send(f"member from aly is {e_member}")
        await ctx.send(f"Я кончил.")

def setup(client):
    client.add_cog(MemberPoints(client))
