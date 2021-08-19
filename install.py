#    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
#    See the file LICENSE.txt for your rights.

""" Installer for the jas skin. """
try:
    # Python 2
    from StringIO import StringIO
except ImportError:
    # Python 3
    from io import StringIO

import configobj
from weecfg.extension import ExtensionInstaller

VERSION = "0.1.0-rc01"

EXTENSION_CONFIG = """
[StdReport]
    [[jas]]
        skin = jas
        HTML_ROOT = jas
        enable = true 
        [[[Extras]]]
            # display_aeris_observation = True
            #index_page_interval = last24hours

            # The client id abd secret for Aeris APIs
            client_id = REPLACE_ME
            client_secret = REPLACE_ME        

            # Additional charts
            [[[[charts]]]]
                [[[[[inTemp]]]]]
                    [[[[[[chart]]]]]]
                        type = "'line'"            
                    [[[[[[dataLabels]]]]]]
                        enabled = false
                    [[[[[[xaxis]]]]]]
                        type = "'datetime'"
                        [[[[[[[labels]]]]]]]
                            formatter = "function(val, timestamp) {return moment.unix(timestamp/1000).format('MM/DD hh:mm');}"
                    [[[[[[tooltip]]]]]]
                        [[[[[[[x]]]]]]]
                            formatter = "function(timestamp) {return moment.unix(timestamp/1000).format('hh:mm');}"   
                    [[[[[[series]]]]]]
                        [[[[[[[inTemp]]]]]]]

            # The pages to display
            [[[[pages]]]]
                [[[[[index]]]]]
                    #[[[[[[observations]]]]]]
                    [[[[[[avgMax]]]]]]
                    [[[[[[windRange]]]]]]
                    [[[[[[outTemp]]]]]]
                        layout = grid
                    [[[[[[barometer]]]]]]
                    #[[[[[[forecast]]]]]]
                    #    layout = row
                    [[[[[[rain]]]]]]
                    [[[[[[radar]]]]]]
                    [[[[[[inTemp]]]]]]
                [[[[[week]]]]]
                    [[[[[[outTemp]]]]]]
                [[[[[month]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]
                [[[[[year]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[rain]]]]]]
                [[[[[yesterday]]]]]
                    [[[[[[outTemp]]]]]]

"""

EXTENSION_DICT = configobj.ConfigObj(StringIO(EXTENSION_CONFIG))

def loader():
    """ Load and return the extension installer. """
    return JASInstaller()

class JASInstaller(ExtensionInstaller):
    """ The extension installer. """

    def __init__(self):
        super(JASInstaller, self).__init__(
            version=VERSION,
            name='jas',
            description='Interactive charts using ApexCharts and Bootstrap.',
            author="Rich Bell",
            author_email="bellrichm@gmail.com",
            config=EXTENSION_DICT,
            files=[('bin/user', ['bin/user/jas.py']),
                   ('skins/jas', ['skins/jas/forecast.inc',
                                  'skins/jas/index.html.tmpl',
                                  'skins/jas/month.html.tmpl',
                                  'skins/jas/observations.inc',
                                  'skins/jasdar.inc',
                                  'skins/jas/skin.conf',
                                  'skins/jas/week.html.tmpl',
                                  'skins/jas/year.html.tmpl'
                                  ]),
                   ('skins/jas/charts', ['skins/jas/charts/daycharts.js.tmpl',
                                         'skins/jasarts/monthcharts.js.tmpl',
                                         'skins/jas/charts/weekcharts.js.tmpl',
                                         'skins/jas/charts/yearcharts.js.tmpl'
                                         ]),
                   ('skins/jas/data', ['skins/jas/data/day-data.js.tmpl',
                                       'skins/jas/data/month-data.js.tmpl',
                                       'skins/jas/data/week-data.js.tmpl',
                                       'skins/jas/data/year-data.js.tmpl'
                                      ]),
                   ('skins/jas/generators', ['skins/jas/generators/navbar.gen',
                                             'skins/jas/generators/pages.gen'
                                            ]),
                   ('skins/jas/javascript', ['skins/jas/javascript/mqtt.js']),
                   ('skins/jas/lang', ['skins/jas/lang/en.conf']),
                   ('skins/jas/weather-icons/css', ['skins/jas/weather-icons/css/weather-icons.min.css',
                                                   'skins/jas/weather-icons/css/weather-icons-wind.min.css'
                                                     ]),
                   ('skins/jas/weather-icons/font', ['skins/jas/weather-icons/font/weathericons-regular-webfont.eot',
                                                    'skins/jas/weather-icons/font/weathericons-regular-webfont.svg',
                                                    'skins/jas/weather-icons/font/weathericons-regular-webfont.ttf',
                                                    'skins/jas/weather-icons/font/weathericons-regular-webfont.woff',
                                                    'skins/jas/weather-icons/font/weathericons-regular-webfont.woff2'
                                                   ])
                   ]
        )
