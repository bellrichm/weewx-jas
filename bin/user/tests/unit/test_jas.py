#    Copyright (c) 2025 Rich Bell <bellrichm@gmail.com>
#
#    See the file LICENSE.txt for your full rights.
#

import configobj
import logging

import unittest
import mock

import user.jas

class TestConfiguration(unittest.TestCase):
    def test_enable_is_false(self):
        print("start")

        config_dict = {
            'StdReport': {
                'jas': {
                    'enable': False
                }
            }
        }
        config = configobj.ConfigObj(config_dict)

        mock_generator = mock.Mock()
        mock_generator.skin_dict = config

        with self.assertRaises(AttributeError) as error:
            user.jas.JAS(mock_generator)

        self.assertEqual(error.exception.args[0], "'lang' setting is required.")

        print("end")

if __name__ == '__main__':
    test_suite = unittest.TestSuite()                                                    # noqa: E265
    test_suite.addTest(TestConfiguration('test_enable_is_false'))  # noqa: E265
    unittest.TextTestRunner().run(test_suite)                                            # noqa: E265

    #unittest.main(exit=False)                                                           # noqa: E265
