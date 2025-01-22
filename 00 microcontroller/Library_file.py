# Library_file.py
# 09. January 2025
# Jordon D Hemingway
# Modified from the original code by Philip Gautschi (ETH LIP)

'''
File to read and write to json files
'''

from json import dump as dump_js, load as load_js
from os import mkdir

#function to read json file
def read_file(file_name: str, path: str = ''):
    '''
    Reads json file

    Parameters
    ----------
    file_name : str
        Name of .json file to be read

    path : str
        String to get the absolute path, if not in same directory. Defaults to
        "" (blank).

    Returns
    -------
    data : dict
        Dictionary of data loaded from json file
    '''

    #try to import the data
    try:
        #make absolute path
        full_path = file_name

        with open(full_path, 'r') as outfile:
            data = load_js(outfile)

    #if data cannot be loaded, return None
    except OSError as err:
        print("ERROR, '%s': Could not load data from '%s'. (%s, OSError: %i)" %
              (read_file.__name__, full_path, err.strerror, err.errno))
        return None
    
    #otherwise raise error
    except:
        print("DEBUG, '%s': %s: '%s'." % (read_file.__name__, "", ""))
        raise

    return data

#funciton to write to json file
def write_file(data: dict, file_name: str, path: str) -> None:
    '''
    Writes data to a json file

    Parameters
    ----------
    data : dict
        Dictionary of data to write to json file

    file_name : str
        Name of file to create (without .json)

    path : str
        String to set the absolute path, if not in same directory.
    '''

    #raise some errors if needed
    try:
        pass

    # if data cannot be loaded, return None
    except OSError as err:
        print("ERROR, '%s': Could not create '%s' or check its existence. (%s, OSError: %i)" %
              (write_file.__name__, path, err.strerror, err.errno))
        return None

    #otherwise raise error
    except:
        print("DEBUG, '%s': %s: '%s'." % (read_file.__name__, "", ""))
        raise

    #now try writing data to file
    try:
        #make absolute path
        full_path = file_name + '.json'

        #write data to that file
        with open(full_path, 'w') as outfile:
            dump_js(data, outfile, indent = 4)
    
    #print a message if it can't write
    except OSError as err:
        print("ERROR, '%s': Could not write data to '%s'. (%s, OSError: %i)" %
              (write_file.__name__, full_path, err.strerror, err.errno))
    
    #otherwise raise error
    except:
        print("DEBUG, '%s': %s: '%s'." % 
            (read_file.__name__, exc_info()[0].__name__, exc_info()[1]))
        raise

    return None

