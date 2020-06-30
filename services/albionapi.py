import urllib.request
import json
import datetime as DT
import statistics
import difflib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import configparser
import os
from statistics import mean
import numpy

class AlbionApi():
    """
    Helper to work with albionapi
    """

    def __init__(self):
        # Load config.ini and get configs
        currentPath = os.path.dirname(os.path.realpath(__file__))
        configs = configparser.ConfigParser()
        configs.read(os.path.dirname(currentPath) + "/config.ini")
        
        # API URLs
        self.iconURL = "https://gameinfo.albiononline.com/api/gameinfo/items/"
        # Latest
        self.apiURL = "https://www.albion-online-data.com/api/v2/stats/prices/"
        self.locationURL = "?locations=Caerleon,Lymhurst,Martlock,Bridgewatch,FortSterling,Thetford,ArthursRest,MerlynsRest,MorganasRest,BlackMarket"
        # Historical
        self.historyURL = "https://www.albion-online-data.com/api/v1/stats/charts/"
        self.historyLocationURL = "&locations=BlackMarket"

        self.itemDataURL = "https://gameinfo.albiononline.com/api/gameinfo/items/"

        self.allianceURL = (
            "https://gameinfo.albiononline.com/api/gameinfo/alliances/"  # + ID
        )
        self.guildURL = (
            "https://gameinfo.albiononline.com/api/gameinfo/guilds/"  # + ID + /members
        )
        self.playerURL = (
            "https://gameinfo.albiononline.com/api/gameinfo/players/"  # + ID
        )
        self.searchURL = (
            "https://gameinfo.albiononline.com/api/gameinfo/search?q="  # + name
        )

        # Bot will search items through this list
        # There are also different localization names
        self.itemList = os.path.dirname(currentPath) + "\\item_data.json"

    def get_item(self, item_name):
        itemNames, itemIDs = self.item_match(item_name)
        return itemNames[0], itemIDs[0]
    
    def get_item_min_price(self, item_id, cities):
        fullURL = self.apiURL + item_id + f"?locations={cities}"
        with urllib.request.urlopen(fullURL) as url:
            data = json.loads(url.read().decode())

        min_price = data[0]["sell_price_min"]
        return min_price

    def get_craft_resources_list(self, item_id):
        fullURL = self.itemDataURL + item_id + "/data"
        with urllib.request.urlopen(fullURL) as url:
            data = json.loads(url.read().decode())
        craft_items = data["craftingRequirements"]["craftResourceList"]
        return craft_items

    def get_all_equipment_id_from_itemdata(self):
        # Open list of items
        try:
            with open(self.itemList, "r", encoding="utf-8") as inFile:
                data = json.load(inFile)
        except Exception as e:
            print(e)        
        items_data = []
        for (i, indivData) in enumerate(data):
            try:
                item_type = indivData["LocalizedDescriptions"]["EN-US"]
            except:
                continue
            if 'Equipment Item' in item_type and '_ARENA_' not in indivData["UniqueName"]:
                item_id = indivData["UniqueName"]
                item_name = indivData["LocalizedNames"]["EN-US"]
                items_data.append((str(item_id), str(item_name)))        
        return items_data

    def get_item_data_by_id(self, item_id):
        items_ids = []
        return items_ids

    def get_item_blackmarket_price(self, item_id):
        fullURL = self.apiURL + item_id + f"?locations=BlackMarket"
        with urllib.request.urlopen(fullURL) as url:
            data = json.loads(url.read().decode())

        prices_list = []
        for price in data:
            pr = price["buy_price_min"]
            prices_list.append(int(pr))

        mid_prices = numpy.array(prices_list)
        mid_prices.sort()
        prices_with_removed_min_and_max = mid_prices[1:][:-1]
        if prices_with_removed_min_and_max.any():
            average_price = mean(prices_with_removed_min_and_max)
            return int(average_price)            
        else:
            return 0

    def get_item_blackmarket_history_price(self, item_id):
        today = DT.datetime.utcnow()
        numDays = 0
        date = (today - DT.timedelta(days=numDays)).strftime("%m-%d-%Y")
        prices_minAll = [[]]
        timestampsAll = [[]]

        fullURL = self.historyURL + item_id + "?date=" + date + self.historyLocationURL
        with urllib.request.urlopen(fullURL) as url:
            prices = json.loads(url.read().decode())

        if not prices:
            return 0, 0
        else:
            avg_price = prices[0]["data"]["prices_avg"][0]
        
        items_count = prices[0]["data"]["item_count"][0]
        
        return avg_price, items_count

    def item_match(self, inputWord):
        """Find closest matching item name and ID of input item.

        - Matches both item ID (UniqueName) and item name (LocalizedNames)
        - Uses difflib.
        - Returns 4 closest match.
        """

        itemNames = []
        itemIDs = []
        jDists = []

        # Open list of items
        try:
            with open(self.itemList, "r", encoding="utf-8") as inFile:
                data = json.load(inFile)
        except Exception as e:
            print(e)

        # Loop through each item in item_data.json
        # Store distance and item index of each item
        for (i, indivData) in enumerate(data):

            # Calculate distance for item ID (UniqueName)
            try:
                w1 = inputWord.lower()
                w2 = indivData["UniqueName"].lower()

                # Use difflib's SequenceMatcher
                jDist = 1 - difflib.SequenceMatcher(None, w1, w2).ratio()
                jDists.append([jDist, i])

            # If item has no 'UniqueName'
            except:
                # Max distance is 1
                jDists.append([1, i])

            # Calculate distance for item name (LocalizedNames)
            try:
                w1 = inputWord.lower()

                # Get distance for all localizations
                localDists = []
                for name in indivData["LocalizedNames"]:
                    w2 = indivData["LocalizedNames"][name].lower()

                    localDist = 1 - difflib.SequenceMatcher(None, w1, w2).ratio()
                    localDists.append(localDist)

                # Pick the closest distance as jDist
                jDist = min(localDists)
                jDists.append([jDist, i])

            # If item has no 'LocalizedNames'
            except:
                jDists.append([1, i])

        # Sort JDists
        # Closest match has lowest distance
        jDists = sorted(jDists)

        # Get item names and IDs of first 4 closest match
        itemNames = [data[jDist[1]]["LocalizedNames"]["EN-US"] for jDist in jDists[:4]]
        itemIDs = [data[jDist[1]]["UniqueName"] for jDist in jDists[:4]]

        return itemNames, itemIDs


    def search_guild(self, guildName):
        guildNameUrl = guildName.replace(" ", "%20")
        fullURL = self.searchURL + guildNameUrl
        with urllib.request.urlopen(fullURL) as url:
            data = json.loads(url.read().decode())
        guilds = data["guilds"]
        for guild in guilds:
            if guild["Name"] == guildName:
                return guild
        return ""

    def get_guild(self, guildId):
        fullURL = self.guildURL + guildId
        with urllib.request.urlopen(fullURL) as url:
            data = json.loads(url.read().decode())
        return data

    def request_api(self, url, retry_count = 10):
        success = False
        retry_num = 0
        while not success:
            try:
                if retry_num > retry_count:
                    break
                with urllib.request.urlopen(url) as url:
                    data = json.loads(url.read().decode())
                    success = True
            except:
                retry_num = retry_num + 1
                continue
        return data

    def get_guild_members(self, guildId):
        fullURL = self.guildURL + guildId + '/members'
        data = self.request_api(fullURL)
        return data

    def get_alliance(self, allianceId):
        fullURL = self.allianceURL + allianceId
        with urllib.request.urlopen(fullURL) as url:
            data = json.loads(url.read().decode())
        return data

    def get_our_alliance(self, myGuild='Albion Choppers'):
        guild = ap.search_guild(myGuild)
        alliance_id = guild["AllianceId"]
        return self.get_alliance(alliance_id)

    def get_all_alliance_member_names(self):
        result_list = []
        alliance_guilds = self.get_our_alliance()["Guilds"]
        for guild_in_alliance in alliance_guilds:
            guild_members = self.get_guild_members(guild_in_alliance["Id"])
            names = [member["Name"] for member in guild_members]
            result_list = result_list + names
        return result_list


#ap = AlbionApi()
#all_members = ap.get_all_alliance_member_names()
#all_members