import datetime
import os
import shutil
import sys

from packages import logger
from packages import configer
from packages import importer
from packages import analyser
from packages import webserver

VERSION = "1.0.5"
ROOT_DIR = PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))
if getattr(sys, 'frozen', False):
    ROOT_DIR = os.path.dirname(os.path.realpath(sys.executable))  # when run packaged we want path of executable instead of temporary directory
os.chdir(ROOT_DIR)

CONFIG_DIR = os.path.join(ROOT_DIR, 'config')
LOGS_DIR = os.path.join(ROOT_DIR, 'logs')
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')
LOG_FILE = os.path.join(LOGS_DIR, f'{datetime.datetime.now().strftime("%Y-%m-%d")}.log')
CONFIG_FILE = os.path.join(CONFIG_DIR, f'{sys.argv[2] if len(sys.argv) > 2 else 'default'}.json')
ACTION = sys.argv[1] if len(sys.argv) > 1 else None

if getattr(sys, 'frozen', False):
    '''Do some file copying when run as package'''
    os.makedirs(LOGS_DIR, exist_ok=True)
    if not os.path.exists(CONFIG_FILE):
        shutil.copytree(PACKAGE_DIR + '/config', CONFIG_DIR)
    if not os.path.exists(SCRIPTS_DIR):
        shutil.copytree(PACKAGE_DIR + '/scripts', SCRIPTS_DIR)

log = logger.setup(__name__, LOG_FILE, logger.DEBUG)
config = configer.setup(CONFIG_FILE)
config.set("general", "root_dir", ROOT_DIR)
config.set("general", "log_file", LOG_FILE)


def main():
    global config
    global log

    if ACTION is None:
        log.critical("Action must be provided! Use one of: import, import_images, analyse, webserver")

    if ACTION == 'version':
        print(f'App: {VERSION}')
        print(f'Python: {sys.version}')

    if "help" in ACTION:
        print('This program can be used as following. Note that ".exe" is only required on Windows.')
        print(' > toolbox.exe [ACTION] [CONFIG_FILE_PATH]')
        print('')
        print('- Parameter ACTION is required. Available actions are: help, version, import, import_images, analyse, webserver')
        print('- Parameter CONFIG_FILE_PATH is optional. Default config file path is "config/default.json".')

    if ACTION == "import":
        log.info(f'Importing data to {config.get_from_import_run_mode('db_name')}')
        importer.start(config, ACTION)

    if ACTION == "images_import":
        log.info(f'Importing 4chan thumbnails to {config.get('images_import', 'db_name')}')
        importer.start(config, ACTION)

    if ACTION == "analyse":
        log.info(f'Analysing data from {config.get_from_import_run_mode('db_name')}')
        analyser.start(config, ACTION)

    if ACTION == "webserver":
        log.info(f'Starting web server from {config.as_path(config.get('analysis', 'results_dir'))}')
        webserver.run(config.as_path(config.get('analysis', 'results_dir')))


if __name__ == '__main__':
    main()
