from __future__ import print_function
from apscheduler.schedulers.blocking import BlockingScheduler
import pickle
import os.path
from datetime import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import plaid
import calendar
import configparser

sched = BlockingScheduler()
config = None
google_sheets_service = None
plaid_service = None

@sched.scheduled_job('interval', minutes=30)
def main():
    global google_sheets_service
    global plaid_service

    open_config()

    google_sheets_service = build_google_sheet_service_for_acct()
    plaid_service = build_plaid_service()

    dollars_spent_on_amazon_credit_card = get_chase_spent_for_amazon_credit_card()
    update_cell_with_balance(dollars_spent_on_amazon_credit_card, last_month_balance_for_amazon_card_not_paid, get_amazon_credit_card_cell)

    dollars_in_checking = get_checking_account_money()
    update_cell_with_balance(dollars_in_checking, default_no_last_month, get_chase_checking_cell)

    dollars_in_savings = get_saving_account_money()
    update_cell_with_balance(dollars_in_savings, default_no_last_month, get_chase_saving_cell)

    dollars_spent_on_costco_credit_card = get_citi_spent_for_costco_credit_card()
    update_cell_with_balance(dollars_spent_on_costco_credit_card, last_month_balance_for_costco_card_not_paid, get_costco_credit_card_cell)

    dollars_in_robinhood = get_robinhood_money()
    update_cell_with_balance(dollars_in_robinhood, default_no_last_month, get_robinhood_investment_cell)
    
def open_config():
      global config
      config = configparser.ConfigParser()
      config.read('config.ini')

def build_google_sheet_service_for_acct():
    sheets_service= None
    try:
        google_sheet_creds = generate_google_sheets_creds()
        google_sheets_api = build('sheets', 'v4', credentials=google_sheet_creds)
        sheets_service = google_sheets_api.spreadsheets()
    except Exception as e:
        print("Could not authenticate Google Sheets with account: "+ str(e))
    return sheets_service

def build_plaid_service():
    PLAID_CLIENT_ID = config['plaid']['PLAID_CLIENT_ID']
    PLAID_SECRET = config['plaid']['PLAID_SECRET']
    PLAID_ENV = config['plaid']['PLAID_ENV']

    try:
        client = plaid.Client(client_id=PLAID_CLIENT_ID, secret=PLAID_SECRET, environment=PLAID_ENV, api_version='2019-05-29')
    except plaid.errors.PlaidError as e:
        print(e.code + ':' + e.type)
        client = None
    return client

def generate_google_sheets_creds():
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
    creds = None
    GOOGLEDOC_CREDENTIALFILE_NAME = config['googlesheets']['GOOGLEDOC_CREDENTIALFILE_NAME']
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

def get_chase_spent_for_amazon_credit_card():
    try:
        balanceResponse = plaid_service.Accounts.balance.get(config['plaid']['CHASE_ACCESS_TOKEN'])
        balance = balanceResponse['accounts'][1]['balances']['available']
        limit = float(balanceResponse['accounts'][1]['balances']['limit'])
        return round(limit - balance, 2) * -1
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Chase because the following error occured: ' + e.code + ':' + e.type)

def get_citi_spent_for_costco_credit_card():
    try:
        balanceResponse = plaid_service.Accounts.balance.get(config['plaid']['CITI_ACCESS_TOKEN'])
        balance = balanceResponse['accounts'][1]['balances']['available']
        limit = float(balanceResponse['accounts'][1]['balances']['limit'])
        return round(limit - balance, 2) * -1
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Citi because the following error occured: ' + e.code + ':' + e.type)

def get_robinhood_money():
    try:
        balanceResponse = plaid_service.Accounts.balance.get(config['plaid']['ROBINHOOD_ACCESS_TOKEN'])
        current_balance = float(balanceResponse['accounts'][0]['balances']['current'])
        return round(current_balance, 2)
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Robinhood because the following error occured: ' + e.code + ':' + e.type)

def get_checking_account_money():
    try:
        balanceResponse = plaid_service.Accounts.balance.get(config['plaid']['CHASE_ACCESS_TOKEN'])
        current_balance = float(balanceResponse['accounts'][0]['balances']['current'])
        return round(current_balance, 2)
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Robinhood because the following error occured: ' + e.code + ':' + e.type)

def get_saving_account_money():
    try:
        balanceResponse = plaid_service.Accounts.balance.get(config['plaid']['CHASE_ACCESS_TOKEN'])
        current_balance = float(balanceResponse['accounts'][2]['balances']['current'])
        return round(current_balance, 2)
    
    except plaid.errors.PlaidError as e:
        print('Could not get balances from Robinhood because the following error occured: ' + e.code + ':' + e.type)

def update_cell_with_balance(total_balance, check_if_last_month_balance_not_paid, get_sheet_cell):
    last_month_unpaid_balance = 0

    if check_if_last_month_balance_not_paid():
        last_month_balance_cell = get_sheet_cell(-1)
        try:
            last_month_balance_response = google_sheets_service.values().get(spreadsheetId=config.get("googlesheets",'SPREADSHEET_ID'), range=last_month_balance_cell, valueRenderOption='UNFORMATTED_VALUE').execute()
            last_month_unpaid_balance = float(last_month_balance_response['values'][0][0])
        except Exception as e:
            print("Could not retrieve last months unpaid balance because: "+ str(e))
            return

    sheet_cell_to_update_for_balance = get_sheet_cell(0)
        
    current_month_balance = round(total_balance - last_month_unpaid_balance, 2)
    google_sheets_payload = {"values":[[current_month_balance]]}

    try:
        google_sheets_service.values().update(spreadsheetId=config['googlesheets']['SPREADSHEET_ID'], range=sheet_cell_to_update_for_balance, valueInputOption='RAW',body=google_sheets_payload).execute()
        print("Successfully updated budget sheet with amount of: $" + str(current_month_balance) )
    except Exception as e:
        print("Whoops could not update the spreadsheet because of: " + str(e) )

def get_row_number_of_month(months, targetMonth):
    if targetMonth == 0:
         targetMonth = 12

    for possibleMonth in months:
        if possibleMonth:
            month = possibleMonth[0]
            dateObjectForMonth = datetime.strptime(month, '%B %Y')
            if dateObjectForMonth.month == targetMonth: #this assumes no duplicate month in the spreadsheet
                return months.index(possibleMonth) + 1

def get_amazon_credit_card_cell(offsetFromCurrentMonth):
    BUDGET_SHEET_NAME = config['googlesheets']['BUDGET_SHEET_NAME']
    MONTHS_COLUMN_RANGE = config['googlesheets']['MONTHS_COLUMN_RANGE'] 
    CELLOFFSET_TO_MONTH = config.getint('googlesheets','AMAZON_CC_VERTICAL_CELLOFFSET_TO_MONTH')
    COLUMN_TO_UPDATE = config['googlesheets']['CC_OWED_COLUMN']

    monthrangeStr = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    try:
        resultMonths = google_sheets_service.values().get(spreadsheetId=config['googlesheets']['SPREADSHEET_ID'], range=monthrangeStr).execute()
        
        if resultMonths:
            months = resultMonths['values']
            creditcardPaymentMonth = (datetime.now().date().month + 1 + offsetFromCurrentMonth)%12 if datetime.now().date().day < 22 else (datetime.now().date().month + 2 + offsetFromCurrentMonth) % 12
            monthIndex = get_row_number_of_month(months, creditcardPaymentMonth)
            chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
            chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
            return chaseSpentCell

    except Exception as e:
        print("Could not get months from spreadsheet because of: " + str(e))

def get_costco_credit_card_cell(offsetFromCurrentMonth):
    BUDGET_SHEET_NAME = config['googlesheets']['BUDGET_SHEET_NAME']
    MONTHS_COLUMN_RANGE = config['googlesheets']['MONTHS_COLUMN_RANGE'] 
    CELLOFFSET_TO_MONTH = config.getint('googlesheets','COSTCO_CC_VERTICAL_CELLOFFSET_TO_MONTH')
    COLUMN_TO_UPDATE = config['googlesheets']['CC_OWED_COLUMN']

    monthrangeStr = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    try:
        resultMonths = google_sheets_service.values().get(spreadsheetId=config['googlesheets']['SPREADSHEET_ID'], range=monthrangeStr).execute()
        
        if resultMonths:
            months = resultMonths['values']
            creditcardPaymentMonth = (datetime.now().date().month + 1 + offsetFromCurrentMonth)%12 if datetime.now().date().day < 18 else (datetime.now().date().month + 2 + offsetFromCurrentMonth) % 12
            monthIndex = get_row_number_of_month(months, creditcardPaymentMonth)
            chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
            chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
            return chaseSpentCell

    except Exception as e:
        print("Could not get months from spreadsheet because of: " + str(e))

def get_robinhood_investment_cell(offsetFromCurrentMonth):
    BUDGET_SHEET_NAME = config['googlesheets']['BUDGET_SHEET_NAME']
    MONTHS_COLUMN_RANGE = config['googlesheets']['MONTHS_COLUMN_RANGE'] 
    CELLOFFSET_TO_MONTH = config.getint('googlesheets','CURRENT_MONEY_VERTICAL_CELLOFFSET_TO_MONTH')
    COLUMN_TO_UPDATE = config['googlesheets']['INVESTMENT_COLUMN']

    monthrangeStr = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    try:
        resultMonths = google_sheets_service.values().get(spreadsheetId=config['googlesheets']['SPREADSHEET_ID'], range=monthrangeStr).execute()
        
        if resultMonths:
            months = resultMonths['values']
            currentMonth = datetime.now().date().month
            monthIndex = get_row_number_of_month(months, currentMonth)
            chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
            chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
            return chaseSpentCell

    except Exception as e:
        print("Could not get months from spreadsheet because of: " + str(e))

def get_chase_checking_cell(offsetFromCurrentMonth):
    BUDGET_SHEET_NAME = config['googlesheets']['BUDGET_SHEET_NAME']
    MONTHS_COLUMN_RANGE = config['googlesheets']['MONTHS_COLUMN_RANGE'] 
    CELLOFFSET_TO_MONTH = config.getint('googlesheets','CURRENT_MONEY_VERTICAL_CELLOFFSET_TO_MONTH')
    COLUMN_TO_UPDATE = config['googlesheets']['CHECKING_COLUMN']

    monthrangeStr = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    try:
        resultMonths = google_sheets_service.values().get(spreadsheetId=config['googlesheets']['SPREADSHEET_ID'], range=monthrangeStr).execute()
        
        if resultMonths:
            months = resultMonths['values']
            currentMonth = datetime.now().date().month
            monthIndex = get_row_number_of_month(months, currentMonth)
            chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
            chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
            return chaseSpentCell

    except Exception as e:
        print("Could not get months from spreadsheet because of: " + str(e))

def get_chase_saving_cell(offsetFromCurrentMonth):
    BUDGET_SHEET_NAME = config['googlesheets']['BUDGET_SHEET_NAME']
    MONTHS_COLUMN_RANGE = config['googlesheets']['MONTHS_COLUMN_RANGE'] 
    CELLOFFSET_TO_MONTH = config.getint('googlesheets','CURRENT_MONEY_VERTICAL_CELLOFFSET_TO_MONTH')
    COLUMN_TO_UPDATE = config['googlesheets']['SAVING_COLUMN']

    monthrangeStr = BUDGET_SHEET_NAME + "!" + MONTHS_COLUMN_RANGE

    try:
        resultMonths = google_sheets_service.values().get(spreadsheetId=config['googlesheets']['SPREADSHEET_ID'], range=monthrangeStr).execute()
        
        if resultMonths:
            months = resultMonths['values']
            currentMonth = datetime.now().date().month
            monthIndex = get_row_number_of_month(months, currentMonth)
            chaseSpentIndex = str(monthIndex + CELLOFFSET_TO_MONTH)
            chaseSpentCell = BUDGET_SHEET_NAME+ "!" + COLUMN_TO_UPDATE + chaseSpentIndex
            return chaseSpentCell

    except Exception as e:
        print("Could not get months from spreadsheet because of: " + str(e))

def last_month_balance_for_amazon_card_not_paid() -> bool:
    return datetime.now().date().day < get_first_tmobile_payday_of_month() or datetime.now().date().day >= 22

def last_month_balance_for_costco_card_not_paid()-> bool:
    return datetime.now().date().day < get_first_tmobile_payday_of_month() or datetime.now().date().day >= 18

def default_no_last_month():
    return False

def get_first_tmobile_payday_of_month():
    calendarInstance = calendar.Calendar(firstweekday=calendar.SUNDAY)
    currentDate = datetime.now().date()
    weeksInMonth = calendarInstance.monthdatescalendar(currentDate.year, currentDate.month)

    #return the first friday of the month that falls on payday
    if weeksInMonth[0][5].isocalendar()[1] % 2 == 1:
        return weeksInMonth[0][5].day
    return weeksInMonth[1][5].day

sched.start()