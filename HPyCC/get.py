import os
import logging
import sys
from hpycc.filerunning import getfiles
from hpycc.scriptrunning import getscripts

LOG_PATH = 'hpycc.log'
logger = logging.getLogger()


def boot_logger(silent, debg, log_to_file, logpath):
    # TODO: get logger in each funtion

    global logger

    if debg:
        logger.setLevel(logging.DEBUG)
    elif silent:
        logger.setLevel(logging.WARN)
    else:
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    if log_to_file:
        fh = logging.FileHandler(logpath)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


def get_output(script, server, port="8010", repo=None,
               username="hpycc_get_output", password='" "',
               legacy=False, do_syntaxcheck=True,
               silent=False, debg=False, log_to_file=False, logpath=LOG_PATH):
    """
    Return the first output of an ECL script as a DataFrame.

    Parameters
    ----------
    :param script: str
         Path of script to execute.
    :param server: str
        Ip address and port number of HPCC in the form
        XX.XX.XX.XX.
    :param port: str, optional
        Port number ECL Watch is running on. "8010" by default.
    :param repo: str, optional
        Path to the root of local ECL repository if applicable.
    :param username: str, optional
        Username to execute the ECL workunit. "hpycc_get_output" by
        default.
    :param password: str, optional
        Password to execute the ECL workunit. " " by
    default.
    :param silent: bool
        If False, the program will print out its progress. True by
        default.

    Returns
    -------
    :return: result: DataFrame
        The first output produced by the script.
    """

    boot_logger(silent, debg, log_to_file, logpath)
    logger = logging.getLogger('get_output')
    logger.debug('Starting get_script')

    parsed_data_frames = getscripts.get_script(
        script, server, port, repo,
        username, password, silent,
        legacy, do_syntaxcheck)

    logger.debug('Extracting outputs')
    try:
        first_parsed_result = parsed_data_frames[0][1]
    except IndexError:
        logger.error('Unable to parse response, printing first 500 characters: %s' % parsed_data_frames[:500])
        raise

    return first_parsed_result


def get_outputs(script, server, port="8010", repo=None,
                username="hpycc_get_output", password='" "',
                legacy=False, do_syntaxcheck=True,
                silent=False, debg=False, log_to_file=False,
                logpath=LOG_PATH):
    """
    Return all outputs of an ECL script as a dict of DataFrames.

    Parameters
    ----------
    :param script: str
         Path of script to execute.
    :param server: str
        Ip address and port number of HPCC in the form
        XX.XX.XX.XX.
    :param port: str, optional
        Port number ECL Watch is running on. "8010" by default.
    :param repo: str, optional
        Path to the root of local ECL repository if applicable.
    :param username: str, optional
        Username to execute the ECL workunit. "hpycc_get_output" by
        default.
    :param password: str, optional
        Password to execute the ECL workunit. " " by
    default.
    :param silent: bool
        If False, the program will print out its progress. True by
        default.

    Returns
    -------
    :return: as_dict: dictionary
        Outputs produced by the script in the form {output_name, df}.
    """

    boot_logger(silent, debg, log_to_file, logpath)
    logger = logging.getLogger('get_outputs')
    logger.debug('Starting get_script')

    parsed_data_frames = getscripts.get_script(
        script, server, port, repo,
        username, password, silent,
        legacy, do_syntaxcheck)

    logger.debug('Converting response to Dict')
    as_dict = dict(parsed_data_frames)

    return as_dict


def get_file(logical_file, server, port='8010',
             username = "hpycc_get_output", password = '" "',
             csv_file=False, silent=False, debg=False,
             log_to_file=False, logpath=LOG_PATH):

    """
    Main call to process an HPCC file. Advantage over scripts as it can be chunked and threaded.

    Parameters
    ----------
    logical_file: str
        logical file to be downloaded
    csv_file: bool
        IS the logical file a CSV?
    server: str
        address of the HPCC cluster
    output_path: str, optional
        Path to save to. If blank will return a dataframe. Blank by default.
    Returns
    -------
    result: pd.DataFrame
        a DF of the given file
    """

    boot_logger(silent, debg, log_to_file, logpath)
    logger = logging.getLogger('get_file')
    logger.debug('Starting get_file')

    try:
        df = getfiles.get_file(logical_file, server, port,
                               username, password, csv_file, silent)
    except KeyError:
        logger.error('Key error, have you specified a CSV or THOR file correctly?')
        raise

    return df


def save_output(script, server, path, port="8010", repo=None,
                username="hpycc_get_output", password='" "',
                compression=None, legacy=False, silent=False, debg=False,
                log_to_file=False, logpath=LOG_PATH):
    """
    Save the first output of an ECL script as a csv.

    Parameters
    ----------
    :param path: str
        Path of target destination.
    :param script: str
         Path of script to execute.
    :param server: str
        Ip address and port number of HPCC in the form
        XX.XX.XX.XX.
    :param port: str, optional
        Port number ECL Watch is running on. "8010" by default.
    :param repo: str, optional
        Path to the root of local ECL repository if applicable.
    :param username: str, optional
        Username to execute the ECL workunit. "hpycc_get_output" by
        default.
    :param password: str, optional
        Password to execute the ECL workunit. " " by
    default.
    :param silent: bool
        If False, the program will print out its progress. True by
        default.
    :param compression: str, optional
        Compression format to give to pandas. None by default.

    Returns
    -------
    :return: None
    """

    # boot_logger(silent, debg, log_to_file, logpath) # No logger as get_output boots logger

    result = get_output(script, server, port, repo, username, password, silent, legacy)
    result.to_csv(path_or_buf=path, compression=compression, index=False)
    return None


def save_outputs(
        script, server, directory=".", port="8010", repo=None,
        username="hpycc_get_output", password='" "',
        compression=None, filenames=None, prefix="", legacy=False,
        do_syntaxcheck=True, silent=False, debg=False,
        log_to_file=False, logpath=LOG_PATH):

    """
    Save all outputs of an ECL script as csvs using their output
    name. The file names can be changed using the filenames and
    prefix parameters.

    Parameters
    ----------
    :param script: str
         Path of script to execute.
    :param server: str
        Ip address and port number of HPCC in the form
        XX.XX.XX.XX.
    :param directory: str, optional
        Directory to save output files in. "." by default.
    :param port: str, optional
        Port number ECL Watch is running on. "8010" by default.
    :param repo: str, optional
        Path to the root of local ECL repository if applicable.
    :param username: str, optional
        Username to execute the ECL workunit. "hpycc_get_output" by
        default.
    :param password: str, optional
        Password to execute the ECL workunit. " " by
    default.
    :param silent: bool
        If False, the program will print out its progress. True by
        default.
    :param compression: str, optional
        Compression format to give to pandas. None by default.
    :param filenames: list, optional
        File names to save results as. If filenames is shorter than
        number of outputs, only those with a filename will be saved.
        If not specified, all files will be named their output name
        assigned by the ECL script.
    :param prefix: str, optional
        Prefix to prepend to all file names. "" by default.

    Returns
    -------
    :return: None
    """

    boot_logger(silent, debg, log_to_file, logpath)
    logger = logging.getLogger('get_outputs')
    logger.debug('Starting get_script')

    parsed_data_frames = getscripts.get_script(
        script, server, port, repo, username, password, silent, legacy, do_syntaxcheck)

    if filenames:
        if len(filenames) != len(parsed_data_frames):
            logger.warning("The number of filenames specified is different to "
                        "the number of outputs in your script. Adding names to compensate.")
        zipped = list(zip(parsed_data_frames, filenames))
    else:
        zipped = [(p, "{}.csv".format(p[0])) for p in parsed_data_frames]

    for result in zipped:
        file_name = "{}{}".format(prefix, result[1])
        path = os.path.join(directory, file_name)
        result[0][1].to_csv(path, compression=compression, index=False)

    return None


def save_file(logical_file, output_path, server, port='8010',
              username="hpycc_get_output", password='" "',
              csv_file=False, compression=None, silent=False,
              debg=False, log_to_file=False, logpath=LOG_PATH):

    """

    :param df:
    :param output_path:
    :param do_compression:
    :return:
    """

    # boot_logger(silent, debg, log_to_file, logpath) # no logger as get_file boots logger

    df = get_file(logical_file, server, port, username, password, csv_file, silent)

    df.to_csv(output_path, index=False, encoding='utf-8',
              compression=compression)


# TODO: Run function that runs a script and saves the output. Probably another class.
