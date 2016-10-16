import json
import hvac
import requests.exceptions
import argparse
import logging
from logging.config import fileConfig
from packages.VaultServer import VaultServer

wrapped = None
auth = None
vault = None
fileConfig('logging_config.ini')
logging.basicConfig(
    filename='vault-demo.log',
    level=logging.INFO,
    format='%(asctime)s %(message)s'
)

parser = argparse.ArgumentParser(description='Process optional tokens')
parser.add_argument(
    '--wrapped-token',
    dest='wrapped_token',
    default=None,
    help='Pass the Vault wrapped authentication token via the command line.'
)
parser.add_argument(
    '--auth-file',
    dest='auth_file',
    default=None,
    help='Pass the filename of a JSON file containing authentication tokens (wrapped or unwrapped).'
)
parser.add_argument(
    '--server',
    dest='server',
    required=True,
    default=None,
    help='Pass the Vault server name (or FQDN).'
)
parser.add_argument(
    '--port',
    dest='port',
    default=8200,
    help='Pass the Vault server port number (default 8200)'
)
args = parser.parse_args()
_wrapped = args.wrapped_token
_server = args.server
_port = args.port
_auth_file = args.auth_file

# Check if a port number has been passed as a parameter
if _port is not None:
    _success = False
    try:
        _port = int(_port)
        _success = True
    except:
        _success = False

    if not _success:
        _error_text = 'ERROR: app.py: _port: ' + \
            'Port number, if provided, must be an integer. '+ \
            '{0} is not an int'.format(_port)

        logging.error(_error_text)
        raise ValueError(_error_text)

    if _port < 1:
        raise ValueError('Port number, if provided, must be greater than zero or None.')

# Check if an auth file has been passed and that it exists
if _auth_file is not None:
    if not isinstance(_auth_file, str):
        raise ValueError('Auth file, if provided, must be a filename (i.e. a string).')
    _auth_file_handle = None
    _success = False
    try:
        _auth_file_handle = open(_auth_file, 'r')
        _success = True
    except:
        _success = False

    if not _success:
        fnf_error = FileNotFoundError(
            '{0} was not found - is the spelling correct?'.format(_auth_file)
        )
        logging.error('ERROR: authentication_file: {0}'.format(str(fnf_error)))
        raise fnf_error
    t_auth = json.load(_auth_file_handle)
    _auth_file_handle.close()

    _wrapped = t_auth.get('wrapped-token', None)
    if _wrapped is None:
        _error_text = 'ERROR: authentication_file: ' + \
            'Authentication file did not contain a wrap token. ' + \
            'Key MUST be "wrapped-token":{value}'

        logging.error(_error_text)
        raise ValueError(_error_text)

vault = VaultServer(name=_server, port=_port)

try:
    vault.authenticate(wrapped_token=_wrapped)
except requests.ConnectionError as ce:
    logging.error('A connection error occurred; is the vault server information correct?')
    raise
except hvac.exceptions.Forbidden:
    logging.error('** SECURITY LOG ** The authentication request was forbidden.')
    raise
except Exception as e:
    logging.error('Exception! {0}'.format(repr(e)))
    raise

try:
    foo = vault.read_kv_secret(secret='foo')
    print('foo: {0}'.format(foo))
except ValueError as ve:
    logging.error(ve)
    raise
except hvac.exceptions.Forbidden as f:
    _error_text = 'ERROR: app.py: foo: ' + \
        'Unable to read secret. '+ \
        'Token {0} returns permission denied!'.format(
                vault.accessor if vault.accessor is not None else 'is null, so'
        )
    logging.error(_error_text)
    raise
