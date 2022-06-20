import base64

from algosdk.future import transaction
from algosdk import account, mnemonic, logic
from algosdk.v2client import algod
from pyteal import *
import algosdk.encoding as e
from algosdk import constants
from time import time


# user declared account mnemonics
creator_mnemonic = "equip increase middle blade achieve drama brother enter punch hour push bunker maple work moment patrol silver lady swear key sphere destroy matter absent ripple"
funder_mnemonic = "father scrap upset giggle strike vital occur access live spider client sorry wood build chase describe genius outdoor hockey scissors oval steak addict abstract when"
# user declared algod connection parameters. Node must have EnableDeveloperAPI set to true in its config
algod_address = "https://testnet-api.algonode.cloud"
algod_token = ""

# helper function to compile program source
def compile_program(client, source_code):
    compile_response = client.compile(source_code)
    return base64.b64decode(compile_response['result'])

# helper function that converts a mnemonic passphrase into a private signing key
def get_private_key_from_mnemonic(mn) :
    private_key = mnemonic.to_private_key(mn)
    return private_key


# helper function that formats global state for printing
def format_state(state):
    formatted = {}
    for item in state:
        key = item['key']
        value = item['value']
        formatted_key = base64.b64decode(key).decode('utf-8')
        if value['type'] == 1:
            # byte string
            if formatted_key != 'creator_address':
                formatted_value = base64.b64decode(value['bytes']).decode('utf-8')
                formatted[formatted_key] = formatted_value
        else:
            # integer
            formatted[formatted_key] = value['uint']
    return formatted

# helper function to read app global state
def read_global_state(client, app_id):
    app = client.application_info(app_id)
    global_state = app['params']['global-state'] if "global-state" in app['params'] else []
    return format_state(global_state)

def read_local_state(client, addr, app_id) :   
    results = client.account_info(addr)
    local_state = results['apps-local-state']
    for index in local_state :
        if index['id'] == app_id :
            return(format_state(index['key-value']))

# create new application
def create_app(client, private_key, approval_program, clear_program, global_schema, local_schema, args):

    # define sender as creator
    sender = account.address_from_private_key(private_key)

    # declare on_complete as NoOp
    on_complete = transaction.OnComplete.NoOpOC.real

    # get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    txn = transaction.ApplicationCreateTxn(sender, params, on_complete, \
                                            approval_program, clear_program, \
                                            global_schema, local_schema, args)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # wait for confirmation
    try:
        transaction_response = transaction.wait_for_confirmation(client, tx_id, 5)
        print("TXID: ", tx_id)
        print("Result confirmed in round: {}".format(transaction_response['confirmed-round']))
    except Exception as err:
        print(err)
        return

    # display results
    transaction_response = client.pending_transaction_info(tx_id)
    app_id = transaction_response['application-index']
    print("Created new app-id:", app_id)

    return app_id


# call application
def call_app(client, private_key, index, app_args):

    # declare sender
    sender = account.address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    txn = transaction.ApplicationNoOpTxn(sender, params, index, app_args)
    
    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])

    # wait for confirmation
    try:
        transaction_response = transaction.wait_for_confirmation(client, tx_id, 4)
        print("TXID: ", tx_id)
        print("Result confirmed in round: {}".format(transaction_response['confirmed-round']))
    except Exception as err:
        print(err)
    print("Application called")

    return

# call group transactions
def call_group(client, private_key, index, app_args, receiver):

    # declare sender
    sender = account.address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    app_txn = transaction.ApplicationNoOpTxn(sender, params, index, app_args)

    params = client.suggested_params()
    # comment out the next two (2) lines to use suggested fees
    params.flat_fee = True
    params.fee = constants.MIN_TXN_FEE
    pay_txn = transaction.PaymentTxn(sender, params, receiver, app_args[1])

    # group transactions
    gid = transaction.calculate_group_id([pay_txn, app_txn])                                                                
    pay_txn.group = gid
    app_txn.group = gid     

    #sign both
    stxn_1 = pay_txn.sign(private_key)    
    stxn_2 = app_txn.sign(private_key)
    signed_group =  [stxn_1, stxn_2]

    # send group of signed transactions
    tx_id = client.send_transactions(signed_group)

    # wait for confirmation
    try:
        transaction_response = transaction.wait_for_confirmation(client, tx_id, 4)
        print("TXID: ", tx_id)
        print("Result confirmed in round: {}".format(transaction_response['confirmed-round']))
    except Exception as err:
        print(err)
    
    print("Application called")
    return


# optin application
def optin_app(client, private_key, index) :
    # declare sender
    sender = account.address_from_private_key(private_key)

    # get node suggested parameters
    params = client.suggested_params()

    # create unsigned transaction
    txn = transaction.ApplicationOptInTxn(sender, params, index)

    # sign transaction
    signed_txn = txn.sign(private_key)
    tx_id = signed_txn.transaction.get_txid()

    # send transaction
    client.send_transactions([signed_txn])


    # wait for confirmation
    try:
        transaction_response = transaction.wait_for_confirmation(client, tx_id, 4)
        print("TXID: ", tx_id)
        print("Result confirmed in round: {}".format(transaction_response['confirmed-round']))

    except Exception as err:
        print(err)
        #return 1
    print("Application called")
    return 0

def main() :
    # initialize an algodClient
    algod_client = algod.AlgodClient(algod_token, algod_address)

    # define private keys
    creator_private_key = get_private_key_from_mnemonic(creator_mnemonic)
    funder_private_key = get_private_key_from_mnemonic(funder_mnemonic)

    # declare application state storage (immutable)
    local_ints = 1
    local_bytes = 0
    global_ints = 6
    global_bytes = 4
    global_schema = transaction.StateSchema(global_ints, global_bytes)
    local_schema = transaction.StateSchema(local_ints, local_bytes)

    # compile program to TEAL assembly
    with open('cfunding_approval.teal', "r") as fa:
        approval_prog = fa.read()

    with open('cfunding_clear.teal', "r") as fc:
        clear_prog = fc.read()

    # compile program to binary
    approval_program_compiled = compile_program(algod_client, approval_prog)

    # compile program to binary
    clear_state_program_compiled = compile_program(algod_client, clear_prog)

    proj_name = "Project 1"
    image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcQFAtAMxFYtyFdxi2RqchdS490OLjI3mZIQMg&usqp=CAU"

    
    #start_date = "21 June 2022"
    #start_int = int(time.strptime(start_date, "%d %B %Y"))

    #end_date = "28 June 2022"
    #end_int = int(time.strptime(end_date, "%d %B %Y"))

    start_int = int(time()) + 5              #small timing to try it
    end_int = int(time()) + (30)

    goal = 10000000
    description = "description"

    args = [proj_name, image_url, start_int, end_int, goal, description]


    print("--------------------------------------------")
    print("Deploying crowdfund application......")

    # create new application
    app_id = create_app(algod_client, creator_private_key, approval_program_compiled, clear_state_program_compiled, global_schema, local_schema, args)

    # read global state of application (debugging)
    #print("Global state:", read_global_state(algod_client, app_id))

    app_address = e.encode_address(e.checksum(b'appID'+(app_id).to_bytes(8, 'big')))
    print("This is the app n. " + str(app_id) + " address: " + app_address)

    print("--------------------------------------------")

    input("Press Enter to optin")
        
    print("Opting in")

    optin_app(algod_client, funder_private_key, app_id)

    print("Local state after optin: ", read_local_state(algod_client, account.address_from_private_key(funder_private_key), app_id))
    
    print("--------------------------------------------")

    input("Press Enter to fund the project")

    print("Funding")

    amount = 2000000
    app_args = ["Fund", amount]

    call_group(algod_client, funder_private_key, app_id, app_args, app_address)
    
    print("Local state after funding ", amount , " mAlgos: ", read_local_state(algod_client, account.address_from_private_key(funder_private_key), app_id))
    print("Global state:", read_global_state(algod_client, app_id))

    print("--------------------------------------------")

    input("Press Enter to retrieve funds")


    print("Retrieving funds")

    app_args = ["Retrieve funds"]
    call_app(algod_client, creator_private_key, app_id, app_args)

    print("Global state:", read_global_state(algod_client, app_id))

    print("Retrieved all the funds and closed the project.")

    # read global state of application
    #print("Global state:", read_global_state(algod_client, app_id))

main()