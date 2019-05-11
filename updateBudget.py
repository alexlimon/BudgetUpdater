from __future__ import print_function
import pickle
import os.path
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import plaid
import json

config = None

def openConfig():
      global config
      with open('config.json') as config_file:  
        config = json.load(config_file)

def authGoogleSheets():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    GOOGLEDOC_CREDENTIALFILE_NAME = config['GOOGLEDOC_CREDENTIALFILE_NAME']
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLEDOC_CREDENTIALFILE_NAME, SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return creds

def findIndexOfCurrentMonthInList(months):
    
    creditcardPaymentMonth = datetime.now().date().month + 1 if datetime.now().date().day < 22 else datetime.now().date().month + 2

    for possibleMonth in months:
        if possibleMonth:
            month = possibleMonth[0]
            dateObjectForMonth = datetime.strptime(month, '%B %Y')
            if dateObjectForMonth.month == creditcardPaymentMonth:
                return months.index(possibleMonth) + 1

def updateChaseSpentCell(currentSpent):

    SPREADSHEET_ID= config['SPREADSHEET_ID']
    BUDGET_SHEET_NAME = config['BUDGET_SHEET_NAME']
    MONTHS_COLUMN_RANGE = config['MONTHS_COLUMN_RANGE']
    COLUMN_TO_UPDATE = config['COLUMN_TO_UPDATE']
    CELLOFFSET_TO_MONTH = config['CELLOFFSET_TO_MONTH']

    monthrangeName = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    googleSheetCreds = authGoogleSheets()
    
    service = build('sheets', 'v4', credentials=googleSheetCreds)
    # Call the Sheets API
    sheet = service.spreadsheets()
    
    resultMonths = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=monthrangeName).execute()
    
    if resultMonths:
        months = resultMonths['values']
        monthIndex = findIndexOfCurrentMonthInList(months)

        chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
        chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
        updateValue = {"values":[[currentSpent]]}
        chaseSpentResult = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=chaseSpentCell, valueInputOption='RAW',body=updateValue).execute()

def pretty_print_response(response):
  print(json.dumps(response, indent=2, sort_keys=True))
  
def authPlaidClient():

    PLAID_CLIENT_ID = config['PLAID_CLIENT_ID']
    PLAID_SECRET = config['PLAID_SECRET']
    PLAID_PUBLIC_KEY = config['PLAID_PUBLIC_KEY']
    PLAID_ENV = config['PLAID_ENV']

    try:
        client = plaid.Client(client_id=PLAID_CLIENT_ID, secret=PLAID_SECRET,
                      public_key=PLAID_PUBLIC_KEY, environment=PLAID_ENV, api_version='2018-05-22')
    except plaid.errors.PlaidError as e:
        print(e.code + ':' + e.type)
        client = None
    return client

def initChaseToken(client, access_token):
    try:
        client.Item.public_token.create(access_token)
    except plaid.errors.PlaidError as e:
        print('Could not get public access token for Chase because the following error occured: '+ e.code + ':' + e.type)


def getChaseSpent():

    CHASE_ACCESS_TOKEN = config['CHASE_ACCESS_TOKEN']
    
    client = authPlaidClient()

    if client:
        initChaseToken(client, CHASE_ACCESS_TOKEN)
  
    try:
        balance_response = client.Accounts.balance.get(CHASE_ACCESS_TOKEN)
        balance = balance_response['accounts'][0]['balances']['available']
        limit = float(balance_response['accounts'][0]['balances']['limit'])
        return round(limit - balance, 2)
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Chase because the following error occured: ' + e.code + ':' + e.type)

def main():
    try:
        openConfig()
    except Exception as e:
        print("Could not open your config file. See README.md for more about config file.: " + str(e))
  
    try:
        chaseSpentAmount = getChaseSpent()
        updateChaseSpentCell(chaseSpentAmount)
        print("Successfully updated budget sheet with chase spend amount of: $" + str(chaseSpentAmount) )
    except Exception as e:
        print("Whoops could not update the spreadsheet because of:"+ str(e) )

if __name__ == '__main__':
   main()



    
    

   
    
    
    