#!/usr/bin/python3

import decimal
import getpass
import logging
import logging.handlers
import os
import traceback
import json
import pprint
import sys

import click
from mnemonic import Mnemonic
from jsonrpcclient.exceptions import ReceivedErrorResponse
from path import Path
from two1.lib.bitrequests import BitTransferRequests
from two1.lib.blockchain.chain_provider import ChainProvider
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.wallet.account_types import account_types
from two1.lib.wallet.base_wallet import convert_to_btc
from two1.lib.wallet.base_wallet import convert_to_satoshis
from two1.lib.wallet.base_wallet import satoshi_to_btc
from two1.lib.wallet import exceptions
from two1.lib.wallet.two1_wallet import Two1Wallet
from two1.lib.wallet.two1_wallet import Wallet
from two1.lib.wallet.daemonizer import get_daemonizer
from two1.commands.config import Config


HASHCLI_VERSION = "0.0.1"
DEFAULT_ENDPOINT = "http://127.0.0.1:8000/"
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
REQUIRED_DATA_PROVIDER_PARAMS = {'chain': ['chain_api_key_id', 'chain_api_key_secret'],
                                 'twentyone': []}

wallet = Wallet()
username = Config().username
requests = BitTransferRequests(wallet, username)
logger = logging.getLogger('hashcli')

pp = pprint.PrettyPrinter(indent=2, width=77)


def handle_exceptions(f, custom_msg=""):
    """ Decorator for handling exceptions

    Args:
        f (function): The function to decorate. This assumes that f
            is a click wrapper function which will be passed a context
            object as its first argument.

    Returns:
        function: A wrapper function that handles exceptions in f.
    """
    def wrapper(*args, **kwargs):
        try:
            rv = f(*args, **kwargs)
        except Exception as e:
            if hasattr(e, 'message'):
                if e.message == "Timed out waiting for lock":
                    msg = e.message + ". Please try again."
            else:
                tb = e.__traceback__
                if custom_msg:
                    msg = "%s: %s" % (custom_msg, e)
                else:
                    msg = str(e)
            logger.error(msg)
            logger.debug("".join(traceback.format_tb(tb)))
            if not logger.hasHandlers():
                click.echo(msg)

            args[0].exit(code=1)

        return rv

    return wrapper


def log_usage(f):
    """ Decorator for logging function usage

    Args:
        f (function): The function to be logged

    Returns:
        function: A wrapper function that logs usage information
    """
    def wrapper(*args, **kwargs):
        logger.info("%s(args=%r, kwargs=%r)" % (f.__name__, args[1:], kwargs))
        return f(*args, **kwargs)

    return wrapper


def get_passphrase():
    """ Prompts the user for a passphrase.

    Returns:
        str: The user-entered passphrase.
    """
    return getpass.getpass("Passphrase to unlock wallet: ")


@click.pass_context
def validate_data_provider(ctx, param, value):
    """ Validates the data provider sent in via the CLI.

    Args:
        ctx (Click context): Click context object.
        param (str): Parameter that is being validated.
        value (str): Parameter value.
    """
    data_provider_params = {}
    if ctx.obj is None:
        ctx.obj = {}

    if value not in REQUIRED_DATA_PROVIDER_PARAMS:
        ctx.fail("Unknown data provider %s" % value)

    required = REQUIRED_DATA_PROVIDER_PARAMS[value]

    fail = False
    for r in required:
        if r not in ctx.params:
            s = r.replace('_', '-')
            click.echo("--%s is required to use %s." % (s, value))
            fail = True
        else:
            data_provider_params[r] = ctx.params[r]

    if fail:
        ctx.fail("One or more required arguments are missing.")

    dp = None
    if value == 'chain':
        key = ctx.params['chain_api_key_id']
        secret = ctx.params['chain_api_key_secret']

        # validate key and secret for chain data provider
        if len(key) != 32 or len(secret) != 32 or \
           not key.isalnum() or not secret.isalnum():
            ctx.fail("Invalid chain_api_key_id or chain_api_key_secret")

        dp = ChainProvider(api_key_id=key, api_key_secret=secret)
    elif value == 'twentyone':
        dp = TwentyOneProvider()

    ctx.obj['data_provider'] = dp
    ctx.obj['data_provider_params'] = data_provider_params


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--endpoint', '-e',
              default=DEFAULT_ENDPOINT,
              metavar='STRING',
              show_default=True,
              help='API endpoint URI')
@click.option('--debug', '-d',
              is_flag=True,
              help='Turns on debugging messages.')
@click.version_option(HASHCLI_VERSION)
@click.pass_context
def main(ctx, endpoint, debug):
    """ Command-line Interface for the Two1 Wallet
    """

    # Initialize some logging handlers
    ch = logging.StreamHandler()
    ch_formatter = logging.Formatter(
        '%(levelname)s: %(message)s')
    ch.setFormatter(ch_formatter)

    logger.addHandler(ch)

    ch.setLevel(logging.DEBUG if debug else logging.WARNING)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)

    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj['endpoint'] = endpoint


@click.command(name='info')
@click.pass_context
@handle_exceptions
@log_usage
def cmd_info(ctx):
    response = requests.get(url=ctx.obj['endpoint'])
    json_val = json.loads(response.text)
    pp.pprint(json_val)

@click.command(name='get')
@click.argument('hash')
@click.pass_context
@handle_exceptions
@log_usage
def cmd_get(ctx, hash):
    if len(hash) != 64:
        ctx.fail("Invalid hash length for string " + hash)

    hash_url = "%shashfs/1/get/%s" % (ctx.obj['endpoint'], hash)
    response = requests.get(url=hash_url)

    sys.stdout.write(response.text)

main.add_command(cmd_get)
main.add_command(cmd_info)

if __name__ == "__main__":
    main()

