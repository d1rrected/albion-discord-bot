import json
import os

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

# The ID and range of a sample spreadsheet.
test_action = 'get'
test_user = 'Cartsoon'
test_rang = 'Officer'


class MemberPointsManager():
    def __init__(self):
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file",
                 "https://www.googleapis.com/auth/drive"]
        # creds = json.loads(os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'))
        # with open('gcreds.json', 'w') as fp:
        #    json.dump(creds, fp)
        creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
        client = gspread.authorize(creds)
        self.sheet = client.open("albion_chopers_member_points").sheet1
        self.members_list = self.sheet.get_all_records()

        self.member = self.get_member(test_user)

    def get_all_members(self):
        return self.members_list

    def get_member(self, name):
        member = list(filter(lambda person: person['Name'] == name, self.members_list))
        return member[0]

    def get_output(self):
        output_string = self.member
        print(output_string)

    def get_points(self, name):
        member = self.get_member(name)
        return member["Points"]

    def add_points(self, name, points):
        cell = self.sheet.find(name)
        current_points = int(self.sheet.cell(cell.row, cell.col+2).value)
        new_points = current_points + points
        self.sheet.update_cell(cell.row, cell.col+2, new_points)

    def remove_points(self, name, points):
        cell = self.sheet.find(name)
        current_points = int(self.sheet.cell(cell.row, cell.col+2).value)
        new_points = current_points - points
        self.sheet.update_cell(cell.row, cell.col+2, new_points)


def main():
    # Extract and print all of the values
    manager = MemberPointsManager()
    manager.remove_points(test_user, 500)
    #print(points)

if __name__ == '__main__':
    main()
# [END sheets_quickstart]
