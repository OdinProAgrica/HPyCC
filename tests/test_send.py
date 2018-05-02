import tests.make_data as md
import hpycc.send as send
import hpycc.run as run
from hpycc.utils.HPCCconnector import HPCCconnector

server = 'localhost'
hpcc_connection = HPCCconnector(server, '8010', None, "hpycc_get_output", '" "', False)
logical_file = '~TEMP::HPYCC::TEST::FILE'  # this needs to match the below script
source_file = 'testData.csv'

# make DF and ensure file doesn't exist.
df = md.make_csv(source_file, 15000)
run.delete_logical_file(logical_file, server)


def test_send_file_1():

    send.send_file(source_file, logical_file, 'localhost', port="8010", repo=None,
              username="hpycc_get_output", password='" "',
              legacy=False, overwrite=False, delete=True,
              silent=False, debg=False, log_to_file=False)

    file_uploaded = md.check_exists(logical_file, hpcc_connection)
    assert file_uploaded  # File contents is tested in test_sendfiles