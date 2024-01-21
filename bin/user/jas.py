#    Copyright (c) 2021-2023 Rich Bell <bellrichm@gmail.com>
#    See the file LICENSE.txt for your rights.

# pylint: disable=line-too-long, too-many-lines

"""
This search list extension provides the following tags:
  aggregate_types
    Returns:
      A dictionary of all aggregate types (avg, max, min, sum, etc.) used.

  $dateTimeFormats
    Arguments:
      language: The language to get the formats.
    Returns:
      The formats.

  $forecasts
    Returns:
      A list of dictionaries containing forecastdata.
      ToDo: determine and document what forecast data is returned.

  $genCharts
    Arguments:
      page: The page to generate the charts for
      interval: The time interval to generate the chart for (day, yesterday, 2000, 200001, etc)
    Returns:
      The charts for the page.

  $languages
    The languages supported by the skin

  $last24hours
    A WeeWX timespanBinder for the last 24 hours.

  $last7days
     A WeeWX timespanBinder for the last 7 days.

  $last31days
    A WeeWX timespanBinder for the last 31 days.

  $last366days
    A WeeWX timespanBinder for the last 366 days.

  $logdbg(message)
    A method to log debug messages.

  $loginf(message)
    A method to log informational messages.

  $logerr(message)
    A method to log warning messages.

  $observations
    A dictionary of all the observations that will be charted.

  $observationLabels
    Arguments:
      language: The language to get the labels.
    Returns:
      The labels.

  $ordinateNames
    The names of the compass ordinates.

  $skinDebug
    The skin debug option.

  $textLabels
    Arguments:
      language: The language to get the labels.
    Returns:
      The labels.

  $utcOffset
    The UTC offset in minutes.

  $version
    Returns:
      The version of this skin.

  $weewx_version
    Returns:
      The version of WeeWX.

  $windCompass(start_offset, end_offset)
    Arguments:
      start_offset: The starting time offset from the current time. Default is 86400, 24 hours.
      end_offset: The ending time offset from the current time. Default is 0, 'now'.
    Returns:
      A tuple consisting of:
        average: A list of wind speed averages for the compass ordinals.
        maximum: A list of wind speed maximums for the compass ordinals.
        speed_ranges: A list of lists. Each primary list is a speed range that contains a list
          of the counts of that speed for each compass ordinal.


https://groups.google.com/g/weewx-development/c/QRHGtzpKV_4/m/lrNSWxNhAwAJ
The member function get_extension_list() will be called for each template.
So, if you have 10 templates, it will get called 10 times.
If there is an expensive calculation that does not depend on the timespan that needs to be done,
then it is best done in the initializer ('__init__') of your extension.

There are 3 runtime options for extensions:
1. The initializer. Called once per skin.
2. In  get_extension_list(). Called once per template.
3. In the extension tag. Gets called when a '$' tag matches your extension tag.

In general, you want expensive calculations to be done farther up this list.
But, if they depend on things only known farther down the list, in particular, a timespan, then you're out of luck.

"""

import copy
import datetime
import errno
import locale
import os
import platform
import sys
import time
import json

import configobj

import weewx
import weecfg
try:
    # Python 3
    from urllib.request import Request, urlopen, HTTPError # pyright: ignore reportMissingImports=false
    from urllib.error import URLError
except ImportError:
    # Python 2
    from urllib2 import Request, urlopen, HTTPError # pyright: ignore reportMissingImports=false
    from urllib2 import URLError # pyright: ignore reportMissingImports=false

from weewx.cheetahgenerator import SearchList
from weewx.reportengine import merge_lang
from weewx.units import get_label_string
from weewx.tags import TimespanBinder
from weeutil.weeutil import to_bool, to_int, to_list, TimeSpan, timestamp_to_string

try:
    import weeutil.logger # pylint: disable=unused-import
    import logging

    log = logging.getLogger(__name__) # pylint: disable=invalid-name

    def logdbg(msg):
        """ log debug messages """
        log.debug(msg)

    def loginf(msg):
        """ log informational messages """
        log.info(msg)

    def logerr(msg):
        """ log error messages """
        log.error(msg)

except ImportError:
    import syslog

    def logmsg(level, msg):
        """ log to syslog """
        syslog.syslog(level, F'jas: {msg}')

    def logdbg(msg):
        """ log debug messages """
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        """ log informational messages """
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        """ log error messages """
        logmsg(syslog.LOG_ERR, msg)


VERSION = "1.1.1-rc03"

class JAS(SearchList):
    """ Implement tags used by templates in the skin. """
    def __init__(self, generator):
        self.gen_time = int(time.time())
        SearchList.__init__(self, generator)
        self.skin_dict = generator.skin_dict

        logdbg(F"Using weewx version {weewx.__version__}")
        logdbg(F"Using Python {sys.version}")
        logdbg(F"Platform {platform.platform()}")
        logdbg(F"Locale is '{locale.setlocale(locale.LC_ALL)}'")
        logdbg(F"jas version is {VERSION}")
        logdbg(F"First run: {self.generator.first_run}")
        delta_time = self.gen_time - weewx.launchtime_ts if weewx.launchtime_ts else None
        logdbg(F"WeeWX uptime (seconds): {delta_time}")
        #logdbg(self.skin_dict)

        if 'lang' not in self.skin_dict:
            raise AttributeError("'lang' setting is required.")

        self.unit = weewx.units.UnitInfoHelper(generator.formatter, generator.converter)

        self.utc_offset = (datetime.datetime.fromtimestamp(self.gen_time) -
                           datetime.datetime.utcfromtimestamp(self.gen_time)).total_seconds()/60

        self.wind_observations = ['windCompassAverage', 'windCompassMaximum',
                                  'windCompassRange0', 'windCompassRange1', 'windCompassRange2',
                                  'windCompassRange3', 'windCompassRange4', 'windCompassRange5', 'windCompassRange6']

        # todo duplicate code
        self.wind_ranges = {}
        self.wind_ranges['mile_per_hour'] = [1, 4, 8, 13, 19, 25, 32]
        self.wind_ranges['mile_per_hour2'] = [1, 4, 8, 13, 19, 25, 32]
        self.wind_ranges['km_per_hour'] = [.5, 6, 12, 20, 29, 39, 50]
        self.wind_ranges['km_per_hour2'] = [.5, 6, 12, 20, 29, 39, 50]
        self.wind_ranges['meter_per_second'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        self.wind_ranges['meter_per_second2'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        self.wind_ranges['knot'] = [1, 4, 7, 11, 17, 22, 28]
        self.wind_ranges['knot2'] = [1, 4, 7, 11, 17, 22, 28]
        self.wind_ranges_count = 7

        self.skin_dict = generator.skin_dict
        report_dict = self.generator.config_dict.get('StdReport', {})

        self.skin_debug = to_bool(self.skin_dict['Extras'].get('debug', False))
        self.data_binding = self.skin_dict['data_binding']

        self.observations, self.aggregate_types = self._get_observations_information()

        self.skin_dicts = {}
        skin_path = os.path.join(self.generator.config_dict['WEEWX_ROOT'], self.skin_dict['SKIN_ROOT'], self.skin_dict['skin'])
        self.languages = weecfg.get_languages(skin_path)

        html_root = self.skin_dict.get('HTML_ROOT',
                                       report_dict.get('HTML_ROOT', 'public_html'))

        html_root = os.path.join(
            self.generator.config_dict['WEEWX_ROOT'], html_root)
        self.html_root = html_root

        if 'topic' in self.skin_dict['Extras']['mqtt']:
            logerr("'topic' is deprecated, use '[[[[[topics]]]]]'")

        if 'fields' in self.skin_dict['Extras']['mqtt']:
            logerr("'[[[[[fields.unused]]]]]' is deprecated, use '[[[[[topics]]]]] [[[[[[[fields]]]]]]]'")

    def get_extension_list(self, timespan, db_lookup):
        # save these for use when the template variable/function is evaluated
        #self.db_lookup = db_lookup
        #self.timespan = timespan

        search_list_extension = {
                                 'aggregate_types': self.aggregate_types,
                                 'dateTimeFormats': self._get_date_time_formats,
                                 'data_binding': self.data_binding,
                                 'genJs': self._gen_js,
                                 'genJasOptions': self._gen_jas_options,
                                 'genTime': self.gen_time,
                                 'getObsUnitLabel': self._get_obs_unit_label,
                                 'getRange': self._get_range,
                                 'getUnitLabel': self._get_unit_label,
                                 'languages': self.languages,
                                 'last24hours': self._get_last24hours,
                                 'last7days': self._get_last_7_days,
                                 'last31days': self._get_last_31_days,
                                 'last366days': self._get_last_366_days,
                                 'logdbg': logdbg,
                                 'loginf': loginf,
                                 'logerr': logerr,
                                 'observations': self.observations,
                                 'observationLabels': self._get_observation_labels,
                                 #'ordinateNames': self.ordinate_names,
                                 'skinDebug': self._skin_debug,
                                 'textLabels': self._get_text_labels,
                                 'utcOffset': self.utc_offset,
                                 'version': VERSION,
                                 'weewx_version': weewx.__version__,
                                }

        return [search_list_extension]

    def _skin_debug(self, msg):
        if self.skin_debug:
            logdbg(msg)

# Todo - this code is duplicated
    def _get_observations_information(self):
        observations = {}
        aggregate_types = {}
        # ToDo: isn't this done in the init method?
        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        charts = self.skin_dict.get('Extras', {}).get('chart_definitions', {})

        pages = self.skin_dict.get('Extras', {}).get('pages', {})
        for page in pages:
            if not self.skin_dict['Extras']['pages'][page].get('enable', True):
                continue
            for chart in pages[page].sections:
                if chart in charts:
                    chart_data_binding = charts[chart].get('weewx', {}).get('data_binding', skin_data_binding)
                    series = charts[chart].get('series', {})
                    for obs in series:
                        weewx_options = series[obs].get('weewx', {})
                        observation = weewx_options.get('observation', obs)
                        obs_data_binding = series[obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        if observation not in self.wind_observations:
                            if observation not in observations:
                                observations[observation] = {}
                                observations[observation]['aggregate_types'] = {}

                            aggregate_type = weewx_options.get('aggregate_type', 'avg')
                            if aggregate_type not in observations[observation]['aggregate_types']:
                                observations[observation]['aggregate_types'][aggregate_type] = {}

                            if obs_data_binding not in observations[observation]['aggregate_types'][aggregate_type]:
                                observations[observation]['aggregate_types'][aggregate_type][obs_data_binding] = {}

                            unit = weewx_options.get('unit', 'default')
                            observations[observation]['aggregate_types'][aggregate_type][obs_data_binding][unit] = {}
                            aggregate_types[aggregate_type] = {}

        minmax_observations = self.skin_dict.get('Extras', {}).get('minmax', {}).get('observations', {})
        minmax_data_binding = self.skin_dict.get('Extras', {}).get('minmax', {}).get('data_binding', skin_data_binding)
        if minmax_observations:
            for observation in self.skin_dict['Extras']['minmax']['observations'].sections:
                data_binding = minmax_observations[observation].get('data_binding', minmax_data_binding)
                if observation not in self.wind_observations:
                    unit = minmax_observations[observation].get('unit', 'default')
                    if observation not in observations:
                        observations[observation] = {}
                        observations[observation]['aggregate_types'] = {}

                    if 'min' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['min'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['min']:
                        observations[observation]['aggregate_types']['min'][data_binding] = {}
                    observations[observation]['aggregate_types']['min'][data_binding][unit] = {}
                    aggregate_types['min'] = {}
                    if 'max' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['max'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['max']:
                        observations[observation]['aggregate_types']['max'][data_binding] = {}
                    observations[observation]['aggregate_types']['max'][data_binding][unit] = {}
                    aggregate_types['max'] = {}

        if 'thisdate' in self.skin_dict['Extras']:
            thisdate_observations = self.skin_dict.get('Extras', {}).get('thisdate', {}).get('observations', {})
            thisdate_data_binding = self.skin_dict.get('Extras', {}).get('thisdate', {}).get('data_binding', skin_data_binding)
            for observation in  self.skin_dict['Extras']['thisdate']['observations'].sections:
                data_binding = thisdate_observations[observation].get('data_binding', thisdate_data_binding)
                if observation not in self.wind_observations:
                    unit = thisdate_observations[observation].get('unit', 'default')
                    if observation not in observations:
                        observations[observation] = {}
                        observations[observation]['aggregate_types'] = {}

                    if 'min' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['min'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['min']:
                        observations[observation]['aggregate_types']['min'][data_binding] = {}
                    observations[observation]['aggregate_types']['min'][data_binding][unit] = {}
                    aggregate_types['min'] = {}
                    if 'max' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['max'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['max']:
                        observations[observation]['aggregate_types']['max'][data_binding] = {}
                    observations[observation]['aggregate_types']['max'][data_binding][unit] = {}
                    aggregate_types['max'] = {}

        return observations, aggregate_types

    def _get_skin_dict(self, language):
        self.skin_dicts[language] = configobj.ConfigObj()
        # Get the 'lang' file data.
        merge_lang(language, self.generator.config_dict, self.skin_dict['REPORT_NAME'], self.skin_dicts[language])

        # Get the data from the documented report locations in weewx.conf
        # WeeWX does a good job merging this into the skin dict
        # But it merges too much for our use. So pull directly from the 'source'
        self.skin_dicts[language]['Labels']['Generic'].merge(self.generator.config_dict['StdReport']['Defaults'].get('Labels', {}).get('Generic', {}))
        self.skin_dicts[language]['Labels']['Generic'].merge(self.generator.config_dict['StdReport'][self.skin_dict['REPORT_NAME']].get('Labels', {}).get('Generic', {}))
        self.skin_dicts[language]['Texts'].merge(self.generator.config_dict['StdReport'][self.skin_dict['REPORT_NAME']].get('Texts', {}))

        # Now get the jas specific data
        self.skin_dicts[language]['Labels']['Generic'].merge((self.skin_dict['Extras'].get('lang', {}).get(language, {}).get('Labels', {}).get('Generic', {})))
        self.skin_dicts[language]['Texts'].merge((self.skin_dict['Extras'].get('lang', {}).get(language, {}).get('Texts', {})))

    def _get_observation_labels(self, language):
        if language not in self.skin_dicts:
            if language in self.languages:
                self._get_skin_dict(language)

        return self.skin_dicts[language]['Labels']['Generic']

    def _get_text_labels(self, language):
        if language not in self.skin_dicts:
            if language in self.languages:
                self._get_skin_dict(language)

        return self.skin_dicts[language]['Texts']

    def _get_date_time_formats(self, language):
        if language not in self.skin_dicts:
            if language in self.languages:
                self._get_skin_dict(language)

        date_time_formats = {}
        date_time_formats['forecast_date_format'] = self.skin_dicts[language]['Texts']['forecast_date_format']
        date_time_formats['current_date_time'] = self.skin_dicts[language]['Texts']['current_date_time']
        date_time_formats['datepicker_date_format'] = self.skin_dicts[language]['Texts']['datepicker_date_format']

        date_time_formats['year_to_year_xaxis_label'] = self.skin_dicts[language]['Texts']['year_to_year_xaxis_label']

        date_time_formats['aggregate_interval_mqtt'] = {}
        date_time_formats['aggregate_interval_mqtt']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_mqtt']['tooltip_x']
        date_time_formats['aggregate_interval_mqtt']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_mqtt']['xaxis_label']
        date_time_formats['aggregate_interval_mqtt']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_mqtt']['label']

        date_time_formats['aggregate_interval_multiyear'] = {}
        date_time_formats['aggregate_interval_multiyear']['tooltip_x'] = \
            self.skin_dicts[language]['Texts']['aggregate_interval_multiyear']['tooltip_x']
        date_time_formats['aggregate_interval_multiyear']['xaxis_label'] = \
            self.skin_dicts[language]['Texts']['aggregate_interval_multiyear']['xaxis_label']
        date_time_formats['aggregate_interval_multiyear']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_multiyear']['label']

        date_time_formats['aggregate_interval_none'] = {}
        date_time_formats['aggregate_interval_none']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_none']['tooltip_x']
        date_time_formats['aggregate_interval_none']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_none']['xaxis_label']
        date_time_formats['aggregate_interval_none']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_none']['label']

        date_time_formats['aggregate_interval_hour'] = {}
        date_time_formats['aggregate_interval_hour']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_hour']['tooltip_x']
        date_time_formats['aggregate_interval_hour']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_hour']['xaxis_label']
        date_time_formats['aggregate_interval_hour']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_hour']['label']

        date_time_formats['aggregate_interval_day'] = {}
        date_time_formats['aggregate_interval_day']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_day']['tooltip_x']
        date_time_formats['aggregate_interval_day']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_day']['xaxis_label']
        date_time_formats['aggregate_interval_day']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_day']['label']

        return date_time_formats

    def _get_last24hours(self, data_binding=None):
        dbm = self.generator.db_binder.get_manager(data_binding=data_binding)
        end_ts = dbm.lastGoodStamp()
        start_timestamp = end_ts - 86400
        last24hours = TimespanBinder(TimeSpan(start_timestamp, end_ts),
                                     self.generator.db_binder.bind_default(data_binding),
                                     data_binding=data_binding,
                                     context='last24hours',
                                     formatter=self.generator.formatter,
                                     converter=self.generator.converter)

        return last24hours

    def _get_last_7_days(self, data_binding=None):
        return  self._get_last_n_days(7, data_binding=data_binding)

    def _get_last_31_days(self, data_binding=None):
        return  self._get_last_n_days(31, data_binding=data_binding)

    def _get_last_366_days(self, data_binding=None):
        return  self._get_last_n_days(366, data_binding=data_binding)

    def _get_last_n_days(self, days, data_binding=None):
        dbm = self.generator.db_binder.get_manager(data_binding=data_binding)
        end_ts = dbm.lastGoodStamp()
        start_date = datetime.date.fromtimestamp(end_ts) - datetime.timedelta(days=days)
        start_timestamp = time.mktime(start_date.timetuple())
        last_n_days = TimespanBinder(TimeSpan(start_timestamp, end_ts),
                                     self.generator.db_binder.bind_default(data_binding),
                                     data_binding=data_binding,
                                     context='last_n_hours',
                                     formatter=self.generator.formatter,
                                     converter=self.generator.converter)

        return last_n_days

    def _get_obs_unit_label(self, observation):
        # For now, return label for first observations unit. ToDo: possibly change to return all?
        return get_label_string(self.generator.formatter, self.generator.converter, observation, plural=False)

    def _get_unit_label(self, unit):
        return self.generator.formatter.get_label_string(unit, plural=False)

    # to do duplicate code
    def _get_range(self, start, end, data_binding):
        dbm = self.generator.db_binder.get_manager(data_binding=data_binding)
        first_year = int(datetime.datetime.fromtimestamp(dbm.firstGoodStamp()).strftime('%Y'))
        last_year = int(datetime.datetime.fromtimestamp(dbm.lastGoodStamp()).strftime('%Y'))

        if start is None:
            start_year = first_year
        elif start[:1] == "+":
            start_year = first_year + int(start[1:])
        elif start[:1] == "-":
            start_year = last_year - int(start[1:])
        else:
            start_year = int(start)

        if end is None:
            end_year = last_year + 1
        else:
            end_year = int(end) + 1

        return (start_year, end_year)

    def _gen_js(self, filename, page, page_name, year, month, interval_long_name):
        start_time = time.time()
        data = ''

        data += '// start\n'
        data += 'pageLoaded = false;\n'
        data += 'DOMLoaded = false;\n'
        data += 'dataLoaded = false;\n'
        data += 'traceStart = Date.now();\n'
        data += 'console.debug(Date.now().toString() + " starting");\n'

        if interval_long_name:
            start_date = interval_long_name + "startDate"
            end_date = interval_long_name + "endDate"
            start_timestamp = interval_long_name + "startTimestamp"
            end_timestamp = interval_long_name + "endTimestamp"
        else:
            start_date = "null"
            end_date = "null"
            start_timestamp = "null"
            end_timestamp = "null"

        today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

        selected_year = str(today.year)
        if year is not None:
            selected_year = str(year)

        selected_month = str(today.month)
        if month is not None:
            selected_month = str(month)

        offset_seconds = str(self.utc_offset * 60)

        data += 'headerMaxDecimals = ' + self.skin_dict['Extras'].get('current', {}).get('header_max_decimals', 'null') + ';\n'
        data += "logLevel = sessionStorage.getItem('logLevel');\n"

        data += 'if (!logLevel) {\n'
        data += '    logLevel = "' + self.skin_dict['Extras'].get('jas_debug_level', '3') + '";\n'
        data += "    sessionStorage.setItem('logLevel', logLevel);\n"
        data += '}\n'
        data += '\n'

        data += 'function setupZoomDate() {\n'
        data += '    zoomDateRangePicker = new DateRangePicker("zoomdatetimerange-input",\n'
        data += '                        {\n'
        data += '                            minDate: ' + start_date + ',\n'
        data += '                            maxDate: '+ end_date + ',\n'
        data += '                            startDate: '+ start_date + ',\n'
        data += '                            endDate: ' + end_date + ',\n'
        data += '                            locale: {\n'
        data += '                                format: dateTimeFormat[lang].datePicker,\n'
        data += '                                applyLabel: getText("datepicker_apply_label"),\n'
        data += '                                cancelLabel: getText("datepicker_cancel_label"),\n'
        data += '                            },\n'
        data += '                        },\n'
        data += '                        function(start, end, label) {\n'
        data += '                            // Update all charts with selected date/time and min/max values\n'
        data += '                            pageCharts.forEach(function(pageChart) {\n'
        data += '                                pageChart.chart.dispatchAction({type: "dataZoom", startValue: start.unix() * 1000, endValue: end.unix() * 1000});\n'
        data += '                            });\n'
        data += '\n'
        data += '                            updateMinMax(start.unix() * 1000, end.startOf("day").unix() * 1000);\n'
        data += '                    }\n'
        data += '    );\n'
        data += '}\n'
        data += '\n'
        data += 'function setupThisDate() {\n'
        data += '    var thisDateRangePicker = new DateRangePicker("thisdatetimerange-input",\n'
        data += '                        {singleDatePicker: true,\n'
        data += '                            minDate: ' + start_date + ',\n'
        data += '                            maxDate: ' + end_date + ',\n'
        data += '                            locale: {\n'
        data += '                                format: dateTimeFormat[lang].datePicker,\n'
        data += '                                applyLabel: getText("datepicker_apply_label"),\n'
        data += '                                cancelLabel: getText("datepicker_cancel_label"),\n'
        data += '                            },\n'
        data += '                        },\n'
        data += '                            function(start, end, label) {\n'
        data += '                                updateThisDate(start.unix() * 1000);\n'
        data += '                        }\n'
        data += '    );\n'
        data += '\n'
        data += '    var lastDay = new Date(' + selected_year + ', ' + selected_month + ', 0).getDate();\n'
        data += '    var selectedDay = new Date().getDate();\n'
        data += '    if (selectedDay > lastDay) {\n'
        data += '        selectedDay = lastDay;\n'
        data += '    }\n'
        data += '\n'
        data += '    var selectedDate = Date.UTC(' + selected_year + ', ' + selected_month + ' - 1, selectedDay) / 1000 - ' + offset_seconds + ';\n'
        data += '\n'
        data += '    thisDateRangePicker.setStartDate(moment.unix(selectedDate).utcOffset(' + str(self.utc_offset) + '));\n'
        data += '    thisDateRangePicker.setEndDate(moment.unix(selectedDate).utcOffset(' + str(self.utc_offset) + '));\n'
        data += '    updateThisDate(selectedDate * 1000);\n'
        data += '}\n'
        data += '\n'
        wait_milliseconds = str(int(self.skin_dict['Extras']['pages'][page].get('wait_seconds', 300)) * 1000)
        delay_milliseconds = str(int(self.skin_dict['Extras']['pages'][page].get('delay_seconds', 60)) * 1000)
        data += 'function setupPageRefresh() {\n'
        data += '    // Set a timer to reload the iframe/page.\n'
        data += '    var currentDate = new Date();\n'
        data += '    var futureDate = new Date();\n'
        data += '    futureDate.setTime(futureDate.getTime() + ' + wait_milliseconds + ');\n'
        data += '    var futureTimestamp = Math.floor(futureDate.getTime()/' + wait_milliseconds + ') * '+ wait_milliseconds + ';\n'
        data += '    var timeout = futureTimestamp - currentDate.getTime() + ' + delay_milliseconds + ';\n'
        data += '    setTimeout(function() { handleRefreshData(null); setupPageRefresh();}, timeout);\n'
        data += '}\n'
        data += '\n'
        data += '// Handle reset button of zoom control\n'
        data += 'function resetRange() {\n'
        data += '    zoomDateRangePicker.setStartDate(' + start_date + ');\n'
        data += '    zoomDateRangePicker.setEndDate(' + end_date + ');\n'
        data += '    pageCharts.forEach(function(pageChart) {\n'
        data += '            pageChart.chart.dispatchAction({type: "dataZoom", startValue: ' + start_timestamp + ', endValue: ' + end_timestamp + '});\n'
        data += '    });\n'
        data += '    updateMinMax(' + start_timestamp + ', ' + end_timestamp + ');\n'
        data += '}\n'
        data += '\n'
        data += '// Handle event messages of type "mqtt".\n'
        data += 'var test_obj = null; // Not a great idea to be global, but makes remote debugging easier.\n'
        data += 'function updateCurrentMQTT(topic, test_obj) {\n'
        data += '        fieldMap = topics.get(topic);\n'
        data += '        // Handle the "header" section of current observations.\n'
        data +='        header = JSON.parse(sessionStorage.getItem("header"));\n'
        data +='        if (header) {\n'
        data +='            observation = fieldMap.get(header.name);\n'
        data +='            if (observation === undefined) {\n'
        data +='                mqttValue = test_obj[header.name];\n'
        data +='            }\n'
        data +='            else {\n'
        data +='                mqttValue = test_obj[observation];\n'
        data +='            }\n'
        data += '\n'
        data +='            if (mqttValue != undefined) {\n'
        data +='                if (headerMaxDecimals) {\n'
        data +='                    mqttValue = Number(mqttValue).toFixed(headerMaxDecimals);\n'
        data +='                }\n'
        data +='                if (!isNaN(mqttValue)) {\n'
        data +='                    header.value = Number(mqttValue).toLocaleString(lang);\n'
        data +='                }\n'
        data +='            }\n'
        data += '\n'
        data += '            if (test_obj[header.unit]) {\n'
        data +='                header.unit = test_obj[header.unit];\n'
        data +='            }\n'
        data +='            sessionStorage.setItem("header", JSON.stringify(header));\n'
        data +='            headerElem = document.getElementById(header.name);\n'
        data +='            if (headerElem) {\n'
        data +='                headerElem.innerHTML = header.value + header.unit;\n'
        data +='            }\n'
        data +='            headerModalElem = document.getElementById("currentModalTitle");\n'
        data +='            if (headerModalElem) {\n'
        data +='                headerModalElem.innerHTML = header.value + header.unit;\n'
        data +='            }\n'
        data +='        }\n'
        data += '\n'
        data +='        // Process each observation in the "current" section.\n'
        data +='        observations = [];\n'
        data +='        if (sessionStorage.getItem("observations")) {\n'
        data +='            observations = sessionStorage.getItem("observations").split(",");\n'
        data +='        }\n'
        data += '\n'
        data +='        observations.forEach(function(observation) {\n'
        data +='            obs = fieldMap.get(observation);\n'
        data +='            if (obs === undefined) {\n'
        data +='                obs = observation;\n'
        data +='            }\n'
        data +='\n'
        data +='            observationInfo = current.observations.get(observation);\n'
        data +='            if (observationInfo.mqtt && test_obj[obs]) {\n'
        data +='                data = JSON.parse(sessionStorage.getItem(observation));\n'
        data +='                data.value = Number(test_obj[obs]);\n'
        data +='                if (observationInfo.maxDecimals != null) {\n'
        data +='                   data.value = data.value.toFixed(observationInfo.maxDecimals);\n'
        data +='                }\n'
        data +='                if (!isNaN(data.value)) {\n'
        data +='                    data.value = Number(data.value).toLocaleString(lang);\n'
        data +='                }\n'
        data +='                sessionStorage.setItem(observation, JSON.stringify(data));\n'
        data += '\n'
        # ToDo: see if this can be removed
        #data +='                labelElem = document.getElementById(observation + "_label");\n'
        #data +='                if (labelElem) {\n'
        #data +='                    labelElem.innerHTML = data.label;\n'
        #data +='                }\n'
        data +='                dataElem = document.getElementById(data.name + "_value");\n'
        data +='                if (dataElem) {\n'
        data +='                    dataElem.innerHTML = data.value + data.unit;\n'
        data +='                }\n'
        data += '               if (data.modalLabel) {\n'
        data +='                    document.getElementById(data.modalLabel).innerHTML = data.value + data.unit;\n'
        data += '               }\n'
        data +='            }\n'
        data +='        });\n'
        data += '\n'
        data +='        // And the "current" section date/time.\n'
        data +='        if (test_obj.dateTime) {\n'
        data +='            sessionStorage.setItem("updateDate", test_obj.dateTime*1000);\n'
        data +='            timeElem = document.getElementById("updateDateDiv");\n'
        data +='            if (timeElem) {\n'
        data +='                timeElem.innerHTML = moment.unix(test_obj.dateTime).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].current);\n'
        data +='            }\n'
        data +='            timeModalElem = document.getElementById("updateModalDate");\n'
        data +='            if (timeModalElem) {\n'
        data +='                timeModalElem.innerHTML = moment.unix(test_obj.dateTime).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].current);\n'
        data +='            }\n'
        data +='        }\n'
        data += '}\n'
        data += '\n'
        data += 'function updateCurrentObservations() {\n'
        data += '    if (jasOptions.currentHeader) {\n'
        data +='        //ToDo: switch to allow non mqtt header data? similar to the observation section\n'
        data +='        if(sessionStorage.getItem("header") === null || !jasOptions.MQTTConfig){\n'
        data +='            sessionStorage.setItem("header", JSON.stringify(current.header));\n'
        data +='        }\n'
        data +='        header = JSON.parse(sessionStorage.getItem("header"));\n'
        data +='        document.getElementById(jasOptions.currentHeader).innerHTML = header.value + header.unit;\n'
        data += '    }\n'
        data += '\n'
        data += '    if (jasOptions.displayAerisObservation) {\n'
        data +='        document.getElementById("currentObservation").innerHTML = current_observation;\n'
        data += '    }\n'
        data += '\n'
        data += '    // ToDo: cleanup, perhaps put observation data into an array and store that\n'
        data += '    // ToDo: do a bit more in cheetah?\n'
        data += '    observations = [];\n'
        data += '    for (var [observation, data] of current.observations) {\n'
        data +='        observations.push(observation);\n'
        data +='        if (sessionStorage.getItem(observation) === null || !jasOptions.MQTTConfig || ! data.mqtt){\n'
        data +='            sessionStorage.setItem(observation, JSON.stringify(data));\n'
        data +='        }\n'
        data +='        obs = JSON.parse(sessionStorage.getItem(observation));\n'
        data += '\n'
        data +='        document.getElementById(obs.name + "_value").innerHTML = obs.value + obs.unit;\n'
        data += '    }\n'
        data += '    sessionStorage.setItem("observations", observations.join(","));\n'
        data += '\n'
        data += '    if(sessionStorage.getItem("updateDate") === null || !jasOptions.MQTTConfig){\n'
        data +='        sessionStorage.setItem("updateDate", updateDate);\n'
        data += '    }\n'
        data += '    document.getElementById("updateDateDiv").innerHTML = moment.unix(sessionStorage.getItem("updateDate")/1000).utcOffset(' + str(self.utc_offset) +').format(dateTimeFormat[lang].current);\n'
        data += '}\n'
        data += '\n'

        if 'minmax' in self.skin_dict['Extras']['pages'][page]:
            data += '// Update the min/max observations\n'
            data += 'function updateMinMax(startTimestamp, endTimestamp) {\n'
            data += '    jasLogDebug("Min start: ", startTimestamp);\n'
            data += '    jasLogDebug("Max start: ", endTimestamp);\n'
            data += '    // ToDo: optimize to only get index once for all observations?\n'
            data += '    minMaxObs.forEach(function(minMaxObsData) {\n'
            data +='        startIndex = minMaxObsData.minDateTimeArray.findIndex(element => element == startTimestamp);\n'
            data +='        endIndex = minMaxObsData.minDateTimeArray.findIndex(element => element == endTimestamp);\n'
            data +='        if (startIndex < 0) {\n'
            data +='            startIndex = 0;\n'
            data +='        }\n'
            data +='        if (endIndex < 0) {\n'
            data +='            endIndex  = minMaxObsData.minDateTimeArray.length - 1;\n'
            data +='        }\n'
            data +='        if (startIndex == endIndex) {\n'
            data +='            minIndex = startIndex;\n'
            data +='            maxIndex = endIndex;\n'
            data +='        } else {\n'
            data +='            minIndex = minMaxObsData.minDataArray.indexOf(Math.min(...minMaxObsData.minDataArray.slice(startIndex, endIndex + 1).filter(obs => obs != null)));\n'
            data +='            maxIndex = minMaxObsData.maxDataArray.indexOf(Math.max(...minMaxObsData.maxDataArray.slice(startIndex, endIndex + 1)));\n'
            data +='        }\n'
            data += '\n'
            data +='        min = minMaxObsData.minDataArray[minIndex];\n'
            data +='        max = minMaxObsData.maxDataArray[maxIndex];\n'
            data +='        if (minMaxObsData.maxDecimals) {\n'
            data +='            min = min.toFixed(minMaxObsData.maxDecimals);\n'
            data +='            max = max.toFixed(minMaxObsData.maxDecimals);\n'
            data +='        }\n'
            data +='        min = Number(min).toLocaleString(lang);\n'
            data +='        max = Number(max).toLocaleString(lang);\n'
            data +='        min = min + minMaxObsData.label;\n'
            data +='        max = max + minMaxObsData.label;\n'
            data +='\n'
            min_format = self.skin_dict['Extras']['page_definition'][page].get('aggregate_interval', {}).get('min', 'none')
            max_format = self.skin_dict['Extras']['page_definition'][page].get('aggregate_interval', {}).get('max', 'none')
            data +='        minDate = moment.unix(minMaxObsData.minDateTimeArray[minIndex]/1000).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].chart["' + min_format + '"].label);\n'
            data +='        maxDate = moment.unix(minMaxObsData.maxDateTimeArray[maxIndex]/1000).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].chart["' +max_format + '"].label);\n'
            data += '\n'
            data +='        observation_element=document.getElementById(minMaxObsData.minId);\n'
            data +='        observation_element.innerHTML = min + "<br>" + minDate;\n'
            data +='        observation_element=document.getElementById(minMaxObsData.maxId);\n'
            data +='        observation_element.innerHTML = max + "<br>" + maxDate;\n'
            data += '    });\n'
            data += '}\n'

        data += '\n'
        default_theme = to_list(self.skin_dict['Extras'].get('themes', 'light'))[0]
        data += 'document.addEventListener("DOMContentLoaded", function (event) {\n'
        data += '    console.debug(Date.now().toString() + " DOMContentLoaded start");\n'
        data += '    setupPage();\n'
        data += '    console.debug(Date.now().toString() + " setupPage done");\n'
        if page != 'about':
            data += '    setupCharts();\n'
            data += '    console.debug(Date.now().toString() + " setupCharts done");\n'
        data += '    DOMLoaded = true;\n'
        data += '    console.debug(Date.now().toString() + " DOMContentLoaded end");\n'
        data += '});\n'
        data += '\n'

        data += 'function updateData() {\n'
        data += '    console.debug(Date.now().toString() + " updateData start");\n'
        data += '    if (jasOptions.minmax) {\n'
        data +='        updateMinMax(' + start_timestamp + ', ' + end_timestamp + ');\n'
        data += '    }\n'
        data += '\n'
        data += '    // Set up the date/time picker\n'
        data += '    if (jasOptions.zoomcontrol) {\n'
        data +='        setupZoomDate();\n'
        data += '    }\n'
        data += '\n'
        data += '    if (jasOptions.thisdate) {\n'
        data +='        setupThisDate();\n'
        data += '    }\n'
        data += '\n'
        data += '    if (jasOptions.current) {\n'
        data +='        updateCurrentObservations();\n'
        data += '    }\n'
        data += '    console.debug(Date.now().toString() + " updateCurrentObservations done");\n'
        data += '    if (jasOptions.forecast) {\n'
        data +='        updateForecasts();\n'
        data += '    }\n'
        data += '    console.debug(Date.now().toString() + " updateForecasts done");\n'
        data += '    updateChartData();\n'
        data += '    console.debug(Date.now().toString() + " updateChartData done");\n'
        data += '    console.debug(Date.now().toString() + " updateData end");\n'
        data +='\n'
        data += '}\n'
        data += '\n'

        data += 'function setupPage(pageDataString) {\n'
        data += '    console.debug(Date.now().toString() + " setupPage start");\n'
        data += '    theme = sessionStorage.getItem("theme");\n'
        data += '    if (!theme) {\n'
        data += '        theme = "' + default_theme + '";\n'
        data += '    }\n'
        data += '    console.debug(Date.now().toString() + " getTheme done");\n'
        data += '    setTheme(theme);\n'
        data += '    console.debug(Date.now().toString() + " setTheme done");\n'
        data += '    updateTexts();\n'
        data += '    console.debug(Date.now().toString() + " updateTexts done");\n'
        data += '    updateLabels();\n'
        data += '    console.debug(Date.now().toString() + " updateLabels done");\n'
        data += '\n'
        data += '    if (jasOptions.refresh) {\n'
        data +='        setupPageRefresh();\n'
        data += '    }\n'
        data += '\n'
        data += '    console.debug(Date.now().toString() + " setupPage end");\n'
        data += '};\n'
        data += '\n'

        data += 'window.addEventListener("load", function (event) {\n'
        data += '    console.debug(Date.now().toString() + " onLoad start");\n'
        data += '    setIframeSrc();\n'
        data += '    if (dataLoaded) {\n'
        data += '        pageLoaded = true;\n'
        data += '        updateData();\n'
        data += '    }\n'

        data += '    modalChart = null;\n'
        data += '    var chartModal = document.getElementById("chartModal");\n'

        data += '    chartModal.addEventListener("shown.bs.modal", function (event) {\n'
        data += '      var titleElem = document.getElementById("chartModalTitle");\n'
        data += '      titleElem.innerText = getText(event.relatedTarget.getAttribute("data-bs-title"));\n'
        data += '      var divelem = document.getElementById("chartModalBody");\n'
        data += '      modalChart = echarts.init(divelem);\n'

        data += '      var chartId = event.relatedTarget.getAttribute("data-bs-chart");\n'
        data += '      index = pageIndex[chartId];\n'
        data += '      option = pageCharts[index]["def"];\n'
        data += '      modalChart.setOption(option);\n'
        data += '      modalChart.setOption(pageCharts[index]["option"]);\n'
        data += '      resizeChart(modalChart, elemHeight = divelem.getAttribute("jasHeight") -\n'
        data += '                                      4* document.getElementById("chartModalHeader").clientHeight -\n'
        data += '                                      document.getElementById("chartModalFooter").clientHeight);\n'
        data += '    })\n'

        data += '    chartModal.addEventListener("hidden.bs.modal", function (event) {\n'
        data += '      modalChart.dispose();\n'
        data += '      modalChart = null;\n'

        data += '      bootstrap.Modal.getInstance(document.getElementById("chartModal")).dispose();\n'
        data += '    })\n'

        data += '    if (jasOptions.current) {\n'
        data += '      var currentModal = document.getElementById("currentModal");\n'
        data += '      currentModal.addEventListener("shown.bs.modal", function (event) {\n'
        data +='          headerModalElem = document.getElementById("currentModalTitle");\n'
        data +='          if (headerModalElem) {\n'
        data +='              headerModalElem.innerHTML = header.value + header.unit;\n'
        data +='          }\n'

        data += '        if (jasOptions.displayAerisObservation) {\n'
        data +='           document.getElementById("currentObservationModal").innerHTML = current_observation;\n'
        data += '        }\n'
        data +='         // Process each observation in the "current" section.\n'
        data +='         observations = [];\n'
        data +='         if (sessionStorage.getItem("observations")) {\n'
        data +='            observations = sessionStorage.getItem("observations").split(",");\n'
        data +='         }\n'
        data += '\n'
        data +='         observations.forEach(function(observation) {\n'
        data +='            obs = JSON.parse(sessionStorage.getItem(observation));\n'
        data += '           if (obs.modalLabel) {\n'
        data +='                document.getElementById(obs.modalLabel).innerHTML = obs.value + obs.unit;\n'
        data += '           }\n'
        data +='         });\n'

        data +='         var updateDate = sessionStorage.getItem("updateDate")/1000;\n'
        data +='         timeElem = document.getElementById("updateModalDate");\n'
        data +='         if (timeElem) {\n'
        data +='            timeElem.innerHTML = moment.unix(updateDate).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].current);\n'
        data +='         }\n'
        data += '    })\n'

        data += '    currentModal.addEventListener("hidden.bs.modal", function (event) {\n'
        data += '      bootstrap.Modal.getInstance(document.getElementById("currentModal")).dispose();\n'
        data += '    })\n'
        data +='   }\n'

        data += '    // Todo: create functions for code in the if statements\n'
        data += '    // Tell the parent page the iframe size\n'
        data += '    message = {};\n'
        data += '    message.kind = "resize";\n'
        data += '    message.message = {};\n'
        data += '    message.message = { height: document.body.scrollHeight, width: document.body.scrollWidth };\n'
        data += '    // window.top refers to parent window\n'
        data += '    window.top.postMessage(message, "*");\n'
        data += '\n'
        data += '    // When the iframe size changes, let the parent page know\n'
        data += '    const myObserver = new ResizeObserver(entries => {\n'
        data +='        entries.forEach(entry => {\n'
        data += '       message = {};\n'
        data += '       message.kind = "resize";\n'
        data += '       message.message = {};\n'
        data +='        message.message = { height: document.body.scrollHeight, width: document.body.scrollWidth };\n'
        data +='        // window.top refers to parent window\n'
        data +='        window.top.postMessage(message, "*");\n'
        data +='        });\n'
        data += '    });\n'
        data += '    myObserver.observe(document.body);\n'
        data += '\n'
        data += '    message = {};\n'
        data += '    message.kind = "loaded";\n'
        data += '    message.message = {};\n'
        data += '    // window.top refers to parent window\n'
        data += '    window.top.postMessage(message, "*");\n'
        data += '    console.debug(Date.now().toString() + " onLoad End");\n'
        data += '});\n'
        data += '\n'
        data += 'function setIframeSrc() {\n'
        data += '    url = "../dataload/' + page_name + '.html";\n'
        if page in self.skin_dict['Extras']['pages'] and \
          'data' in to_list(self.skin_dict['Extras']['pages'][page].get('query_string_on', self.skin_dict['Extras']['pages'].get('query_string_on', []))):
            data += '    // use query string so that iframe is not cached\n'
            data += '    url = url + "?ts=" + Date.now();\n'
        data += '    document.getElementById("data-iframe").src = url;\n'
        data += '}\n'

        javascript = '''
function jasShow(data) {
    return window[data]
}

function updatelogLevel(logLevel) {
    jasLogDebug = () => {};
    jasLogInfo = () => {};
    jasLogWarn= () => {};
    jasLogError = () => {};

    switch(logLevel) {
        case "1":
            jasLogDebug = (prefix, info) => {console.debug(prefix + JSON.stringify(info));};
        case "2":
            jasLogInfo = (prefix, info) => {console.info(prefix + JSON.stringify(info));};
        case "3":
            jasLogWarn = (prefix, info) => {console.warn(prefix + JSON.stringify(info));};
        case "4":
            jasLogError = (prefix, info) => {console.error(prefix + JSON.stringify(info));};
        }
}

updatelogLevel(logLevel);

// ToDo: make a dictionary of dictionaries
var pageCharts = [];
var pageIndex = {};

// Ensure that the height of charts is consistent ratio of the width.
function refreshSizes() {
    radarElem = document.getElementById("radar");
    if (radarElem) {
        // Match the height of charts 
        height = radarElem.offsetWidth / 1.618;
        height = height + "px";    
        radarElem.style.height = height; 
    }

    for (var index in pageCharts) {
        resizeChart(pageCharts[index].chart);
    }
}

function resizeChart(chart, elemHeight = null) {
    chartElem = chart.getDom();
    if (!elemHeight){ 
        height = chartElem.offsetWidth / 1.618;
    }
    else {
        height = Math.min(height = chartElem.offsetWidth / 1.618, elemHeight);
    }
    width = Math.max(document.documentElement.clientWidth, window.innerWidth || 0);
    // width/100 is like the css variable vw
    fontSize = width/100 * 1.5;
    // Max is 18px and min is 10px
    document.getElementsByTagName("html")[0].style.fontSize = Math.min(18, Math.max(10, fontSize)) + "px";
    height = height + "px";
    chart.resize({width: null, height: height});
    options = chart.getOption();
    updatedOptions = {};
    if (chartElem.offsetWidth > 505) {
        percent = 1;
        legendTextStyleWidth = 70;
        legendIcon = 'roundRect';
    }
    else if (chartElem.offsetWidth > 350) {
        percent = 2/3;
        legendTextStyleWidth = 70;
        legendIcon = 'roundRect';
    }
    else if (chartElem.offsetWidth > 300) {
        percent = 1/2;
        legendTextStyleWidth = 70;
        legendIcon = 'roundRect';
    }
    else {
        percent = 1/2;
        legendTextStyleWidth = 20;
        legendIcon = 'none';    
    }

    updatedOptions.toolbox = {};
    updatedOptions.toolbox.itemSize = Math.round(15 * percent);
    updatedOptions.toolbox.showTitle = false
    updatedOptions.tooltip = {};
    updatedOptions.tooltip.textStyle = {};
    updatedOptions.tooltip.textStyle.fontSize = Math.round(14 * percent); 
    updatedOptions.axisPointer = {};
    updatedOptions.axisPointer.label = {};
    updatedOptions.axisPointer.label.fontSize = Math.round(12 * percent); 
    updatedOptions.legend = {};
    updatedOptions.legend.itemHeight = Math.round(14 * percent); 
    updatedOptions.legend.itemWidth = Math.round(25 * percent); 
    updatedOptions.legend.textStyle = {};
    updatedOptions.legend.textStyle.fontSize = Math.round(12 * percent);
    if (options.legend[0].type == 'scroll') {
        updatedOptions.legend.pageIconSize = Math.round(15 * percent); 
        updatedOptions.legend.pageTextStyle = {};
        updatedOptions.legend.pageTextStyle.fontSize = Math.round(12 * percent); 
    }
    if ('xAxis' in options) {
        updatedOptions.xAxis = {};
        updatedOptions.xAxis.axisLabel = {};
        updatedOptions.xAxis.axisLabel.fontSize = Math.round(12 * percent); 
        updatedOptions.yAxis = [];
        for (let i = 0; i < options.yAxis.length; i++) {
            updatedOptions.yAxis[i] = {};
            updatedOptions.yAxis[i].axisLabel = {};
            updatedOptions.yAxis[i].axisLabel.fontSize = Math.round(12 * percent); 
            updatedOptions.yAxis[i].nameTextStyle = {};
            updatedOptions.yAxis[i].nameTextStyle.fontSize = Math.round(12 * percent); 
        }      
    }
    if ('angleAxis' in options) {
        updatedOptions.legend.textStyle.width = legendTextStyleWidth;    
        updatedOptions.legend.icon = legendIcon;
        updatedOptions.angleAxis = {};
        updatedOptions.angleAxis.axisLabel = {};
        updatedOptions.angleAxis.axisLabel.fontSize = Math.round(12 * percent);
    }

    chart.setOption(updatedOptions);
}

function getLogLevel() {
    return "Sub-page log level: " + sessionStorage.getItem("logLevel")
}

function setLogLevel(logLevel) {
    sessionStorage.setItem("logLevel", logLevel);
    updatelogLevel(logLevel.toString());
    return "Sub-page log level: " + sessionStorage.getItem("logLevel")
}

// Handle event messages of type "setTheme".
function setTheme(theme) {
    buttons = document.getElementsByClassName("btn");
    if (theme == 'dark') {
        for(var i = 0; i < buttons.length; i++)
        {
            buttons[i].classList.remove("btn-dark");
            buttons[i].classList.add("btn-light");
        }
    }
    else {
        for(var i = 0; i < buttons.length; i++)
        {
            buttons[i].classList.remove("btn-light");
            buttons[i].classList.add("btn-dark");
        }
    }

    if (document.documentElement.getAttribute('data-bs-theme') == theme) {
        return;
    }
    document.documentElement.setAttribute('data-bs-theme', theme);
    const style = getComputedStyle(document.body);
    bsBodyColor =  style.getPropertyValue("--bs-body-color");

    textColor = {
        textStyle: {
            color: bsBodyColor
        }
    }
    toolboxColor = {
        toolbox: {
            iconStyle: {
                borderColor: bsBodyColor
            }        
        }
    }
    xAxisColor = {
        xAxis: {
            axisLine: {
                lineStyle: {
                    color: bsBodyColor
                }
            }
        }
    } 
    angleAxisColor = {
        angleAxis: {
            axisLine: {
                lineStyle: {
                    color: bsBodyColor
                }
            }
        }
    }     

    for (var index in pageCharts) {
        options = pageCharts[index].chart.getOption();
        pageCharts[index].chart.setOption(textColor);
        pageCharts[index].chart.setOption(toolboxColor);
        if ('xAxis' in options) {
            pageCharts[index].chart.setOption(xAxisColor);
        }
        if ('angleAxis' in options) {
            pageCharts[index].chart.setOption(angleAxisColor);
        }            
    }

}

// Handle event messages of type "lang".
function handleLang(lang) {
    sessionStorage.setItem("currentLanguage", lang);
    window.location.reload(true);
}

// Handle event messages of type "resize".
function handleResize(message) {
  var divelem = document.getElementById('chartModalBody');
  divelem.setAttribute('jasHeight', message.height)
  if (modalChart) {
     resizeChart(modalChart, elemHeight = message.height -
                            4 * document.getElementById('chartModalHeader').clientHeight - 
                            document.getElementById('chartModalFooter').clientHeight)
  }    
}

// Handle event messages of type "log".
function handleLog(message) {
    var logDisplayElem = document.getElementById("logDisplay");
    if (logDisplayElem) {
        logDisplayElem.innerHTML = message + "\\n<br>" + logDisplayElem.innerHTML;
    }
}

// Handle event messages of type "refreshData".
function handleRefreshData(message) {
    setIframeSrc();
}

// Handle event messages of type "scroll".
function handleScroll(message) {
    document.getElementById('chartModal').style.top = message.currentScroll + 'px';
}

// Handle event messages of type "dataLoaded".
function handleDataLoaded(message) {
    console.debug(Date.now().toString() + " handleDataLoaded start");
'''
        data += javascript

        if page in self.skin_dict['Extras']['page_definition']:
            series_type = self.skin_dict['Extras']['page_definition'][page].get('series_type', 'single')
            if series_type == 'single':
                data += 'getData' + interval_long_name + '(message);\n'
            elif series_type == 'multiple':
                data += 'getDataMultiyear(message);\n'
            elif series_type == 'comparison':
                data += 'getDataComparison(message);\n'
            data += 'console.debug(Date.now().toString() + " getData done");\n'

        javascript = '''
    dataLoaded = true;\n
    if (DOMLoaded) {
        pageLoaded = true;
        updateData();
    }
    console.debug(Date.now().toString() + " handleDataLoaded end");
 }

function handleMQTT(message) {
    test_obj = JSON.parse(message.payload);
    
    jasLogDebug("test_obj: ", test_obj);
    jasLogDebug("sessionStorage: ", sessionStorage);
    jasLogDebug("topics: ", Object.fromEntries(topics));
    // ToDo - only exists on pages with "current" section
    //jasLogDebug("current.observations: ", Object.fromEntries(current.observations));

    if (jasOptions.current && jasOptions.pageMQTT)
    {
        updateCurrentMQTT(message.topic, test_obj);
    }

    // Proof of concept, charting MQTT data
    for (obs in test_obj) {
        if (obs in mqttData2) {
            if (mqttData2[obs].length >= 1800) {
                mqttData2[obs].shift;
            }
            mqttData2[obs].push([parseInt(test_obj.dateTime) * 1000, parseFloat(test_obj[obs])]);
        }
    }
    
    pageCharts.forEach(function(pageChart) {
        if (pageChart.option === null) {
            echartSeries = [];
            pageChart.series.forEach(function(series) {
                seriesData = {};
                seriesData.data = mqttData2[series.obs];
                seriesData.name = series.name;
                if (seriesData.name == null) {
                    seriesData.name = getLabel(series.obs);
                }
                echartSeries.push(seriesData);
            });
            pageChart.chart.setOption({series: echartSeries});
        }
    });
}

// Get the observation for timeSramp
function getObservation(timeStamp, observations) {
    var array_result = observations.filter(function(v,i) { return v[0] === timeStamp; });
    if (array_result.length > 0)     {
        return array_result[0][1];
    }

    return observations[0][1];
}

// Update the "on this date" observations with observations at timeStamp
function updateThisDate(timeStamp) {
    thisDateObsList.forEach(function(thisDateObs) {
        thisDateObs.forEach(function(thisDateObsDetail) {
            obs = getObservation(timeStamp, thisDateObsDetail.dataArray);
            if (thisDateObsDetail.maxDecimals) {
                obs = obs.toFixed(thisDateObsDetail.maxDecimals);
            }
            obsValue = Number(obs).toLocaleString(lang);
            observation=document.getElementById(thisDateObsDetail.id);
            observation.innerHTML = obsValue + thisDateObsDetail.label;                    
        });
    });
}

function updateForecasts() {
    i = 0;
    forecasts.forEach(function(forecast)
    {
        observation = '';
        forecast.observation_codes.forEach(function(observationCode) {
            observation += getText(observationCode) + ' '
        });'''

        data += javascript + "\n"
        data += '        date = moment.unix(forecast["timestamp"]).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].forecast);\n'

        javascript =\
        '''        observationId = "forecastObservation" + i;
        document.getElementById("forecastDate" + i).innerHTML = getText(forecast["day_code"])  + " " + date;
        document.getElementById("forecastObservation" + i).innerHTML = observation;
        document.getElementById("forecastTemp" + i).innerHTML = forecast["temp_min"] + " | " + forecast["temp_max"];
        document.getElementById("forecastRain" + i).innerHTML = '<i class="bi bi-droplet"></i>' + ' ' + forecast['rain'] + '%';
        document.getElementById('forecastWind' + i).innerHTML = '<i class="bi bi-wind"></i>' + ' ' + forecast['wind_min'] + ' | ' + forecast['wind_max'] + ' ' + forecast['wind_unit'];
        i += 1;
    });
}

window.addEventListener("onresize", function() {
    message = {};
    message.kind = "resize";
    message.message = {};
    message.message = { height: document.body.scrollHeight, width: document.body.scrollWidth };	

    // window.top refers to parent window
    window.top.postMessage(message, "*");
});

window.addEventListener("message",
                        function(e) {
                        // Running directly from the file system has some strangeness
                        if (window.location.origin != "file://" && e.origin !== window.location.origin)
                        return;

                        message = e.data;
                        if (message.kind == undefined) {
                            return;
                        }
                        if (message.kind == "jasShow")
                        {
                            console.log(jasShow(message.message));
                        }       
                        if (message.kind == "getLogLevel")
                        {
                            console.log(getLogLevel());
                        }                                           
                        if (message.kind == "setLogLevel")
                        {
                            console.log(setLogLevel(message.message.logLevel));
                        }                        
                        if (message.kind == "lang")
                        {
                            handleLang(message.message);
                        }
                        if (message.kind == "dataLoaded")
                        {
                            handleDataLoaded(message.message);
                        }                        
                        if (message.kind == "mqtt")
                        {
                            handleMQTT(message.message);
                        }
                        if (message.kind == "setTheme")
                        {
                            setTheme(message.message);
                        }
                        if (message.kind == "refreshData")
                        {
                            handleRefreshData(message.message);
                        }                               
                        if (message.kind == "resize")
                        {
                            handleResize(message.message);
                        }                        
                        if (message.kind == "scroll")
                        {
                            handleScroll(message.message);
                        }       
                        if (message.kind == "log")
                        {
                            handleLog(message.message);
                        }},
                        false
                       );
        '''

        data += javascript + "\n"

        data += 'console.debug(Date.now().toString() + " ending");\n'
        data += '// end\n'

        elapsed_time = time.time() - start_time
        log_msg = "Generated " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return data

    def _gen_jas_options(self, filename, page):
        start_time = time.time()
        data = ''

        data += '/* jas ' + VERSION + ' ' + str(self.gen_time) + ' */\n'

        data += "jasOptions = {};\n"

        data += "jasOptions.pageMQTT = " + self.skin_dict['Extras']['pages'][page].get('mqtt', 'true').lower() + ";\n"
        data += "jasOptions.displayAerisObservation = -" + self.skin_dict['Extras'].get('display_aeris_observation', 'false').lower() + ";\n"
        data += "jasOptions.refresh = " + self.skin_dict['Extras']['pages'][page].get('reload', 'false').lower() + ";\n"
        data += "jasOptions.zoomcontrol = " + self.skin_dict['Extras']['pages'][page].get('zoomControl', 'false').lower() + ";\n"

        data += "jasOptions.currentHeader = null;\n"

        if self.skin_dict['Extras'].get('current', {}).get('observation', False):
            data += "jasOptions.currentHeader = '" + self.skin_dict['Extras']['current']['observation'] + "';\n"

        if "current" in self.skin_dict['Extras']['pages'][page]:
            data += "jasOptions.current = true;\n"
        else:
            data += "jasOptions.current = false;\n"

        if "forecast" in self.skin_dict['Extras']['pages'][page]:
            data += "jasOptions.forecast = true;\n"
        else:
            data += "jasOptions.forecast = false;\n"

        if "minmax" in self.skin_dict['Extras']['pages'][page]:
            data += "jasOptions.minmax = true;\n"
        else:
            data += "jasOptions.minmax = false;\n"

        if "thisdate" in self.skin_dict['Extras']['pages'][page]:
            data += "jasOptions.thisdate = true;\n"
        else:
            data += "jasOptions.thisdate = false;\n"

        if to_bool(self.skin_dict['Extras']['pages'][page].get('mqtt', True)) and to_bool(self.skin_dict['Extras']['mqtt'].get('enable', False)) or page == "debug":
            data += "jasOptions.MQTTConfig = true;\n"
        else:
            data += "jasOptions.MQTTConfig = false;\n"

        data += "\n"

        elapsed_time = time.time() - start_time
        log_msg = "Generated jasOptions for " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return data

class JASGenerator(weewx.reportengine.ReportGenerator):
    """ Generate the charts used by the JAS skin. """
    def __init__(self, config_dict, skin_dict, *args, **kwargs):
        """Initialize an instance of ChartGenerator"""
        self.gen_time = int(time.time())
        weewx.reportengine.ReportGenerator.__init__(self, config_dict, skin_dict, *args, **kwargs)

        self.data_binding = self.skin_dict['data_binding']

        self.generator_dict = {'archive-day'  : weeutil.weeutil.genDaySpans,
                               'archive-month': weeutil.weeutil.genMonthSpans,
                               'archive-year' : weeutil.weeutil.genYearSpans}        


    def _skip_generation(self, generator_dict, timespan, generate_interval, interval_type, filename, stop_ts):

        if generator_dict and to_bool(generator_dict.get('generate_once', False)) and not self.first_run:
            return True

        if interval_type == 'historical' \
                and os.path.exists(filename) \
                and not timespan.includesArchiveTime(stop_ts):
            return True

        generate_interval_seconds = weeutil.weeutil.nominal_spans(generate_interval)

        if generate_interval_seconds is None or not os.path.exists(filename):
            return False

        if stop_ts - os.stat(filename).st_mtime >= generate_interval_seconds:
            return False

        # If we're on an aggregation boundary, regenerate.
        time_dt = datetime.datetime.fromtimestamp(stop_ts)
        tdiff = time_dt -  time_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        if abs(tdiff.seconds % generate_interval_seconds) < 1:
            return False

        return True

class ChartGenerator(JASGenerator):
    """ Generate the charts used by the JAS skin. """
    def __init__(self, config_dict, skin_dict, *args, **kwargs):
        """Initialize an instance of ChartGenerator"""
        JASGenerator.__init__(self, config_dict, skin_dict, *args, **kwargs)

        self.formatter = weewx.units.Formatter.fromSkinDict(skin_dict)
        self.converter = weewx.units.Converter.fromSkinDict(skin_dict)

        now = time.time()
        self.utc_offset = (datetime.datetime.fromtimestamp(now) -
                           datetime.datetime.utcfromtimestamp(now)).total_seconds()/60

        # todo duplicate code
        self.wind_ranges = {}
        self.wind_ranges['mile_per_hour'] = [1, 4, 8, 13, 19, 25, 32]
        self.wind_ranges['mile_per_hour2'] = [1, 4, 8, 13, 19, 25, 32]
        self.wind_ranges['km_per_hour'] = [.5, 6, 12, 20, 29, 39, 50]
        self.wind_ranges['km_per_hour2'] = [.5, 6, 12, 20, 29, 39, 50]
        self.wind_ranges['meter_per_second'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        self.wind_ranges['meter_per_second2'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        self.wind_ranges['knot'] = [1, 4, 7, 11, 17, 22, 28]
        self.wind_ranges['knot2'] = [1, 4, 7, 11, 17, 22, 28]
        self.wind_ranges_count = 7

        self.ordinate_names = copy.deepcopy(self.formatter.ordinate_names)
        del self.ordinate_names[-1]

        self.chart_defaults = self.skin_dict['Extras']['chart_defaults'].get('global', {})
        self.chart_series_defaults = self.skin_dict['Extras']['chart_defaults'].get('chart_type', {}).get('series', {})
        self.charts_javascript = {}

        self._set_chart_defs()

    def run(self):
        self.generator_dict = {'archive-day'  : weeutil.weeutil.genDaySpans,
                    'archive-month': weeutil.weeutil.genMonthSpans,
                    'archive-year' : weeutil.weeutil.genYearSpans}        

        # Get start and stop times
        default_archive = self.db_binder.get_manager(self.data_binding)
        start_ts = default_archive.firstGoodStamp()
        if not start_ts:
            log.info('Skipping, cannot find start time')
            return

        if self.gen_ts:
            record = default_archive.getRecord(self.gen_ts)
            if record:
                stop_ts = record['dateTime']
            else:
                log.info('Skipping, generate time %s not in database', timestamp_to_string(self.gen_ts))
                return
        else:
            stop_ts = default_archive.lastGoodStamp()

        destination_dir = os.path.join(self.config_dict['WEEWX_ROOT'],
                                    self.skin_dict['HTML_ROOT'],
                                    'charts')

        try:
            # Create the directory that is to receive the generated files.  If
            # it already exists an exception will be thrown, so be prepared to
            # catch it.
            os.makedirs(destination_dir)
        except OSError:
            pass

        for page_name in self.skin_dict['Extras']['pages'].sections:
            if self.skin_dict['Extras']['pages'].get('enable', True) and \
                page_name in self.skin_dict['Extras']['page_definition']:

                if page_name in self.generator_dict:
                    _spangen = self.generator_dict[page_name]
                else:
                    _spangen = lambda start_ts, stop_ts: [weeutil.weeutil.TimeSpan(start_ts, stop_ts)]
                for timespan in _spangen(start_ts, stop_ts):
                    #self.timespan = timespan # todo
                    start_tt = time.localtime(timespan.start)
                    #stop_tt = time.localtime(timespan.stop)
                    if page_name == 'archive-year':
                        filename = os.path.join(destination_dir, "%4d.js") % start_tt[0]
                        period_type = 'historical'
                        interval = f"year{start_tt[0]:4d}"
                        page = f"{start_tt[0]:4d}"
                    elif page_name == 'archive-month':
                        filename = os.path.join(destination_dir, "%4d-%02d.js") % (start_tt[0], start_tt[1])
                        period_type = 'historical'
                        interval = f"month{start_tt[0]:4d}{start_tt[1]:02d}"
                        page = f"{start_tt[0]:4d}-{start_tt[1]:02d}"
                    elif page_name == 'multiyear':
                        filename = os.path.join(destination_dir, page_name + '.js')
                        period_type = ''
                        interval = 'year'
                        page = page_name
                    elif page_name == 'multiyear':
                        filename = os.path.join(destination_dir, page_name + '.js')
                        period_type = ''
                        interval = 'year'
                        page = page_name
                    elif page_name == 'debug':
                        filename = os.path.join(destination_dir, page_name + '.js')
                        period_type = 'active'
                        interval = self.skin_dict['Extras']['pages']['debug'].get('simulate_interval', 'last24hours')
                        page = page_name
                    else:
                        filename = os.path.join(destination_dir, page_name + '.js')
                        period_type = 'active'
                        interval = page_name
                        page = page_name

                    if self._skip_generation(self.skin_dict.get('ChartGenerator'), timespan, None, period_type, filename, stop_ts):
                        continue

                    chart = self._gen_charts(filename, page_name, interval, page)
                    chart = '\n' + chart + '\n'
                    byte_string = chart.encode('utf8')

                    try:
                        # Write to a temporary file first
                        tmpname = filename + '.tmp'
                        # Open it in binary mode. We are writing a byte-string, not a string
                        with open(tmpname, mode='wb') as temp_file:
                            temp_file.write(byte_string)
                        # Now move the temporary file into place
                        os.rename(tmpname, filename)
                    finally:
                        try:
                            os.unlink(tmpname)
                        except OSError:
                            pass

    def _get_obs_unit_label(self, observation):
        # For now, return label for first observations unit. ToDo: possibly change to return all?
        return get_label_string(self.formatter, self.converter, observation, plural=False)

    def _get_unit_label(self, unit):
        return self.formatter.get_label_string(unit, plural=False)

    def _set_chart_defs(self):
        self.chart_defs = configobj.ConfigObj()
        for chart in self.skin_dict['Extras']['chart_definitions'].sections:
            self.chart_defs[chart] = weeutil.config.deep_copy(self.skin_dict['Extras']['chart_definitions'][chart])
            if 'polar' in self.skin_dict['Extras']['chart_definitions'][chart]:
                coordinate_type = 'polar'
            elif 'grid' in self.skin_dict['Extras']['chart_definitions'][chart]:
                coordinate_type = 'grid'
            else:
                coordinate_type = 'grid'
            # ToDo: fix here
            self.chart_defs[chart].merge(self.chart_defaults.get(coordinate_type, {}))

            weewx_options = {}
            weewx_options['aggregate_type'] = 'avg'

            if 'weewx' not in self.chart_defs[chart]:
                self.chart_defs[chart]['weewx'] = {}
            obs = next(iter(self.skin_dict['Extras']['chart_definitions'][chart]['series']))
            observation = obs
            if 'weewx' in self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs]:
                observation = self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs]['weewx'].get('observation', obs)
            if 'yAxis' not in self.chart_defs[chart]['weewx']:
                self.chart_defs[chart]['weewx']['yAxis'] = {}
            self.chart_defs[chart]['weewx']['yAxis']['0'] = {}
            self.chart_defs[chart]['weewx']['yAxis']['0']['weewx'] = {}
            self.chart_defs[chart]['weewx']['yAxis']['0']['weewx']['obs'] = observation

            if self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs].get('weewx', False):
                self.chart_defs[chart]['weewx']['yAxis']['0']['weewx']['unit'] = \
                    self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs]['weewx'].get('unit', None)

            # ToDo: rework
            for value in self.skin_dict['Extras']['chart_definitions'][chart]['series']:
                observation = value
                if 'weewx' in self.skin_dict['Extras']['chart_definitions'][chart]['series'][value]:
                    observation = self.skin_dict['Extras']['chart_definitions'][chart]['series'][value]['weewx'].get('observation', value)

                charttype = self.skin_dict['Extras']['chart_definitions'][chart]['series'][value].get('type', None)
                if not charttype:
                    charttype = "'line'"
                    self.chart_defs[chart]['series'][value]['type'] = charttype

                y_axis_index = self.skin_dict['Extras']['chart_definitions'][chart]['series'][value].get('yAxisIndex', None)
                if y_axis_index is not None:
                    if y_axis_index not in self.chart_defs[chart]['weewx']['yAxis']:
                        self.chart_defs[chart]['weewx']['yAxis'][y_axis_index] = {}
                    if 'weewx' not in self.chart_defs[chart]['weewx']['yAxis'][y_axis_index]:
                        self.chart_defs[chart]['weewx']['yAxis'][y_axis_index]['weewx'] = {}
                    self.chart_defs[chart]['weewx']['yAxis'][y_axis_index]['weewx']['obs'] = observation
                    if self.skin_dict['Extras']['chart_definitions'][chart]['series'][value].get('weewx', False):
                        self.chart_defs[chart]['weewx']['yAxis'][y_axis_index]['weewx']['unit'] = \
                            self.skin_dict['Extras']['chart_definitions'][chart]['series'][value]['weewx'].get('unit', None)

                self.chart_defs[chart]['series'][value].merge((self.chart_series_defaults.get(coordinate_type, {}).get(charttype, {})))
                weewx_options['observation'] = observation
                if 'weewx' not in self.chart_defs[chart]['series'][value]:
                    self.chart_defs[chart]['series'][value]['weewx'] = {}
                weeutil.config.conditional_merge(self.chart_defs[chart]['series'][value]['weewx'], weewx_options)

    def _gen_charts(self, filename, page, interval, page_name):
        start_time = time.time()
        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        page_series_type = self.skin_dict['Extras']['page_definition'][page].get('series_type', 'single')

        chart_final = '\n'
        chart_final += '/* jas ' + VERSION + ' ' + str(self.gen_time) + ' */\n'
        chart_final += 'utc_offset = ' + str(self.utc_offset) + ';\n'

        chart_final += 'function simpleTooltipFormatter(args) {\n'
        chart_final += '  dateTime = moment.unix(args[0].axisValue/1000).utcOffset(utc_offset).format(dateTimeFormat[lang].chart[aggregate_interval].toolTipX);\n'
        chart_final += '  let tooltip = `<div>${dateTime}</div> `;\n'
        chart_final += '\n'
        chart_final += '  args.forEach(({ color, seriesName, value }) => {\n'
        chart_final += '    value = value[1] ? Number(value[1]).toLocaleString(lang) : value[1];\n'
        chart_final += '    tooltip += `<div style="color: ${color};">${seriesName} ${value}</div>`;\n'
        chart_final += '  });\n'
        chart_final += '  return tooltip;\n'
        chart_final += '}\n'
        chart_final += '\n'
        chart_final += 'function setupCharts() {\n'
        chart_final += "  ordinateNames = ['" + "', '".join(self.ordinate_names) + "'];\n"
        if self.skin_dict['Extras']['pages'][page].get('windRose', None) is not None:
            chart_final += "  windRangeLegend = " + self._get_wind_range_legend() + ";\n"
        chart_final += "\n"

        chart2 = ""
        chart3 = "  index = 0;\n"
        charts = self.skin_dict['Extras']['chart_definitions']
        for chart in self.skin_dict['Extras']['pages'][page]:
            if chart in charts.sections:
                chart_data_binding = charts[chart].get('weewx', {}).get('data_binding', skin_data_binding)
                chart_series_type = self.skin_dict['Extras']['pages'][page][chart].get('series_type')

                if chart_series_type and chart_series_type == 'mqtt':
                    series_type = chart_series_type
                else:
                    if chart_series_type and chart_series_type != 'mqtt':
                        logerr("only mqtt supported")
                    series_type = page_series_type

                chart_def = copy.deepcopy(self.chart_defs[chart])
                if 'polar' not in chart_def:
                    weeutil.config.conditional_merge(chart_def, self.skin_dict['Extras']['chart_defaults']['series_type'].get(series_type, {}))

                # for now, do not support overriding chart options by page
                # If this was supported, this would make caching the javascript more complicated
                # And possibly less useful
                # The workaround is to define a specific chart for the page
                #self.charts_def[chart].merge(self.skin_dict['Extras']['pages'][page][chart])

                chart_js = "  var option = {\n"
                chart2 += self._gen_series('    ', page, chart, chart_js, series_type, chart_def['series'], chart_data_binding)

                if chart not in self.charts_javascript:
                    self.charts_javascript[chart] = {}
                    self.charts_javascript[chart][series_type] = self._gen_chart_common(chart, chart_def)
                elif series_type not in self.charts_javascript[chart]:
                    self.charts_javascript[chart][series_type] = self._gen_chart_common(chart, chart_def)

                chart2 += self.charts_javascript[chart][series_type]

                chart2 += "  };\n"
                chart2 += "\n"
                chart2 += "  pageIndex['" + chart + page_name + "'] = Object.keys(pageIndex).length;\n"
                chart2 += "  var telem = document.getElementById('" + chart + page_name + "');\n"
                chart2 += "  var " + chart + "chart = echarts.init(document.getElementById('" + chart + page_name + "'));\n"
                chart2 += "  " + chart + "chart.setOption(option);\n"

                chart2 += "  pageChart = {};\n"

                if series_type == 'mqtt':
                    chart2 += 'pageChart.option = null;\n'
                    chart2 += 'pageChart.series = [];\n'
                    for obs in chart_def['series']:
                        chart2 += 'seriesData = {};\n'
                        chart2 += 'seriesData.obs = "' + obs + '";\n'
                        name = chart_def['series'][obs].get('name', None)
                        if name is not None:
                            chart2 += 'seriesData.name = "' + name + '";\n'
                        else:
                            chart2 += 'seriesData.name = null;\n'
                        chart2 += 'pageChart.series.push(seriesData);\n'
                elif series_type == 'multiple':
                    chart3 += "  series_option = {\n"
                    chart3 += "    series: [\n"
                    for obs in chart_def['series']:
                        aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                        obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        chart3 += "      {name: " + chart_def['series'][obs].get('name', 'getLabel(' + "'" + obs + "')") + ",\n"
                        chart3 += "       data: [\n"
                        (start_year, end_year) = self._get_range(self.skin_dict['Extras']['pages'][page].get('start', None),
                                                                 self.skin_dict['Extras']['pages'][page].get('end', None),
                                                                 chart_data_binding)
                        for year in range(start_year, end_year):
                            chart3 += "               ...year" + str(year) + "_" + aggregate_type \
                                      + "." + chart_def['series'][obs]['weewx']['observation'] + "_"  + obs_data_binding + ",\n"
                        chart3 += "             ]},\n"
                    chart3 += "  ]};\n"
                    chart3 += "  pageCharts[index].chart.setOption(series_option);\n"
                    chart3 += "  pageCharts[index].option = series_option;\n"
                    chart2 += "pageChart.def = option;\n"
                elif series_type == 'comparison':
                    chart3 += "  series_option = {\n"
                    chart3 += "    series: [\n"
                    obs = next(iter(chart_def['series']))
                    obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                    aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                    (start_year, end_year) = self._get_range(self.skin_dict['Extras']['pages'][page].get('start', None),
                                                             self.skin_dict['Extras']['pages'][page].get('end', None),
                                                             chart_data_binding)
                    for year in range(start_year, end_year):
                        chart3 += "      {name: '" + str(year) + "',\n"
                        chart3 += "       data: year" + str(year) + "_" + aggregate_type \
                                + "." + obs + "_"  + obs_data_binding \
                                + ".map(arr => [moment.unix(arr[0] / 1000).utcOffset(" + str(self.utc_offset) \
                                + ").format(dateTimeFormat[lang].chart.yearToYearXaxis), arr[1]])},\n"
                    chart3 += "  ]};\n"
                    chart3 += "  pageCharts[index].chart.setOption(series_option);\n"
                    chart3 += "  pageCharts[index].option = series_option;\n"
                    chart2 += "pageChart.def = option;\n"
                else:
                    chart3 += "  series_option = {\n"
                    chart3 += "    series: [\n"
                    for obs in chart_def['series']:
                        aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                        obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        unit_name = chart_def['series'][obs].get('weewx', {}).get('unit', None)
                        obs_data_unit = ""
                        if unit_name is not None:
                            obs_data_unit = "_" + unit_name
                        chart3 += "      {name: " + chart_def['series'][obs].get('name', "getLabel('" + obs + "')") + ",\n"
                        chart3 += "       data: " \
                                + interval + "_" + aggregate_type \
                                + "." + chart_def['series'][obs]['weewx']['observation'] + "_"  + obs_data_binding + obs_data_unit \
                                + "},\n"
                    chart3 += "  ]};\n"
                    chart3 += "  pageCharts[index].chart.setOption(series_option);\n"
                    chart3 += "  pageCharts[index].option = series_option;\n"
                    chart2 += "  pageChart.def = option;\n"

                chart3 += "  index += 1;\n"

                chart2 += "  pageChart.chart = " + chart + "chart;\n"
                chart2 += "  pageCharts.push(pageChart);\n"
                chart2 += "\n"

        chart2 += "}\n"
        chart2 += "function updateChartData() {\n"
        chart2 += chart3
        chart2 += "}\n"
        chart_final += chart2

        elapsed_time = time.time() - start_time
        log_msg = "Generated " + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return chart_final


    def _gen_series(self, indent, page, chart, chart_js, series_type, value, chart_data_binding):
        chart2 = chart_js
        if isinstance(value, dict):
            chart2 += indent + "series: [\n"

            if series_type == 'comparison':
                obs = next(iter(value))
                (start_year, end_year) = self._get_range(self.skin_dict['Extras']['pages'][page].get('start', None),
                                                            self.skin_dict['Extras']['pages'][page].get('end', None),
                                                            chart_data_binding)
                for year in range(start_year, end_year):
                    chart2 += indent + " {\n"
                    chart2 += "    name: '" + str(year) + "',\n"
                    chart2 = self._iterdict(indent + '  ', chart2, value[obs])
                    chart2 += indent + "  },\n"
            else:
                for obs in value:
                    aggregate_type = self.chart_defs[chart]['series'][obs]['weewx']['aggregate_type']
                    aggregate_interval = self.skin_dict['Extras']['page_definition'][page].get('aggregate_interval', {}) \
                                        .get(aggregate_type, 'none')

                    # set the aggregate_interval at the beginning of the chart definition, so it can be used in the chart
                    # Note, this means the last observation's aggregate type will be used to determine the aggregate interval
                    if series_type == 'multiple':
                        chart2 = "  aggregate_interval = 'multiyear'\n" + chart2
                    elif series_type == 'mqtt':
                        chart2 = "  aggregate_interval = 'mqtt'\n" + chart2
                    else:
                        chart2 = "  aggregate_interval = '" + aggregate_interval + "'\n" + chart2

                    chart2 += indent + "{\n"
                    chart2 = self._iterdict(indent + '  ', chart2, value[obs])

                    chart2 += indent + "},\n"

            chart2 += indent +"],\n"
        else:
            chart2 += indent + 'series' + ": " + value + ",\n"
        return chart2

    def _iterdict(self, indent, chart_js, dictionary):
        chart2 = chart_js
        for key, value in dictionary.items():
            if isinstance(value, dict):
                if key == 'weewx':
                    continue
                if key == 'series':
                    continue
                else:
                    chart2 += indent + key + ":" + " {\n"
                    chart2 = self._iterdict(indent + '  ', chart2, value)
                    chart2 += indent + "},\n"
            else:
                chart2 += indent + key + ": " + value + ",\n"
        return chart2

    def _gen_chart_common(self, chart, chart_def):
        chart_js =''
        chart2 = ''
        chart_temp = self._iterdict('    ', chart_js, chart_def)
        chart2 += chart_temp

        # ToDo: do not hard code 'grid'
        if 'polar' in self.skin_dict['Extras']['chart_definitions'][chart]:
            coordinate_type = 'polar'
        elif 'grid' in self.skin_dict['Extras']['chart_definitions'][chart]:
            coordinate_type = 'grid'
        else:
            coordinate_type = 'grid'

        default_grid_properties = self.skin_dict['Extras']['chart_defaults'].get('properties', {}).get('grid', None)
        if 'yAxis' not in chart_def and coordinate_type == 'grid':
            chart2 += '    yAxis: [\n'
            for i in range(0, len(chart_def['weewx']['yAxis'])):
                i_str = str(i)
                y_axis_default = copy.deepcopy(default_grid_properties['yAxis'])
                if i_str in chart_def['weewx']['yAxis']:
                    y_axis_default.merge(chart_def['weewx']['yAxis'][str(i)])
                    chart2 += '    {\n'

                    if 'name' in y_axis_default and y_axis_default['name'] == 'weewx_unit_label':
                        unit_name = chart_def['weewx']['yAxis'][i_str]['weewx'].get('unit', None)
                        if unit_name is not None:
                            y_axis_label = self._get_unit_label(unit_name)
                        else:
                            y_axis_label = self._get_obs_unit_label( chart_def['weewx']['yAxis'][i_str]['weewx']['obs'])

                        chart2 += "      name:' " + y_axis_label + "',\n"
                        del y_axis_default['name']

                chart2 += self._iterdict('      ', '', y_axis_default)
                chart2 += '    },\n'
            chart2 += '  ],\n'

        return chart2

    def _get_wind_range_legend(self):
        wind_speed_unit = self.skin_dict["Units"]["Groups"]["group_speed"]
        wind_speed_unit_label = self.skin_dict["Units"]["Labels"][wind_speed_unit]
        low_range = self.wind_ranges[wind_speed_unit][0]
        high_range = self.wind_ranges[wind_speed_unit][len(self.wind_ranges[wind_speed_unit]) - 1]
        wind_range_legend = F"['<{low_range} {wind_speed_unit_label}', "
        for high_range in self.wind_ranges[wind_speed_unit][1:]:
            wind_range_legend += F"'{low_range}-{high_range} {wind_speed_unit_label}', "
            low_range = high_range

        wind_range_legend += F"'>{high_range} {wind_speed_unit_label}']"
        return wind_range_legend

    def _get_range(self, start, end, data_binding):
        dbm = self.db_binder.get_manager(data_binding=data_binding)
        first_year = int(datetime.datetime.fromtimestamp(dbm.firstGoodStamp()).strftime('%Y'))
        last_year = int(datetime.datetime.fromtimestamp(dbm.lastGoodStamp()).strftime('%Y'))

        if start is None:
            start_year = first_year
        elif start[:1] == "+":
            start_year = first_year + int(start[1:])
        elif start[:1] == "-":
            start_year = last_year - int(start[1:])
        else:
            start_year = int(start)

        if end is None:
            end_year = last_year + 1
        else:
            end_year = int(end) + 1

        return (start_year, end_year)

class DataGenerator(JASGenerator):
    """ Generate the data used by the JAS skin. """
    def __init__(self, config_dict, skin_dict, *args, **kwargs):
        """Initialize an instance of DataGenerator"""
        JASGenerator.__init__(self, config_dict, skin_dict, *args, **kwargs)

        self.formatter = weewx.units.Formatter.fromSkinDict(skin_dict)
        self.converter = weewx.units.Converter.fromSkinDict(skin_dict)

        report_dict = self.config_dict.get('StdReport', {})
        self.unit_system = self.skin_dict.get('unit_system', 'us').upper()

        now = time.time()
        self.utc_offset = (datetime.datetime.fromtimestamp(now) -
                           datetime.datetime.utcfromtimestamp(now)).total_seconds()/60

        self.wind_ranges = {}
        self.wind_ranges['mile_per_hour'] = [1, 4, 8, 13, 19, 25, 32]
        self.wind_ranges['mile_per_hour2'] = [1, 4, 8, 13, 19, 25, 32]
        self.wind_ranges['km_per_hour'] = [.5, 6, 12, 20, 29, 39, 50]
        self.wind_ranges['km_per_hour2'] = [.5, 6, 12, 20, 29, 39, 50]
        self.wind_ranges['meter_per_second'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        self.wind_ranges['meter_per_second2'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        self.wind_ranges['knot'] = [1, 4, 7, 11, 17, 22, 28]
        self.wind_ranges['knot2'] = [1, 4, 7, 11, 17, 22, 28]
        self.wind_ranges_count = 7

        self.wind_observations = ['windCompassAverage', 'windCompassMaximum',
                                  'windCompassRange0', 'windCompassRange1', 'windCompassRange2',
                                  'windCompassRange3', 'windCompassRange4', 'windCompassRange5', 'windCompassRange6']

        html_root = self.skin_dict.get('HTML_ROOT',
                                       report_dict.get('HTML_ROOT', 'public_html'))

        latitude = self.config_dict['Station']['latitude']
        longitude = self.config_dict['Station']['longitude']

        html_root = os.path.join(self.config_dict['WEEWX_ROOT'], html_root)
        self.html_root = html_root
        self.mkdir_p(os.path.join(self.html_root, 'data'))

        forecast_filename = 'forecast.json'

        forecast_endpoint = 'https://api.aerisapi.com/forecasts/'

        current_filename = 'current.json'
        current_endpoint = 'https://api.aerisapi.com/observations/'

        self.forecast_filename = os.path.join(self.html_root, 'data', forecast_filename)

        self.current_filename = os.path.join(self.html_root, 'data', current_filename)

        self.raw_forecast_data_file = os.path.join(
            self.html_root, 'data', 'raw.forecast.json')

        client_id = self.skin_dict['Extras'].get('client_id')
        if client_id:
            client_secret = self.skin_dict['Extras']['client_secret']
            self.forecast_url = F"{forecast_endpoint}{latitude},{longitude}?"
            self.forecast_url += F"format=json&filter=day&limit=7&client_id={client_id}&client_secret={client_secret}"

            self.current_url = F"{current_endpoint}{latitude},{longitude}?"
            self.current_url += F"&format=json&filter=allstations&limit=1&client_id={client_id}&client_secret={client_secret}"

        self.observations, self.aggregate_types = self._get_observations_information()

        self.data_current = None
        if to_bool(self.skin_dict['Extras'].get('display_aeris_observation', False)):
            self.data_current = self._get_current_obs()

        self.data_forecast = None
        if self._check_forecast():
            self.data_forecast = self._get_forecasts()

    def _call_api(self, url):
        request = Request(url)
        response = None
        try:
            response = urlopen(request)
            body = response.read()
            response.close()
        except HTTPError as exception:
            body = exception.read()
            exception.close()
        except URLError as exception:
            logerr(exception)
            body = "{}"

        data = json.loads(body)

        if 'success' in data and data['success']:
            return data['response']
        else:
            if 'error' in data:
                logerr(F"An error occurred: {data['error']['description']}")
            else:
                logerr("Unknown error")
            return {}

    def _get_forecasts(self):
        now = time.time()
        current_hour = int(now - now % 3600)
        if not os.path.isfile(self.forecast_filename):
            forecast_data = self._retrieve_forecasts(current_hour)
        else:
            with open(self.forecast_filename, "r", encoding="utf-8") as forecast_fp:
                forecast_data = json.load(forecast_fp)

            if current_hour > forecast_data['generated']:
                forecast_data = self._retrieve_forecasts(current_hour)

        return forecast_data['forecasts']

    def _retrieve_forecasts(self, current_hour):
        forecast_observations = {
            'US' : {
                'temp_max': 'maxTempF',
                'temp_min': 'minTempF',
                'temp_unit': 'F',
                'wind_conversion': 1,
                'wind_max': 'windSpeedMaxMPH',
                'wind_min': 'windSpeedMinMPH',
                'wind_unit': 'mph',
            },
            'METRIC' : {
                'temp_max': 'maxTempC',
                'temp_min': 'minTempC',
                'temp_unit': 'C',
                'wind_conversion': 1,
                'wind_max': 'windSpeedMaxKPH',
                'wind_min': 'windSpeedMinKPH',
                'wind_unit': 'km/h',
            },
            'METRICWX' : {
                'temp_max': 'maxTempC',
                'temp_min': 'minTempC',
                'temp_unit': 'C',
                'wind_conversion': 1000/3600,
                'wind_max': 'windSpeedMaxKPH',
                'wind_min': 'windSpeedMinKPH',
                'wind_unit': 'm/s',
            },

        }

        wind_decimals = to_int(self.skin_dict['Extras'].get('forecast_wind_decimals', 2))
        data = self._call_api(self.forecast_url)
        with open(self.raw_forecast_data_file, "w", encoding="utf-8") as raw_forecast_fp:
            json.dump(data, raw_forecast_fp, indent=2)

        forecast_data = {}
        forecast_data['forecasts'] = []

        if data:
            forecast_data['generated'] = current_hour
            forecasts = []
            periods = data[0]['periods']

            for period in periods:
                forecast = {}
                forecast['observation'] = self._get_observation_text(period['weatherPrimaryCoded'])
                forecast['timestamp'] = period['timestamp']
                day_of_week = (int(datetime.datetime.fromtimestamp(period['timestamp']).strftime("%w")) + 6) % 7
                day_of_week_key = 'forecast_week_day' + str(day_of_week)
                forecast['day'] = "'" + day_of_week_key + "'"
                forecast['temp_min'] = period[forecast_observations[self.unit_system]['temp_min']]
                forecast['temp_max'] = period[forecast_observations[self.unit_system]['temp_max']]
                forecast['temp_unit'] = forecast_observations[self.unit_system]['temp_unit']
                forecast['rain'] = period['pop']
                forecast['wind_min'] = round(period[forecast_observations[self.unit_system]['wind_min']] \
                                        * forecast_observations[self.unit_system]['wind_conversion'], wind_decimals)
                forecast['wind_max'] = round(period[forecast_observations[self.unit_system]['wind_max']] \
                                        * forecast_observations[self.unit_system]['wind_conversion'], wind_decimals)
                forecast['wind_unit'] = forecast_observations[self.unit_system]['wind_unit']
                forecasts.append(forecast)

            forecast_data['forecasts'] = forecasts
            with open(self.forecast_filename, "w", encoding="utf-8") as forecast_fp:
                json.dump(forecast_data, forecast_fp, indent=2)
        return forecast_data

    def _get_current(self, obs_type, data_binding, unit_name=None):
        db_manager = self.db_binder.get_manager(data_binding=data_binding)

        # Start of code stolen from tags.py CurrentObj __getattr__
        # The WeeWx method was using the 'current' record to perform the XType calculation.
        # It does not gave the necessary data.
        # This always uses data from the database.
        # Get the record for this timestamp from the database
        record = db_manager.getRecord(self.timespan.stop, max_delta=None)
        # If there was no record at that timestamp, it will be None. If there was a record,
        # check to see if the type is in it.

        if not record or obs_type in record:
            # If there was no record, then the value of the ValueTuple will be None.
            # Otherwise, it will be value stored in the database.
            value_tuple = weewx.units.as_value_tuple(record, obs_type)
        else:
            # Couldn't get the value out of the record. Try the XTypes system.
            try:
                value_tuple = weewx.xtypes.get_scalar(obs_type, record, db_manager)
            except (weewx.UnknownType, weewx.CannotCalculate):
                # Nothing seems to be working. It's an unknown type.
                value_tuple = weewx.units.UnknownType(obs_type)

        # Finally, return a ValueHelper
        current_value =  weewx.units.ValueHelper(value_tuple, 'current', self.formatter, self.converter)
        # End of stolen code

        if unit_name != 'default':
            return getattr(current_value, unit_name)
        else:
            return current_value

    def _get_observations_information(self):
        observations = {}
        aggregate_types = {}
        # ToDo: isn't this done in the init method?
        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        charts = self.skin_dict.get('Extras', {}).get('chart_definitions', {})

        pages = self.skin_dict.get('Extras', {}).get('pages', {})
        for page in pages:
            if not self.skin_dict['Extras']['pages'][page].get('enable', True):
                continue
            for chart in pages[page].sections:
                if chart in charts:
                    chart_data_binding = charts[chart].get('weewx', {}).get('data_binding', skin_data_binding)
                    series = charts[chart].get('series', {})
                    for obs in series:
                        weewx_options = series[obs].get('weewx', {})
                        observation = weewx_options.get('observation', obs)
                        obs_data_binding = series[obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        if observation not in self.wind_observations:
                            if observation not in observations:
                                observations[observation] = {}
                                observations[observation]['aggregate_types'] = {}

                            aggregate_type = weewx_options.get('aggregate_type', 'avg')
                            if aggregate_type not in observations[observation]['aggregate_types']:
                                observations[observation]['aggregate_types'][aggregate_type] = {}

                            if obs_data_binding not in observations[observation]['aggregate_types'][aggregate_type]:
                                observations[observation]['aggregate_types'][aggregate_type][obs_data_binding] = {}

                            unit = weewx_options.get('unit', 'default')
                            observations[observation]['aggregate_types'][aggregate_type][obs_data_binding][unit] = {}
                            aggregate_types[aggregate_type] = {}

        minmax_observations = self.skin_dict.get('Extras', {}).get('minmax', {}).get('observations', {})
        minmax_data_binding = self.skin_dict.get('Extras', {}).get('minmax', {}).get('data_binding', skin_data_binding)
        if minmax_observations:
            for observation in self.skin_dict['Extras']['minmax']['observations'].sections:
                data_binding = minmax_observations[observation].get('data_binding', minmax_data_binding)
                if observation not in self.wind_observations:
                    unit = minmax_observations[observation].get('unit', 'default')
                    if observation not in observations:
                        observations[observation] = {}
                        observations[observation]['aggregate_types'] = {}

                    if 'min' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['min'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['min']:
                        observations[observation]['aggregate_types']['min'][data_binding] = {}
                    observations[observation]['aggregate_types']['min'][data_binding][unit] = {}
                    aggregate_types['min'] = {}
                    if 'max' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['max'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['max']:
                        observations[observation]['aggregate_types']['max'][data_binding] = {}
                    observations[observation]['aggregate_types']['max'][data_binding][unit] = {}
                    aggregate_types['max'] = {}

        if 'thisdate' in self.skin_dict['Extras']:
            thisdate_observations = self.skin_dict.get('Extras', {}).get('thisdate', {}).get('observations', {})
            thisdate_data_binding = self.skin_dict.get('Extras', {}).get('thisdate', {}).get('data_binding', skin_data_binding)
            for observation in  self.skin_dict['Extras']['thisdate']['observations'].sections:
                data_binding = thisdate_observations[observation].get('data_binding', thisdate_data_binding)
                if observation not in self.wind_observations:
                    unit = thisdate_observations[observation].get('unit', 'default')
                    if observation not in observations:
                        observations[observation] = {}
                        observations[observation]['aggregate_types'] = {}

                    if 'min' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['min'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['min']:
                        observations[observation]['aggregate_types']['min'][data_binding] = {}
                    observations[observation]['aggregate_types']['min'][data_binding][unit] = {}
                    aggregate_types['min'] = {}
                    if 'max' not in observations[observation]['aggregate_types']:
                        observations[observation]['aggregate_types']['max'] = {}
                    if data_binding not in observations[observation]['aggregate_types']['max']:
                        observations[observation]['aggregate_types']['max'][data_binding] = {}
                    observations[observation]['aggregate_types']['max'][data_binding][unit] = {}
                    aggregate_types['max'] = {}

        return observations, aggregate_types

    def _check_forecast(self):
        pages = self.skin_dict.get('Extras', {}).get('pages', {})
        for page in pages:
            if self.skin_dict['Extras']['pages'][page].get('enable', True) and 'forecast' in self.skin_dict['Extras']['pages'][page].sections:
                return True

        return False

    def _get_observation_text(self, coded_weather):
        cloud_codes = ["CL", "FW", "SC", "BK", "OV",]

        coverage_code = coded_weather.split(":")[0]
        intensity_code = coded_weather.split(":")[1]
        weather_code = coded_weather.split(":")[2]
        observation_codes = []

        if weather_code in cloud_codes:
            cloud_code_key = 'cloud_code_' + weather_code
            observation_codes.append(cloud_code_key)
        else:
            if coverage_code:
                coverage_code_key = 'coverage_code_' + coverage_code
                observation_codes.append(coverage_code_key)
            if intensity_code:
                intensity_code_key = 'intensity_code_' + intensity_code
                observation_codes.append(intensity_code_key)

            weather_code_key = 'weather_code_' + weather_code
            observation_codes.append(weather_code_key)

        return observation_codes

    def _get_timespan(self, time_period, time_stamp):

        if time_period == 'day':
            return weeutil.weeutil.archiveDaySpan(time_stamp)

        if time_period == 'week':
            #week_start = to_int(self.option_dict.get('week_start', 6))
            week_start = 6
            return weeutil.weeutil.archiveWeekSpan(time_stamp, startOfWeek=week_start, weeks_ago=0)

        if time_period == 'month':
            return weeutil.weeutil.archiveMonthSpan(time_stamp)

        if time_period == 'year':
            return weeutil.weeutil.archiveYearSpan(time_stamp)

        if time_period == 'yesterday':
            return weeutil.weeutil.archiveDaySpan(time_stamp, days_ago=1)

        if time_period == 'last24hours':
            return TimeSpan(time_stamp - 86400, time_stamp)

        if time_period == 'last7days':
            start_date = datetime.date.fromtimestamp(time_stamp) - datetime.timedelta(days=7)
            start_timestamp = time.mktime(start_date.timetuple())
            return TimeSpan(start_timestamp, time_stamp)

        if time_period == 'last366days':
            start_date = datetime.date.fromtimestamp(time_stamp) - datetime.timedelta(days=366)
            start_timestamp = time.mktime(start_date.timetuple())
            return TimeSpan(start_timestamp, time_stamp)

        if time_period == 'last31days':
            start_date = datetime.date.fromtimestamp(time_stamp) - datetime.timedelta(days=31)
            start_timestamp = time.mktime(start_date.timetuple())
            return TimeSpan(start_timestamp, time_stamp)

        raise AttributeError(time_period)

    # Create time stamps by aggregation time for the end of interval
    # For example: endTimestamp_min, endTimestamp_max
    def _gen_interval_end_timestamp(self, page_data_binding, interval_name, page_definition_name):
        data = ''
        for aggregate_type in self.skin_dict['Extras']['page_definition'][page_definition_name]['aggregate_interval']:
            aggregate_interval = self.skin_dict['Extras']['page_definition'][page_definition_name]['aggregate_interval'][aggregate_type]
            if aggregate_interval == 'day':
                end_timestamp =(self._get_timespan_binder(interval_name, page_data_binding).end.raw // 86400 * 86400 - (self.utc_offset * 60)) * 1000
            elif aggregate_interval == 'hour':
                end_timestamp =(self._get_timespan_binder(interval_name, page_data_binding).end.raw // 3600 * 3600 - (self.utc_offset * 60)) * 1000
            else:
                end_timestamp =(self._get_timespan_binder(interval_name, page_data_binding).end.raw // 60 * 60 - (self.utc_offset * 60)) * 1000

            data +=  "  pageData.endTimestamp_" + aggregate_type +  " = " +  str(end_timestamp) + ";\n"

        return data

    def _get_timespan_binder(self, time_period, data_binding):
        return TimespanBinder(self._get_timespan(time_period, self.timespan.stop),
                                     self.db_binder.bind_default(data_binding),
                                     data_binding=data_binding,
                                     context=time_period,
                                     formatter=self.formatter,
                                     converter=self.converter)

    def _get_aggregate(self, observation, data_binding, time_period, aggregate_type, unit_name = None, rounding=2, add_label=False, localize=False):
        obs_binder = weewx.tags.ObservationBinder(
            observation,
            self._get_timespan(time_period, self.timespan.stop),
            self.db_binder.bind_default(data_binding),
            data_binding,
            time_period,
            self.formatter,
            self.converter,
        )

        data_aggregate_binder = getattr(obs_binder, aggregate_type)

        if unit_name != 'default':
            data = getattr(data_aggregate_binder, unit_name)
        else:
            data = data_aggregate_binder

        if rounding:
            return data.round(rounding).format(add_label=add_label, localize=localize)

        return data.format(add_label=add_label, localize=localize)

    def _get_wind_compass(self, data_binding=None, start_time=None, end_time=None):
        db_manager = self.db_binder.get_manager(data_binding=data_binding)
        # default is the last 24 hrs
        if not end_time:
            end_ts = db_manager.lastGoodStamp()
        else:
            end_ts = end_time

        if not start_time:
            start_ts = end_ts - 86400
        else:
            start_ts = start_time

        data_timespan = TimeSpan(start_ts, end_ts)

        # current day calculation
        #day_ts = int(timespan.stop - timespan.stop % age)


        start_vec_t1, stop_vec_t1, wind_speed_data_raw = weewx.xtypes.get_series(  # pylint: disable=unused-variable
            'windSpeed', data_timespan, db_manager)
        start_vec_t2, stop_vec_t2, wind_dir_data = weewx.xtypes.get_series(  # pylint: disable=unused-variable
            'windDir', data_timespan, db_manager)
        start_vec_t3, stop_vec_t3, wind_gust_data_raw = weewx.xtypes.get_series(  # pylint: disable=unused-variable
            'windGust', data_timespan, db_manager)

        wind_data = {}
        # the formatter has the names in a list in the correct order
        # with an additional 'N/A' at the end
        i = 0
        while i < len(self.formatter.ordinate_names) - 1:
            ordinate_name = self.formatter.ordinate_names[i]
            wind_data[ordinate_name] = {}
            wind_data[ordinate_name]['sum'] = 0
            wind_data[ordinate_name]['count'] = 0
            wind_data[ordinate_name]['max'] = 0
            wind_data[ordinate_name]['speed_data'] = []
            j = 0
            while j < self.wind_ranges_count:
                wind_data[ordinate_name]['speed_data'].append(0)
                j += 1
            i += 1

        i = 0
        wind_speed_data = self.converter.convert(wind_speed_data_raw)
        for wind_speed in wind_speed_data[0]:
            if wind_speed and wind_speed > 0:
                wind_unit = wind_speed_data[1]
                ordinate_name = self.formatter.to_ordinal_compass(
                    (wind_dir_data[0][i], wind_dir_data[1], wind_dir_data[2]))
                wind_data[ordinate_name]['sum'] += wind_speed
                wind_data[ordinate_name]['count'] += 1
                wind_gust_data = self.converter.convert(wind_gust_data_raw)
                if wind_gust_data[0][i] > wind_data[ordinate_name]['max']:
                    wind_data[ordinate_name]['max'] = wind_gust_data[0][i]

                j = 0
                for wind_range in self.wind_ranges[wind_unit]:
                    if wind_speed < wind_range:
                        wind_data[ordinate_name]['speed_data'][j] += 1
                        break
                    j += 1

            i += 1

        for ordinate_name, _  in wind_data.items():
            if wind_data[ordinate_name]['count'] > 0:
                wind_data[ordinate_name]['average'] = \
                    wind_data[ordinate_name]['sum'] / \
                    wind_data[ordinate_name]['count']
            else:
                wind_data[ordinate_name]['average'] = 0.0

        wind_compass_avg = []
        wind_compass_max = []
        wind_compass_speeds = []
        j = 0
        while j < self.wind_ranges_count:
            wind_compass_speeds.append([])
            j += 1

        for wind_ordinal_data, _ in wind_data.items():
            wind_compass_avg.append(wind_data[wind_ordinal_data]['average'])
            wind_compass_max.append(wind_data[wind_ordinal_data]['max'])

            i = 0
            for wind_x in wind_data[wind_ordinal_data]['speed_data']:
                wind_compass_speeds[i].append(wind_x)
                i += 1

        return wind_compass_avg, wind_compass_max, wind_compass_speeds

    def _get_series(self, observation, data_binding, time_period, aggregate_type=None, aggregate_interval=None, time_series='both', time_unit='unix_epoch', unit_name = None, rounding=2, jsonize=True):
        obs_binder = weewx.tags.ObservationBinder(
            observation,
            self._get_timespan(time_period, self.timespan.stop),
            self.db_binder.bind_default(data_binding),
            data_binding,
            time_period,
            self.formatter,
            self.converter,
        )

        data_series_helper = obs_binder.series(aggregate_type=aggregate_type, aggregate_interval=aggregate_interval, time_series=time_series, time_unit=time_unit)
        if unit_name != 'default':
            data2 = getattr(data_series_helper, unit_name)
        else:
            data2 = data_series_helper

        data3 = data2.round(rounding)
        if jsonize:
            return data3.json()

        return data3

    def _gen_aggregate_objects(self, interval, page_definition_name, interval_long_name):
        data = ""

        # Define the 'aggegate' objects to hold the data
        # For example: last7days_min = {}, last7days_max = {}
        for aggregate_type in self.aggregate_types:
            data += "  pageData." + interval_long_name + aggregate_type + " = {};\n"

        for observation, observation_items in self.observations.items():
            for aggregate_type, aggregate_type_items in observation_items['aggregate_types'].items():
                aggregate_interval = self.skin_dict['Extras']['page_definition'][page_definition_name]['aggregate_interval'].get(aggregate_type, None)
                interval_name = interval_long_name + aggregate_type
                for data_binding, data_binding_items in aggregate_type_items.items():
                    for unit_name in data_binding_items:
                        name_prefix = interval_name + "." + observation + "_"  + data_binding
                        name_prefix2 = interval_name + "_" + observation + "_"  + data_binding
                        if unit_name == "default":
                            pass
                        else:
                            name_prefix += "_" + unit_name
                            name_prefix2 += "_" + unit_name

                        array_name = name_prefix

                        if aggregate_interval is not None:
                            data += "  pageData." + array_name + " = " + self._get_series(observation, data_binding, interval, aggregate_type, aggregate_interval, 'start', 'unix_epoch_ms', unit_name, 2, True) + ";\n"
                        else:
                            # wind 'observation' is special see #87
                            if observation == 'wind':
                                if aggregate_type == 'max':
                                    weewx_observation = 'windGust'
                                else:
                                    weewx_observation = 'windSpeed'
                                #end if
                            else:
                                weewx_observation = observation
                            #end if
                            data += "  pageData." + array_name + " = " + self._get_series(weewx_observation, data_binding, interval, None, None, 'start', 'unix_epoch_ms', unit_name, 2, True) + ";\n"

        data += "\n"
        return data

    def _get_current_obs(self):
        now = time.time()
        current_hour = int(now - now % 3600)
        if not os.path.isfile(self.current_filename):
            current_data = self._retrieve_current(current_hour)
        else:
            with open(self.current_filename, "r", encoding="utf-8") as current_fp:
                current_data = json.load(current_fp)

            if current_hour > current_data['generated']:
                current_data = self._retrieve_current(current_hour)

        return current_data['current']

    def _retrieve_current(self, current_hour):
        data = self._call_api(self.current_url)

        current_data = {}
        current_data['current'] = {}
        current_data['current']['observation'] = ''

        if data:
            current_observation = data['ob']
            current_data['generated'] = current_hour
            current = {}

            current['observation'] = self._get_observation_text(current_observation['weatherPrimaryCoded'])

            current_data['current'] = current
            with open(self.current_filename, "w", encoding="utf-8") as current_fp:
                json.dump(current_data, current_fp, indent=2)

        return current_data

    def _check_forecast(self):
        pages = self.skin_dict.get('Extras', {}).get('pages', {})
        for page in pages:
            if to_bool(self.skin_dict['Extras']['pages'][page].get('enable', True)) and \
                'forecast' in self.skin_dict['Extras']['pages'][page].sections and \
                to_bool(self.skin_dict['Extras']['pages'][page]['forecast'].get('enable', True)):
                return True

        return False

    # Proof of concept - wind rose
    # Create data for wind rose chart
    def _gen_windrose(self, page_data_binding, interval_name, page_definition_name, interval_long_name):
        data = ''

        interval_start_seconds_global = self._get_timespan_binder(interval_name, page_data_binding).start.raw
        interval_end_seconds_global = self._get_timespan_binder(interval_name, page_data_binding).end.raw

        if self.skin_dict['Extras']['pages'][page_definition_name].get('windRose', None) is not None:
            avg_value, max_value, wind_directions = self._get_wind_compass(data_binding=page_data_binding, start_time=interval_start_seconds_global, end_time=interval_end_seconds_global) # need to match function signature pylint: disable=unused-variable
            i = 0
            for wind in wind_directions:
                data += "  pageData." + interval_long_name + "avg.windCompassRange"  + str(i) + "_" + page_data_binding + " = JSON.stringify(" +  str(wind) +  ");\n"
                i += 1

        return data

    def run(self):
        default_archive = self.db_binder.get_manager(self.data_binding)
        start_ts = default_archive.firstGoodStamp()
        if not start_ts:
            log.info('Skipping, cannot find start time')
            return

        if self.gen_ts:
            record = default_archive.getRecord(self.gen_ts)
            if record:
                stop_ts = record['dateTime']
            else:
                log.info('Skipping, generate time %s not in database', timestamp_to_string(self.gen_ts))
                return
        else:
            stop_ts = default_archive.lastGoodStamp()

        destination_dir = os.path.join(self.config_dict['WEEWX_ROOT'],
                                       self.skin_dict['HTML_ROOT'],
                                       'dataload')

        try:
            # Create the directory that is to receive the generated files.  If
            # it already exists an exception will be thrown, so be prepared to
            # catch it.
            os.makedirs(destination_dir)
        except OSError:
            pass

        for page_name in self.skin_dict['Extras']['pages'].sections:
            if self.skin_dict['Extras']['pages'].get('enable', True) and \
                page_name in self.skin_dict['Extras']['page_definition'] and \
                self.skin_dict['Extras']['page_definition'][page_name].get('series_type', 'single') == 'single':

                generate_interval = self.skin_dict['Extras']['page_definition'][page_name].get('generate_interval', None)
                if page_name in self.generator_dict:
                    _spangen = self.generator_dict[page_name]
                else:
                    _spangen = lambda start_ts, stop_ts: [weeutil.weeutil.TimeSpan(start_ts, stop_ts)]

                for timespan in _spangen(start_ts, stop_ts):
                    self.timespan = timespan
                    start_tt = time.localtime(timespan.start)
                    #stop_tt = time.localtime(timespan.stop)
                    if page_name == 'archive-year':
                        filename = os.path.join(destination_dir, "%4d.js") % start_tt[0]
                        period_type = 'historical'
                        time_period = 'year'
                        interval_long_name = f"year{start_tt[0]:4d}_"
                    elif page_name == 'archive-month':
                        filename = os.path.join(destination_dir, "%4d-%02d.js") % (start_tt[0], start_tt[1])
                        period_type = 'historical'
                        time_period = 'month'
                        interval_long_name = f"month{start_tt[0]:4d}{start_tt[1]:02d}_"
                    elif page_name == 'debug':
                        filename = os.path.join(destination_dir, page_name + '.js')
                        period_type = 'active'
                        time_period = self.skin_dict['Extras']['pages']['debug'].get('simulate_page', 'last24hours')
                        interval_long_name = self.skin_dict['Extras']['pages']['debug'].get('simulate_interval', 'last24hours') + '_'
                    else:
                        filename = os.path.join(destination_dir, page_name + '.js')
                        period_type = 'active'
                        time_period = page_name
                        interval_long_name = page_name + '_'

                    if self._skip_generation(self.skin_dict.get('DataGenerator'), timespan, generate_interval, period_type, filename, stop_ts):
                        continue

                    data = self._gen_data_load(filename, time_period, period_type, page_name, interval_long_name)
                    byte_string = data.encode('utf8')

                    try:
                        # Write to a temporary file first
                        tmpname = filename + '.tmp'
                        # Open it in binary mode. We are writing a byte-string, not a string
                        with open(tmpname, mode='wb') as temp_file:
                            temp_file.write(byte_string)
                        # Now move the temporary file into place
                        os.rename(tmpname, filename)
                    finally:
                        try:
                            os.unlink(tmpname)
                        except OSError:
                            pass

    def _gen_data_load(self, filename, interval, interval_type, page_definition_name, interval_long_name):
        start_time = time.time()

        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        page_data_binding = self.skin_dict['Extras']['pages'][page_definition_name].get('data_binding', skin_data_binding)
        data = ''
        data += '// the start\n'
        data += '/* jas ' + VERSION + ' ' + str(self.gen_time) + ' */\n'
        data += "pageData = {};\n"
        data += 'function ' + interval_long_name + 'dataLoad() {\n'
        data += '  traceStart = Date.now();\n'
        data += '        console.debug(Date.now().toString() + " dataLoad start");\n'
        if self.data_current:
            data += '  pageData.currentObservations = ["' + '", "'.join(self.data_current['observation']) + '"];\n'

        data += '  pageData.forecasts = [];\n'
        data += '\n'
        if self.data_forecast:
            for forecast in self.data_forecast:
                data += '  forecast = {};\n'
                data += '  forecast.timestamp = ' + str(forecast["timestamp"]) + ';\n'
                data += '  forecast.observation_codes = ["' + '", "'.join(forecast["observation"]) + '"];\n'
                data += '  forecast.day_code = ' + forecast["day"] + ';\n'
                data += '  forecast.temp_min = ' + str(forecast["temp_min"]) + ';\n'
                data += '  forecast.temp_max = ' + str(forecast["temp_max"]) + ';\n'
                data += '  forecast.temp_unit = "' + forecast["temp_unit"] + '";\n'
                data += '  forecast.rain = ' + str(forecast["rain"]) + ';\n'
                data += '  forecast.wind_min = ' + str(forecast["wind_min"]) + ';\n'
                data += '  forecast.wind_max = ' + str(forecast["wind_max"]) + ';\n'
                data += '  forecast.wind_unit = "' + forecast["wind_unit"] + '";\n'
                data += '  pageData.forecasts.push(forecast);\n'
                data += '\n'

        data += self._gen_data_load2(interval, interval_type, page_definition_name, skin_data_binding, page_data_binding)

        data += self._gen_aggregate_objects(interval, page_definition_name, interval_long_name)

        if self.skin_dict['Extras']['pages'][page_definition_name].get('current', None) is not None:
            data += self._gen_data_load3(skin_data_binding, interval)

        data += "\n"

        data += "\n"
        if self.skin_dict['Extras']['pages'][page_definition_name].get('windRose', None) is not None:
            data += self._gen_windrose(page_data_binding, interval, page_definition_name, interval_long_name)

        data += '        console.debug(Date.now().toString() + " dataLoad end");\n'
        data += "}\n"
        data += "\n"

        elapsed_time = time.time() - start_time
        log_msg = "Generated " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return data

    # Create the data used to display current conditions.
    # This data is only used when MQTT is not enabled.
    # This data is stored in a javascript object named 'current'.
    # 'current.header' is an object with the data for the header portion of this section.
    # 'current.observations' is a map. The key is the observation name, like 'outTemp'. The value is the data to populate the section.
    def _gen_data_load3(self, skin_data_binding, interval):
        data = ''

        current_data_binding = self.skin_dict['Extras']['current'].get('data_binding', skin_data_binding)
        interval_current = self.skin_dict['Extras']['current'].get('interval', interval)

        #data += 'var mqtt_enabled = false;\n'
        data += '  pageData.updateDate = ' + str(self._get_current('dateTime', data_binding=current_data_binding, unit_name='default').raw * 1000) + ';\n'
        if self.skin_dict['Extras']['current'].get('observation', False):
            data_binding = self.skin_dict['Extras']['current'].get('header_data_binding', current_data_binding)
            data += '  pageData.currentHeaderValue = "' + self._get_current(self.skin_dict['Extras']['current']['observation'], data_binding, 'default').format(add_label=False,localize=False) + '";\n'

        data += '  var currentData = {};\n'
        for observation in self.skin_dict['Extras']['current']['observations']:
            data_binding = self.skin_dict['Extras']['current']['observations'][observation].get('data_binding', current_data_binding)
            type_value =  self.skin_dict['Extras']['current']['observations'][observation].get('type', "")
            unit_name = self.skin_dict['Extras']['current']['observations'][observation].get('unit', "default")

            if type_value == 'rise':
                 # todo this is a place holder and needs work
                #set observation_value = '"' + str($getattr($almanac, $observation + 'rise')) + '";'
                observation_value = 'bar'
                #label = 'foo'
            elif type_value == 'sum':
                observation_value = self._get_aggregate(observation, data_binding, interval_current, type_value, unit_name, False)
            else:
                observation_value = self._get_current(observation, data_binding, unit_name).format(add_label=False,localize=False)

            data += '  currentData.' + observation + ' = "' + observation_value + '";\n'

        data += '  pageData.currentData = JSON.stringify(currentData);'
        return data

    def _gen_data_load2(self, interval, interval_type, page_definition_name, skin_data_binding, page_data_binding):
        data = ""

        skin_timespan_binder = self._get_timespan_binder(interval, skin_data_binding)
        page_timespan_binder = self._get_timespan_binder(interval, page_data_binding)

        if interval_type == 'active':
            data += "  pageData.startDate = moment('" + getattr(page_timespan_binder, 'start').format("%Y-%m-%dT%H:%M:%S") + "').utcOffset(" + str(self.utc_offset) + ");\n"
            data += "  pageData.endDate = moment('" + getattr(page_timespan_binder, 'end').format("%Y-%m-%dT%H:%M:%S") + "').utcOffset(" + str(self.utc_offset) + ");\n"
            data += "  pageData.startTimestamp = " + str(getattr(page_timespan_binder, 'start').raw * 1000) + ";\n"
            data += "  pageData.endTimestamp = " + str(getattr(page_timespan_binder, 'end').raw * 1000) + ";\n"
        else:
            # ToDo: document that skin data binding controls start/end of historical data
            # ToDo: make start/end configurable
            start_timestamp = weeutil.weeutil.startOfDay(getattr(getattr(skin_timespan_binder, 'usUnits'), 'firsttime').raw)
            end_timestamp = weeutil.weeutil.startOfDay(getattr(getattr(skin_timespan_binder, 'usUnits'), 'lasttime').raw)
            start_date = datetime.datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%dT%H:%M:%S')
            end_date = datetime.datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%dT%H:%M:%S')

            data += "pageData.startTimestamp =  " + str(start_timestamp * 1000) + ";\n"
            data += "pageData.startDate = moment('" + start_date + "').utcOffset(" + str(self.utc_offset) + ");\n"
            data += "pageData.endTimestamp =  " + str(end_timestamp * 1000) + ";\n"
            data += "pageData.endDate = moment('" + end_date + "').utcOffset(" + str(self.utc_offset) + ");\n"

        data += "\n"
        data += self._gen_interval_end_timestamp(page_data_binding, interval, page_definition_name)

        return data

    @staticmethod
    def mkdir_p(path):
        """equivalent to 'mkdir -p'"""
        try:
            os.makedirs(path)
        except OSError as exception:
            if exception.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise
