from __future__ import print_function
from apscheduler.schedulers.blocking import BlockingScheduler
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
      try:
        with open('config.json') as config_file:  
            config = json.load(config_file)
      
      except Exception as e:
          print("Could not open your config file. See README.md for more about config file.: " + str(e))

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

def getIndexofMonth(months, targetMonth):
    for possibleMonth in months:
        if possibleMonth:
            month = possibleMonth[0]
            dateObjectForMonth = datetime.strptime(month, '%B %Y')
            if dateObjectForMonth.month == targetMonth:
                return months.index(possibleMonth) + 1

def getMonthChaseCell(sheet, offsetFromCurrentMonth):

    BUDGET_SHEET_NAME = config['BUDGET_SHEET_NAME']
    SPREADSHEET_ID= config['SPREADSHEET_ID']
    MONTHS_COLUMN_RANGE = config['MONTHS_COLUMN_RANGE'] 
    CELLOFFSET_TO_MONTH = config['CELLOFFSET_TO_MONTH']
    COLUMN_TO_UPDATE = config['COLUMN_TO_UPDATE']

    monthrangeStr = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    try:
        resultMonths = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=monthrangeStr).execute()
        
        if resultMonths:
            months = resultMonths['values']
            creditcardPaymentMonth = datetime.now().date().month + 1 + offsetFromCurrentMonth if datetime.now().date().day < 22 else datetime.now().date().month + 2 + offsetFromCurrentMonth
            monthIndex = getIndexofMonth(months, creditcardPaymentMonth)
            chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
            chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
            return chaseSpentCell

    except Exception as e:
        print("Could not get months from spreadsheet because of: " + str(e))

def updateChaseSpentCell(totalBalance):

    SPREADSHEET_ID= config['SPREADSHEET_ID']
    
    try:
        googleSheetCreds = authGoogleSheets()
        service = build('sheets', 'v4', credentials=googleSheetCreds)
        sheet = service.spreadsheets()
    except Exception as e:
        print("Could not authenticate Google Sheets with account")

    #check if we are between 7th - 22nd day of month to know if we already paid last months balance
    if(datetime.now().date().day <= 7 or datetime.now().date().day >= 22):
        # -1 indicates -1 from current month, basically last month's value
        lastChaseSpentCell = getMonthChaseCell(sheet, -1)
        try:
            lastMonthsBalanceResponse = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range=lastChaseSpentCell, valueRenderOption='UNFORMATTED_VALUE').execute()
            lastMonthsBalance = float(lastMonthsBalanceResponse['values'][0][0])
        except Exception as e:
            print("Could not retrieve last months unpaid balance because: "+ str(e))
    else:
        lastMonthsBalance = 0

    chaseSpentCell = getMonthChaseCell(sheet,0)
        
    currentSpentThisMonth = round(totalBalance - lastMonthsBalance,2)
    updateValue = {"values":[[currentSpentThisMonth]]}

    try:
        chaseSpentResult = service.spreadsheets().values().update(spreadsheetId=SPREADSHEET_ID, range=chaseSpentCell, valueInputOption='RAW',body=updateValue).execute()
        print("Successfully updated budget sheet with chase spend amount of: $" + str(currentSpentThisMonth) )
    except Exception as e:
        print("Whoops could not update the spreadsheet because of: " + str(e) )


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
        balanceResponse = client.Accounts.balance.get(CHASE_ACCESS_TOKEN)
        balance = balanceResponse['accounts'][0]['balances']['available']
        limit = float(balanceResponse['accounts'][0]['balances']['limit'])
        return round(limit - balance, 2)
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Chase because the following error occured: ' + e.code + ':' + e.type)


def main():
    openConfig()

    chaseSpentAmount = getChaseSpent()* -1
    updateChaseSpentCell(chaseSpentAmount)

if __name__ == "__main__":
    main()