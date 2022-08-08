#    Copyright (c) 2021-2022 Rich Bell <bellrichm@gmail.com>
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

VERSION = "0.2.2-rc03a"

EXTENSION_CONFIG = """
[StdReport]
    # jas (Just another Skin) is highly configurable. This is an example to get the skin up and running.
    # For more information head over to, https://github.com/bellrichm/weewx-jas/wiki/Getting-Started
    [[jas]]
        skin = jas
        HTML_ROOT = jas
        enable = true 
        [[[Extras]]]
            # display_aeris_observation = True

            # The client id abd secret for Aeris APIs
            client_id = REPLACE_ME
            client_secret = REPLACE_ME       
            
            [[[[mqtt]]]]
                enable = False
                
                host = REPLACE_ME
                port = REPLACE_ME
                
                useSSL = false
                
                username = REPLACE_ME
                password = REPLACE_ME
                
                topic = REPLACE_ME
                
            # Define an additional chart.
            # Once a chart is defined, it can be added to pages.
            # https://github.com/bellrichm/weewx-jas/wiki/Defining-New-Charts
            [[[[chart_definitions]]]]
                # The name of this chart is inTemp. It could be anything.
                [[[[[inTemp]]]]]
                    # Options that are not used by eCharts are put under 'weewx' stanzas'
                    [[[[[[weewx]]]]]]
                        title = Inside Temperature
                    [[[[[[series]]]]]]
                        # Chart one observation, inTemp
                        [[[[[[[inTemp]]]]]]]

            # The '$current' value of these observations will be displayed.
            # If MQTT is enabled, these will be updated when a message is received.
            # https://github.com/bellrichm/weewx-jas/wiki/Sections#the-current-section
            [[[[current]]]]
                # The header observation is outTemp
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
            # https://github.com/bellrichm/weewx-jas/wiki/Sections#the-minmax-section
            [[[[minmax]]]]
                [[[[[observations]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[heatindex]]]]]]
                    [[[[[[windchill]]]]]]
                    [[[[[[dewpoint]]]]]]
                    [[[[[[outHumidity]]]]]]
                    [[[[[[barometer]]]]]]
            
            # For the selected date, values of these observations will be displayed.
            # https://github.com/bellrichm/weewx-jas/wiki/Sections#the-thisdate-section
            [[[[thisdate]]]]
                [[[[[observations]]]]]
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]
                        type = avg                    
                    [[[[[[rain]]]]]]
                        type = sum

            # The pages and the content on the pages to display.
            # https://github.com/bellrichm/weewx-jas/wiki/Pages
            # https://github.com/bellrichm/weewx-jas/wiki/Predefined-Charts
            # https://github.com/bellrichm/weewx-jas/wiki/Sections
            [[[[pages]]]]
                [[[[[last24hours]]]]]
                    [[[[[[current]]]]]]
                    [[[[[[minmax]]]]]]
                    #[[[[[[forecast]]]]]]
                    #    layout = row                                             
                    [[[[[[outTemp]]]]]]
                    [[[[[[barometer]]]]]]  
                    [[[[[[outHumidity]]]]]]  
                    [[[[[[wind]]]]]]  
                    [[[[[[rain]]]]]]                      
                    #[[[[[[radar]]]]]]
                    # Here is the user defined chart, inTemp
                    [[[[[[inTemp]]]]]]             
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
                    enable = false
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
                [[[[[debug]]]]]   
                    enable = false
                    [[[[[[outTemp]]]]]]   
                        series_type = mqtt  
                    [[[[[[barometer]]]]]]                   
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
            description='Interactive charts using ECharts and Bootstrap.',
            author="Rich Bell",
            author_email="bellrichm@gmail.com",
            config=EXTENSION_DICT,
            files=[('bin/user', ['bin/user/jas.py']),
                   ('skins/jas',
                                ['skins/jas/icon/android-chrome-192x192.png',
                                  'skins/jas/icon/android-chrome-512x512.png',
                                  'skins/jas/icon/apple-touch-icon.png',
                                  'skins/jas/icon/favicon.ico',
                                  'skins/jas/icon/favicon-16x16.png',
                                  'skins/jas/icon/favicon-32x32.png'
                                ]), 
                   ('skins/jas/pages', ['skins/jas/pages/debug.html.tmpl',
                                        'skins/jas/pages/day.html.tmpl',
                                        'skins/jas/index.html.tmpl',
                                        'skins/jas/pages/last7days.html.tmpl',
                                        'skins/jas/pages/last24hours.html.tmpl',
                                        'skins/jas/pages/last31days.html.tmpl',
                                        'skins/jas/pages/last366days.html.tmpl',
                                        'skins/jas/manifest.json.tmpl',
                                        'skins/jas/pages/month.html.tmpl',
                                        'skins/jas/skin.conf',
                                        'skins/jas/pages/week.html.tmpl',
                                        'skins/jas/pages/year.html.tmpl',
                                        'skins/jas/pages/yesterday.html.tmpl',
                                        'skins/jas/pages/yeartoyear.html.tmpl',
                                        'skins/jas/pages/multiyear.html.tmpl',
                                        'skins/jas/pages/%Y.html.tmpl',
                                        'skins/jas/pages/%Y-%m.html.tmpl'
                                        ]),
                   ('skins/jas/charts', ['skins/jas/charts/day.js.tmpl',
                                         'skins/jas/charts/debug.js.tmpl',
                                         'skins/jas/charts/last7days.js.tmpl',
                                         'skins/jas/charts/last24hours.js.tmpl',
                                         'skins/jas/charts/last31days.js.tmpl',
                                         'skins/jas/charts/last366days.js.tmpl',
                                         'skins/jas/charts/month.js.tmpl',
                                         'skins/jas/charts/week.js.tmpl',
                                         'skins/jas/charts/year.js.tmpl',
                                         'skins/jas/charts/yesterday.js.tmpl',
                                         'skins/jas/charts/yeartoyear.js.tmpl',
                                         'skins/jas/charts/multiyear.js.tmpl',
                                         'skins/jas/charts/%Y.js.tmpl',
                                         'skins/jas/charts/%Y-%m.js.tmpl'
                                         ]),
                   ('skins/jas/data', ['skins/jas/data/index.js.tmpl',
                                       'skins/jas/data/forecast.js.tmpl',
                                       'skins/jas/data/debug.js.tmpl',
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
                   ('skins/jas/generators', ['skins/jas/generators/charts.gen',
                                            'skins/jas/generators/data.gen',
                                             'skins/jas/generators/js.gen',
                                             'skins/jas/generators/pages.gen',
                                             'skins/jas/generators/startEndHistorical.gen',
                                             'skins/jas/generators/startEndActive.gen'
                                            ]),
                   ('skins/jas/javascript', ['skins/jas/javascript/day.js.tmpl',
                                             'skins/jas/javascript/debug.js.tmpl',
                                             'skins/jas/javascript/index.js.tmpl',
                                             'skins/jas/javascript/last7days.js.tmpl',
                                             'skins/jas/javascript/last24hours.js.tmpl',
                                             'skins/jas/javascript/last31days.js.tmpl',
                                             'skins/jas/javascript/last366days.js.tmpl',
                                             'skins/jas/javascript/month.js.tmpl',
                                             'skins/jas/javascript/mqtt.js.tmpl',
                                             'skins/jas/javascript/week.js.tmpl',
                                             'skins/jas/javascript/year.js.tmpl',
                                             'skins/jas/javascript/yesterday.js.tmpl',
                                             'skins/jas/javascript/yeartoyear.js.tmpl',
                                             'skins/jas/javascript/multiyear.js.tmpl',
                                             'skins/jas/javascript/%Y.js.tmpl',
                                             'skins/jas/javascript/%Y-%m.js.tmpl'
                                             ]),
                   ('skins/jas/lang', ['skins/jas/lang/en.conf']),
                   ('skins/jas/sections', [
                                           'skins/jas/sections/current.inc',
                                           'skins/jas/sections/debug.inc',
                                           'skins/jas/sections/forecast.inc',
                                           'skins/jas/sections/minmax.inc',
                                           'skins/jas/sections/radar.inc',
                                           'skins/jas/sections/thisdate.inc',
                                           'skins/jas/sections/zoomControl.inc'
                                           ]),
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
