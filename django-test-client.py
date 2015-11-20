# import from 21 Bitcoin Library
from two1.commands.config import Config
from two1.lib.wallet import Wallet
from two1.lib.bitrequests import BitTransferRequests

wallet = Wallet()
username = Config().username
requests = BitTransferRequests(wallet, username)

# request the bitcoin-enabled endpoint you're hosting on the 21 Bitcoin Computer
def testendpoint():
    response = requests.get(url='http://localhost:12000/')
    print(response.text)

# make the function available at the command line
if __name__ == '__main__':
    testendpoint()
