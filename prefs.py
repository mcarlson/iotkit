# utilities for persisting preferences to storage
# version 1.0.0
import json

DEBUG = 0
prefs = {}

def _read():
    """Reads preferences from storage
    Private method
    """
    global prefs
    temp = ""
    with open('prefs.json','r') as f:
        temp = f.read()
    f.close()
    prefs = json.loads(temp)
    if DEBUG:
        print('read prefs from disk', prefs)
    

_saved = ""
def _write():
    """Writes preferences to storage
    Private method
    """
    global _saved
    new = json.dumps(prefs)
    if new == _saved:
        return
    with open('prefs.json','w+') as f:
        f.write(new)
    f.close()
    _saved = new
    if DEBUG:
        print('wrote prefs to disk', prefs)
    

def set(name, value, save=True):
    """Sets a preference, saving it to storage by default.
    Args:
        name: name of the preference
        value: value to set
        save: whether to save the preference immediately or not
    """
    if name in prefs and prefs[name] == value:
        return value
    prefs[name] = value
    if DEBUG:
        print('Set pref', name, "=", value)
    if save:
        _write()
    return value



def get(name, default):
    """Gets a single preference
    Args:
        name: name of the preference
        default: default value for the preference if missing
    """
    try:
        value = prefs[name]
        if DEBUG:
            print("Get pref", name, "=", value)
        return value
    except:
        prefs[name] = default
        if DEBUG:
            print("Get pref", name, "set default", default)
        return prefs[name]


def getAll():
    """Gets all preferences
    Returns:
        Copy of the preferences dictionary
    """
    if DEBUG:
        print("Get all prefs", prefs)
    return prefs.copy()


def setAll(newprefs):
    """Sets all preferences, writing to storage immediately
    Args:
        newprefs: dictionary of preferences to store
    """
    global prefs
    prefs = newprefs
    _write()
    if DEBUG:
        print("Set all prefs", prefs)


try:
    _read()
except:
    # prefs missing, write defaults
    _write()