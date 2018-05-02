import os
import hpycc.scriptrunning.runscript as runscript
import hpycc.scriptrunning.getscripts as getscript
import hpycc.filerunning.sendfiles as sendfiles
import pandas as pd

overwrite = True
delete = True


def upload_large_data(hpcc_connection, start_row=0, size=25000):
    syntax_check = False

    wrapper = "a := DATASET([%s], {INTEGER a; INTEGER b}); OUTPUT(a, ,'~a::test::bigfile', EXPIRE(1), OVERWRITE);"

    some_data = list(range(start_row, size))
    backwards_data = list(reversed(some_data))

    row_string = '{%s,%s},'
    out_rows = ''
    for i, j in zip(some_data, backwards_data):
        out_rows += row_string % (i, j)
    out_rows += '{0,0}'

    script = 'ECLtest_temp.ecl'
    ecl_command = wrapper % out_rows
    with open(script, 'w') as f:
        f.writelines(ecl_command)

    some_data.append(0)
    backwards_data.append(0)
    expected_big_data = pd.DataFrame({'a': some_data, 'b': backwards_data})

    runscript.run_script_internal(script, hpcc_connection, syntax_check)
    os.remove(script)

    return expected_big_data


def make_df(size):
    half_size = round(size/2)
    int_col = list(range(0, size))

    df = pd.DataFrame({
        'intcol':  int_col,
        'floatcol': [round(x/3, 2) for x in list(range(0, size))],
        'charcol': ['Spam and ham and eggs and jam'] * size,
        'logicalcol': ([False]*half_size) + [True]*(size-half_size)
    })

    return df


def get_recordset():
    return 'string charcol; string floatcol; string intcol; string logicalcol;'


def make_csv_format_logicalfile(logicalfile, new_file, hpcc_connection, syntax_check):
    ecl_command = "a := DATASET('%s', {%s}, THOR); OUTPUT(a, , '%s', CSV(HEADING(SINGLE), QUOTE('\"')), OVERWRITE);"
    ecl_command = ecl_command % (logicalfile, get_recordset(), new_file)

    script = 'ECLtest_temp.ecl'
    with open(script, 'w') as f:
        f.writelines(ecl_command)

    runscript.run_script_internal(script, hpcc_connection, syntax_check)
    os.remove(script)


def make_csv(save_loc, size):
    df = make_df(size)
    df.to_csv(save_loc, index=False)
    return df


def upload_data(target_name, size, hpcc_connection):
    df = make_df(size)
    sendfiles.send_file_internal(df.copy(), target_name, overwrite, delete, hpcc_connection)
    return df


def check_exists(logical_file, hpcc_connection):
    ecl_command = "IMPORT std; STD.File.FileExists('%s');" % logical_file

    script = 'ECLtest_temp.ecl'
    with open(script, 'w') as f:
        f.writelines(ecl_command)

    check = getscript.get_script_internal(script, hpcc_connection, True)
    os.remove(script)

    return check[0][1].ix[0, 0].tolist()

