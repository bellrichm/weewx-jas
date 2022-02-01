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

VERSION = "0.2.1"

EXTENSION_CONFIG = """
[StdReport]
    [[jas]]
        skin = jas
        HTML_ROOT = jas
        enable = true 
        [[[Extras]]]
            # display_aeris_observation = True

            # The client id abd secret for Aeris APIs
            client_id = REPLACE_ME
            client_secret = REPLACE_ME        

            # Create an additional chart.
            [[[[charts]]]]
                [[[[[inTemp]]]]]
                    [[[[[[chart]]]]]]
                        type = "'line'"            
                    [[[[[[dataLabels]]]]]]
                        enabled = false
                    [[[[[[series]]]]]]
                        [[[[[[[inTemp]]]]]]]

            # The '$current' value of these observations will be displayed.
            [[[[current]]]]
                observation = outTemp
                [[[[[observations]]]]]
                    [[[[[[heatindex]]]]]]
                    [[[[[[windchill]]]]]]
                    [[[[[[dewpoint]]]]]]
                    [[[[[[outHumidity]]]]]]
                    [[[[[[barometer]]]]]]
                        suffix = ($trend.barometer.formatted)
                    [[[[[[windSpeed]]]]]]
                        suffix = $current.windDir.ordinal_compass ($current.windDir)
                    [[[[[[rainRate]]]]]]
                    [[[[[[rain]]]]]]
                        type = sum
            
            # The minimum and maximum values of these observations will be displayed. 
            [[[[minmax]]]]
                [[[[[observations]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[heatindex]]]]]]
                    [[[[[[windchill]]]]]]
                    [[[[[[dewpoint]]]]]]
                    [[[[[[outHumidity]]]]]]
                    [[[[[[barometer]]]]]]
            
            # For the selected date, values of these observations will be displayed.
            [[[[thisdate]]]]
                [[[[[observations]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]
                        type = avg                    
                    [[[[[[rain]]]]]]
                        type = sum

            # The pages and the content on the pages to display.
            [[[[pages]]]]
                [[[[[index]]]]]
                    [[[[[[observations]]]]]]
                    [[[[[[minmax]]]]]]
                    [[[[[[forecast]]]]]]
                        layout = row                                             
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]  
                    [[[[[[outHumidity]]]]]]  
                    [[[[[[wind]]]]]]  
                    [[[[[[rain]]]]]]                      
                    [[[[[[radar]]]]]]              
                [[[[[last7days]]]]]
                    [[[[[[minmax]]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]  
                    [[[[[[outHumidity]]]]]]  
                    [[[[[[wind]]]]]]  
                    [[[[[[rain]]]]]]                                           
                [[[[[last31days]]]]]
                    zoomControl = True
                    [[[[[[minmax]]]]]]
                    [[[[[[thisdate]]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]  
                    [[[[[[outHumidity]]]]]]  
                    [[[[[[wind]]]]]]  
                    [[[[[[rain]]]]]]                                      
                [[[[[last366days]]]]]   
                    zoomControl = True   
                    [[[[[[minmax]]]]]]       
                    [[[[[[thisdate]]]]]]                        
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]  
                    [[[[[[outHumidity]]]]]]  
                    [[[[[[wind]]]]]]  
                    [[[[[[rain]]]]]]                        
               [[[[[archive-month]]]]]
                    in_navbar = false
                    zoomControl = True
                    [[[[[[minmax]]]]]]
                    [[[[[[thisdate]]]]]]                        
                    [[[[[[outTempMinMax]]]]]]    
                    [[[[[[rain]]]]]]      
                [[[[[archive-year]]]]]   
                    in_navbar = false
                    zoomControl = True
                    [[[[[[minmax]]]]]]
                    [[[[[[outTempMinMax]]]]]]
                    [[[[[[rain]]]]]]     
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
                   ('skins/jas', ['skins/jas/day.html.tmpl',
                                  'skins/jas/forecast.inc',
                                  'skins/jas/index.html.tmpl',
                                  'skins/jas/last7days.html.tmpl',
                                  'skins/jas/last24hours.html.tmpl',
                                  'skins/jas/last31days.html.tmpl',
                                  'skins/jas/last366days.html.tmpl',
                                  'skins/jas/minmax.inc',
                                  'skins/jas/month.html.tmpl',
                                  'skins/jas/observations.inc',
                                  'skins/jas/radar.inc',
                                  'skins/jas/reload.inc',
                                  'skins/jas/skin.conf',
                                  'skins/jas/thisdate.inc',
                                  'skins/jas/week.html.tmpl',
                                  'skins/jas/year.html.tmpl',
                                  'skins/jas/yesterday.html.tmpl',
                                  'skins/jas/zoomControl.inc',
                                  'skins/jas/%Y.html.tmpl',
                                  'skins/jas/%Y-%m.html.tmpl'
                                  ]),
                   ('skins/jas/charts', ['skins/jas/charts/day.js.tmpl',
                                         'skins/jas/charts/index.js.tmpl',
                                         'skins/jas/charts/last7day.js.tmpl',
                                         'skins/jas/charts/last24hours.js.tmpl',
                                         'skins/jas/charts/last31days.js.tmpl',
                                         'skins/jas/charts/last366days.js.tmpl',
                                         'skins/jas/charts/month.js.tmpl',
                                         'skins/jas/charts/week.js.tmpl',
                                         'skins/jas/charts/year.js.tmpl',
                                         'skins/jas/charts/yesterday.js.tmpl',
                                         'skins/jas/charts/%Y.js.tmpl',
                                         'skins/jas/charts/%Y-%m.js.tmpl'
                                         ]),
                   ('skins/jas/data', ['skins/jas/data/alltime.js.tmpl',
                                       'skins/jas/data/day.js.tmpl',
                                       'skins/jas/data/last7days.js.tmpl',
                                       'skins/jas/data/last24hours.js.tmpl',
                                       'skins/jas/data/last31days.js.tmpl',
                                       'skins/jas/data/last366days.js.tmpl',
                                       'skins/jas/data/month.js.tmpl',
                                       'skins/jas/data/week.js.tmpl',
                                       'skins/jas/data/year.js.tmpl',
                                       'skins/jas/data/yesterday.js.tmpl',
                                       'skins/jas/data/year%Y.js.tmpl',
                                       'skins/jas/data/month%Y%m.js.tmpl'
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
