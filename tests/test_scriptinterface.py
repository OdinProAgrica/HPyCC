import hpycc.getscripts.scriptinterface as interface
import pandas as pd
from pandas.util.testing import assert_frame_equal

xml = """<Result>
           <Dataset name='Result 1'> 
            <Row><a>1</a><b>2</b></Row> 
            <Row><a>3</a><b>4</b></Row> 
            <Row><a>5</a><b>6</b></Row> 
            <Row><a>7</a><b>8</b></Row> 
            <Row><a>9</a><b>10</b></Row> 
            <Row><a>11</a><b>12</b></Row>
           </Dataset>
        </Result>"""

expected_result_1 = pd.DataFrame({'a': [1, 3, 5, 7, 9, 11], 'b': [2, 4, 6, 8, 10, 12]})

# TODO: this should not be an allowable input as it concateates them!
xml_2Datasets = """<Result>
           <Dataset name='Result 1'> 
            <Row><a>1</a><b>2</b></Row> 
            <Row><a>3</a><b>4</b></Row> 
            <Row><a>5</a><b>6</b></Row> 
            <Row><a>7</a><b>8</b></Row> 
            <Row><a>9</a><b>10</b></Row> 
            <Row><a>11</a><b>12</b></Row>
           </Dataset>
           <Dataset name='Result 2'> 
            <Row><a>11</a><b>12</b></Row> 
            <Row><a>13</a><b>14</b></Row> 
            <Row><a>15</a><b>16</b></Row> 
            <Row><a>17</a><b>18</b></Row> 
            <Row><a>19</a><b>110</b></Row> 
            <Row><a>111</a><b>112</b></Row>
           </Dataset>
        </Result>"""

# TODO: basically runs all other functions in scripts. Doesn't seem much point as all it does is return teh console.
# If stdout breaks it'll break get_script. if stderr breaks it'll break the syntax checker.
# def test_run_command():
#
#     assert False

def test_parse_XML():
    result = interface.parse_xml(xml, silent=False)
    print(result)
    assert_frame_equal(result, expected_result_1, check_dtype=False, check_like=False)