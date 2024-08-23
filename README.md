# 4chan and Reddit

This toolbox can be used to juggle 4chan and reddit data. It was developed to run frequency analysis of markers indication situational definition on 4chan and Reddit. 
However, it should be flexible enough to be used to run any kind of frequency analysis on 4chan and Reddit archive data.

## Usage

To use one of the following instructions:

### The Lazy Way

> Note: This was not tested extensively, especially not on multiple operating systems. So, if it works: GREAT! If not, try the Python way (see below)...  

1. Download toolbox from latest release and place it somewhere on your computer: 

> https://github.com/josiasbruderer/4chan-and-reddit/releases/latest

2. Download the precompiled database (at least data_*) and place it on in a subdirectory relative to the just stored toolbox executable.

3. Open a command line console and change to the directory where you put the toolbox. For example:

```
cd Desktop/4chan-and-reddit
```

4. Run the application. Note: First run will create three directories. You should at least have a look at `config/markers.ods` 

```
toolbox.exe version
toolbox.exe help
#... do what you want
```

### The Python Way

1. Make sure you have Python installed: `python --version` (Hint: we tested with Python 3.12.3 on Arch Linux)
2. Create and activate virtual environment, install requirements

```bash
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```
3. Verify that everything is set up properly. This includes at least having a look at `config/default.json` and `config/markers.ods`
4. Optional: Download archive dumps to be imported. This procedure is described in `download_instructions.md`
4. Optional: Download precompiled database and put it to directory `db` 
5. Run the application:

```bash
python toolbox.py version
python toolbox.py help
#... do what you want
```

## Packaging

This toolbox and the simple_web_server can be packaged to an executable using pyinstaller:

```bash
source venv/bin/activate
pip install pyinstaller
pip install -r requirements.txt
pyinstaller -F -c -n simple_web_server_linux simple_web_server.py
pyinstaller --add-data 'config/*:config' --add-data 'scripts/*:scripts' -F -c -n toolbox_linux toolbox.py
```