from jinja2 import Template, Environment, FileSystemLoader
from helpers.config_parse import write_config
from helpers.xdg import XDG_CONFIG_HOME, XDG_DATA_HOME
from main import load_config
import os

from helpers.logger import setup_logger
logger = setup_logger(__name__, "info")

DEFAULT_VDIRSYNCER_BINARY = '/usr/bin/vdirsyncer'
DEFAULT_VDIRSYNCER_CONFIG_FILE = os.path.join(XDG_CONFIG_HOME,
                                              'vdirsyncer',
                                              'zp_config')
#DEFAULT_VDIRSYNCER_STORAGE_DIRECTORY = os.path.join(XDG_DATA_HOME, 'vdirsyncer')
DEFAULT_VDIRSYNCER_STORAGE_DIRECTORY = os.path.join('/tmp', 'vdirsyncer')

def vdirsyncer_sync(vdirsyncer_pair):
    return vdirsyncer_execute(['sync', vdirsyncer_pair])

def vdirsyncer_discover(vdirsyncer_pair):
    return vdirsyncer_execute(['discover', vdirsyncer_pair])

def vdirsyncer_execute(vdirsyncer_args):
    zp_config = load_config()[0]
    zp_vdirsyncer_config = zp_config.get('vdirsyncer', {})
    vdirsyncer_binary = zp_vdirsyncer_config.get(
        'binary', DEFAULT_VDIRSYNCER_BINARY
    )
    vdirsyncer_config_file = zp_vdirsyncer_config.get(
        'config_file', DEFAULT_VDIRSYNCER_CONFIG_FILE
    )

    vdirsyncer_command = "{} -c {}".format(vdirsyncer_binary,
                                           vdirsyncer_config_file)
    vdirsyncer_command += ' ' + ' '.join(vdirsyncer_args)

    logger.info("External binary call: {}".format(vdirsyncer_command))
    return os.system(vdirsyncer_command)

# TODO: add support for multiple remotes
def vdirsyncer_set_carddav_remote(url, username, password):
    zp_config, zp_config_path = load_config()
    zp_vdirsyncer_config = zp_config.get('vdirsyncer', {})
    contacts_storage_directory = vdirsyncer_get_storage_directory_for('contacts')

    zp_vdirsyncer_config['contacts'] = {
        'pair': {
            'a': 'contacts_local',
            'b': 'contacts_remote',
            'collections': 'null'
        },
        'local': {
            'type': 'filesystem',
            'path': contacts_storage_directory, 
            'fileext': '.vcf'
        },
        'remote': {
            'type': 'carddav',
            'url': url,
            'username': username,
            'password': password
        }
    }

    zp_config['vdirsyncer'] = zp_vdirsyncer_config
    return write_config(zp_config, zp_config_path)

def vdirsyncer_get_storage_directory_for(pair):
    zp_config = load_config()[0]
    zp_vdirsyncer_config = zp_config.get('vdirsyncer', {})
    vdirsyncer_storage_directory = zp_vdirsyncer_config.get(
        'storage_directory', DEFAULT_VDIRSYNCER_STORAGE_DIRECTORY
    )

    directory = os.path.join(vdirsyncer_storage_directory, pair)

    # Create the directory ourself so that vdirsyncer does not ask stdin!
    if not os.path.exists(directory):
        os.makedirs(directory)

    return directory

# TODO: similar to vdirsyncer_set_carddav_remote
def vdirsyncer_set_calddav_remote():
    return

def vdirsyncer_generate_config():
    zp_config = load_config()[0]
    zp_vdirsyncer_config = zp_config.get('vdirsyncer', {})
    status_directory = vdirsyncer_get_storage_directory_for('_vdirsyncer_status')

    logger.info('Generating vdirsyncer configuration')

    jinja2_env = Environment(loader=FileSystemLoader('helpers/vdirsyncer'),
                             trim_blocks=True)
    template = jinja2_env.get_template('config.j2')
    rendered_vdirsyncer_config = template.render(
        contacts=zp_vdirsyncer_config['contacts'],
        status_directory=status_directory
    )

    vdirsyncer_config_file = zp_vdirsyncer_config.get(
        'config_file', DEFAULT_VDIRSYNCER_CONFIG_FILE
    )

    logger.info('Writing vdirsyncer configuration')
    with open(vdirsyncer_config_file, 'w') as fh:
        fh.write(rendered_vdirsyncer_config)
        fh.close
