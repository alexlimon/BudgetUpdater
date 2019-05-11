# BudgetUpdater v 0.1
A simple python script that uses Plaid API's to retrieve credit card balance and update my personal budget spreadsheet using Google Sheet API's

You will most likely have to modify the code for your own needs, but this can help you get started with getting values from your bank account using plaid and writing it to your google sheets

1. To begin using this go through https://plaid.com/docs/quickstart/ (make sure Python is set as language on right hand corner) until you you reach the end of the access token section and make sure to request a sandbox, development or production API key before starting. After going through the excercise, keep in mind the access key as you will need it later. It will be output on the server when you complete the link front-end excercising of authenticating bank. USE AT YOUR OWN RISK

2. Go through steps 1 and 2 of https://developers.google.com/sheets/api/quickstart/python. You will need the credentials.json file output from this, and enable Google Sheets API on your google account

3. Populate the values below from using variables from step 1 and 2 above in the "config.json"

    "PLAID_CLIENT_ID": "", - Client ID that is given after signing up and setting up API Key with Plaid(Dev and Sandbox are free)
    
    "PLAID_SECRET": "", - Secret that is given after signing up and setting up API Key with Plaid(Dev and Sandbox are free)
    
    "PLAID_PUBLIC_KEY": "", - Public key that is given after signing up and setting up API Key with Plaid(Dev and Sandbox are free)
    
    "PLAID_ENV": "development", - Use the environment you choose for plaid (Dev, Prod requires approval from plaid, but sandbox does not)
    
    "CHASE_ACCESS_TOKEN": "", - Use the access token you got from the quick start. this will be shown in the output of your server once you finish authenticating. DOESNT HAVE to be chase, can be whatever bank you use. 
    
    "SPREADSHEET_ID": "", - Use a spreadsheet of choice from your google sheets library. The ID is in the link itself after the d backslash
https://docs.google.com/spreadsheets/d/<ID>
  
    "BUDGET_SHEET_NAME": "", - Use the name of the sheet that is in your spreadsheet, usually the tab below
    
    "MONTHS_COLUMN_RANGE": "A1:A36", - You can set this to A1 as long as its the current month + 1, or you can have a range of months in the following format "January 2019", "Feburary 2019" where each quote is a cell, and each cell is in the column you specified. I recommend leaving a few spaces between the months to leave space for the amount 
    
    "CELLOFFSET_TO_MONTH": 3, - This will place the actual spent amount 3 cells down from the month, but you can set any offset below, and it will place that number in the column specified below
    
    "COLUMN_TO_UPDATE": "B", - This will be the column where your spend amount will go and it will be at the offset from whatever you specified on top
    
    "GOOGLEDOC_CREDENTIALFILE_NAME": "credentials.json" - This is the credential file you got from step 2 of this readme
    
