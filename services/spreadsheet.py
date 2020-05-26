from __future__ import print_function

import configparser
import os
import os.path
import json
import gspread
import re
from oauth2client.service_account import ServiceAccountCredentials


class SpreadSheet():
    """
    Helper to work with google spreadsheets
    """

    def __init__(self, document, worksheet):
        # Load config.ini and get configs
        currentPath = os.path.dirname(os.path.realpath(__file__))
        configs = configparser.ConfigParser()
        configs.read(os.path.dirname(currentPath) + "/config.ini")
        self.DOCUMENT = document
        # API URLs
        self.SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file",
                       "https://www.googleapis.com/auth/drive"]

        creds_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

        if creds_json is None:
            home = os.path.expanduser("~")
            gcreds = f"{home}\\gcreds.json"
        else:
            self.CREDS = json.loads(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
            with open('gcreds.json', 'w') as fp:
                json.dump(self.CREDS, fp)
            gcreds = 'gcreds.json'
            
        creds = ServiceAccountCredentials.from_json_keyfile_name(gcreds, self.SCOPES)
        self.gclient = gspread.authorize(creds)
        self.SHEET = self.gclient.open(document).worksheet(worksheet)
        self.RECORDS = self.get_all_records()


    def find_and_fill_cell(self, cell_with_name, fill_row_number, fill_cell_value):
        cell = self.SHEET.find(cell_with_name)
        cell_row = cell.row
        self.SHEET.update_cell(cell_row, fill_row_number, fill_cell_value)

    def get_all_records(self):
        return self.SHEET.get_all_records()

    def check_row_value_exists(self, value):
        if any(obj['Id'] == value for obj in self.RECORDS):
            return True
        return False
        # for record in self.RECORDS:
        #     if record["Id"] == value:
        #         return True
        # return False
