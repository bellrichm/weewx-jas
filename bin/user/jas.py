#    Copyright (c) 2021-2022 Rich Bell <bellrichm@gmail.com>
#    See the file LICENSE.txt for your rights.

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
import os
import time
import json

import configobj

import weewx
import weecfg
try:
    # Python 3
    from urllib.request import Request, urlopen, HTTPError # pyright: reportMissingImports=false
except ImportError:
    # Python 2
    from urllib2 import Request, urlopen, HTTPError # pyright: reportMissingImports=false

from weewx.cheetahgenerator import SearchList
from weewx.reportengine import merge_lang
from weewx.units import get_label_string
from weewx.tags import TimespanBinder
from weeutil.weeutil import to_bool, to_int, TimeSpan

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


VERSION = "0.3.1-rc01"

class JAS(SearchList):
    """ Implement tags used by templates in the skin. """
    def __init__(self, generator):
        SearchList.__init__(self, generator)

        now = time.time()
        self.utc_offset = (datetime.datetime.fromtimestamp(now) -
                           datetime.datetime.utcfromtimestamp(now)).total_seconds()/60

        self.wind_observations = ['windCompassAverage', 'windCompassMaximum',
                                  'windCompassRange0', 'windCompassRange1', 'windCompassRange2',
                                  'windCompassRange3', 'windCompassRange4', 'windCompassRange5', 'windCompassRange6']

        forecast_filename = 'forecast.json'
        forecast_endpoint = 'https://api.aerisapi.com/forecasts/'

        current_filename = 'current.json'
        current_endpoint = 'https://api.aerisapi.com/observations/'

        self.ordinate_names = copy.deepcopy(self.generator.formatter.ordinate_names)
        del self.ordinate_names[-1]

        self.skin_dict = generator.skin_dict
        report_dict = self.generator.config_dict.get('StdReport', {})

        self.skin_debug = to_bool(self.skin_dict['Extras'].get('debug', False))
        self.data_binding = self.skin_dict['data_binding']
        self.unit_system = self.skin_dict['unit_system'].upper()

        self.chart_defaults = self.skin_dict['Extras']['chart_defaults'].get('global', {})
        self.chart_series_defaults = self.skin_dict['Extras']['chart_defaults'].get('chart_type', {}).get('series', {})

        self.skin_dicts = {}
        skin_path = os.path.join(self.generator.config_dict['WEEWX_ROOT'], self.skin_dict['SKIN_ROOT'], self.skin_dict['skin'])
        self.languages = weecfg.get_languages(skin_path)

        html_root = self.skin_dict.get('HTML_ROOT',
                                       report_dict.get('HTML_ROOT', 'public_html'))

        html_root = os.path.join(
            self.generator.config_dict['WEEWX_ROOT'], html_root)
        self.html_root = html_root
        self.mkdir_p(os.path.join(self.html_root, 'data'))

        latitude = self.generator.config_dict['Station']['latitude']
        longitude = self.generator.config_dict['Station']['longitude']

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

        self._set_chart_defs()

        self.data_forecast = None
        if self._check_forecast():
            self.data_forecast = self._get_forecasts()

        self.data_current = None
        if to_bool(self.skin_dict['Extras'].get('display_aeris_observation', False)):
            self.data_current = self._get_current()

    def get_extension_list(self, timespan, db_lookup):
        # save these for use when the template variable/function is evaluated
        #self.db_lookup = db_lookup

        search_list_extension = {'aggregate_types': self.aggregate_types,
                                 'current_observation': self.data_current,
                                 'dateTimeFormats': self.get_dateTime_formats,
                                 'data_binding': self.data_binding,
                                 'forecasts': self.data_forecast,
                                 'genCharts': self._gen_charts,
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
                                 'observationLabels': self.get_observation_labels,
                                 'ordinateNames': self.ordinate_names,
                                 'skinDebug': self._skin_debug,
                                 'textLabels': self.get_text_labels,
                                 'utcOffset': self.utc_offset,
                                 'version': VERSION,
                                 'windCompass': self._get_wind_compass,
                                }

        return [search_list_extension]

    def _skin_debug(self, msg):
        if self.skin_debug:
            logdbg(msg)

    def _get_skin_dict(self, language):
        self.skin_dicts[language] = copy.deepcopy(self.skin_dict)
        merge_lang(language, self.generator.config_dict, self.skin_dict['REPORT_NAME'], self.skin_dicts[language])

    def get_observation_labels(self, language):
        if language not in self.skin_dicts:
            if language in self.languages:
                self._get_skin_dict(language)

        return self.skin_dicts[language]['Labels']['Generic']

    def get_text_labels(self, language):
        if language not in self.skin_dicts:
            if language in self.languages:
                self._get_skin_dict(language)

        return self.skin_dicts[language]['Texts']        

    def get_dateTime_formats(self, language):
        if language not in self.skin_dicts:
            if language in self.languages:
                self._get_skin_dict(language)

        dateTime_formats = {}
        dateTime_formats['forecast_date_format'] = self.skin_dicts[language]['Texts']['forecast_date_format']
        dateTime_formats['current_date_time'] = self.skin_dicts[language]['Texts']['current_date_time']
        dateTime_formats['datepicker_date_format'] = self.skin_dicts[language]['Texts']['datepicker_date_format']

        dateTime_formats['year_to_year_xaxis_label'] = self.skin_dicts[language]['Texts']['year_to_year_xaxis_label']

        dateTime_formats['aggregate_interval_mqtt'] = {}
        dateTime_formats['aggregate_interval_mqtt']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_mqtt']['tooltip_x']
        dateTime_formats['aggregate_interval_mqtt']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_mqtt']['xaxis_label']
        dateTime_formats['aggregate_interval_mqtt']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_mqtt']['label']

        dateTime_formats['aggregate_interval_multiyear'] = {}
        dateTime_formats['aggregate_interval_multiyear']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_multiyear']['tooltip_x']
        dateTime_formats['aggregate_interval_multiyear']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_multiyear']['xaxis_label']
        dateTime_formats['aggregate_interval_multiyear']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_multiyear']['label']
                
        dateTime_formats['aggregate_interval_none'] = {}
        dateTime_formats['aggregate_interval_none']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_none']['tooltip_x']
        dateTime_formats['aggregate_interval_none']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_none']['xaxis_label']
        dateTime_formats['aggregate_interval_none']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_none']['label']

        dateTime_formats['aggregate_interval_hour'] = {}
        dateTime_formats['aggregate_interval_hour']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_hour']['tooltip_x']
        dateTime_formats['aggregate_interval_hour']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_hour']['xaxis_label']
        dateTime_formats['aggregate_interval_hour']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_hour']['label']

        dateTime_formats['aggregate_interval_day'] = {}
        dateTime_formats['aggregate_interval_day']['tooltip_x'] = self.skin_dicts[language]['Texts']['aggregate_interval_day']['tooltip_x']
        dateTime_formats['aggregate_interval_day']['xaxis_label'] = self.skin_dicts[language]['Texts']['aggregate_interval_day']['xaxis_label']
        dateTime_formats['aggregate_interval_day']['label'] = self.skin_dicts[language]['Texts']['aggregate_interval_day']['label']

        return dateTime_formats

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

    def _get_wind_compass(self, data_binding=None, start_time=None, end_time=None):
        db_manager = self.generator.db_binder.get_manager(data_binding=data_binding)
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

        wind_ranges = {}
        wind_ranges['mile_per_hour'] = [1, 4, 8, 13, 19, 25, 32]
        wind_ranges['mile_per_hour2'] = [1, 4, 8, 13, 19, 25, 32]
        wind_ranges['km_per_hour'] = [.5, 6, 12, 20, 29, 39, 50]
        wind_ranges['km_per_hour2'] = [.5, 6, 12, 20, 29, 39, 50]
        wind_ranges['meter_per_second'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        wind_ranges['meter_per_second2'] = [1, 1.6, 3.4, 5.5, 8, 10.8, 13.9]
        wind_ranges['knot'] = [1, 4, 7, 11, 17, 22, 28]
        wind_ranges['knot2'] = [1, 4, 7, 11, 17, 22, 28]
        wind_ranges_count = 7

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
        while i < len(self.generator.formatter.ordinate_names) - 1:
            ordinate_name = self.generator.formatter.ordinate_names[i]
            wind_data[ordinate_name] = {}
            wind_data[ordinate_name]['sum'] = 0
            wind_data[ordinate_name]['count'] = 0
            wind_data[ordinate_name]['max'] = 0
            wind_data[ordinate_name]['speed_data'] = []
            j = 0
            while j < wind_ranges_count:
                wind_data[ordinate_name]['speed_data'].append(0)
                j += 1
            i += 1

        i = 0
        wind_speed_data = self.generator.converter.convert(wind_speed_data_raw)
        for wind_speed in wind_speed_data[0]:
            if wind_speed and wind_speed > 0:
                wind_unit = wind_speed_data[1]
                ordinate_name = self.generator.formatter.to_ordinal_compass(
                    (wind_dir_data[0][i], wind_dir_data[1], wind_dir_data[2]))
                wind_data[ordinate_name]['sum'] += wind_speed
                wind_data[ordinate_name]['count'] += 1
                wind_gust_data = self.generator.converter.convert(wind_gust_data_raw)
                if wind_gust_data[0][i] > wind_data[ordinate_name]['max']:
                    wind_data[ordinate_name]['max'] = wind_gust_data[0][i]

                j = 0
                for wind_range in wind_ranges[wind_unit]:
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
        while j < wind_ranges_count:
            wind_compass_speeds.append([])
            j += 1

        for wind_ordinal_data, _ in wind_data.items():
            wind_compass_avg.append(wind_data[wind_ordinal_data]['average'])
            wind_compass_max.append(wind_data[wind_ordinal_data]['max'])

            i = 0
            for wind_x in wind_data[wind_ordinal_data]['speed_data']:
                wind_compass_speeds[i].append(wind_x)
                i += 1

        wind_speed_unit = self.skin_dict["Units"]["Groups"]["group_speed"]
        wind_speed_unit_label = self.skin_dict["Units"]["Labels"][wind_speed_unit]
        low_range = wind_ranges[wind_speed_unit][0]
        high_range = wind_ranges[wind_speed_unit][len(wind_ranges[wind_speed_unit]) - 1]
        wind_range_legend = F"['<{low_range} {wind_speed_unit_label}', "
        for high_range in wind_ranges[wind_speed_unit][1:]:
            wind_range_legend += F"'{low_range}-{high_range} {wind_speed_unit_label}', "
            low_range = high_range
        wind_range_legend += F"'>{high_range} {wind_speed_unit_label}']"

        return wind_compass_avg, wind_compass_max, wind_compass_speeds, wind_range_legend

    def _get_observation_text(self, coded_weather):
        cloud_codes = ["CL", "FW", "SC", "BK", "OV",]

        coverage_code = coded_weather.split(":")[0]
        intensity_code = coded_weather.split(":")[1]
        weather_code = coded_weather.split(":")[2]

        if weather_code in cloud_codes:
            cloud_code_key = 'cloud_code_' + weather_code
            observation_text = "textLabels[lang]['" + cloud_code_key + "']"
        else:
            observation_text = ''
            if coverage_code:
                coverage_code_key = 'coverage_code_' + coverage_code
                if observation_text != "":
                    observation_text +=  " + ' ' + "
                observation_text += "textLabels[lang]['" + coverage_code_key + "']"
            if intensity_code:
                intensity_code_key = 'intensity_code_' + intensity_code
                if observation_text != "":
                    observation_text +=  " + ' ' + "
                observation_text += "textLabels[lang]['" + intensity_code_key + "']"

            weather_code_key = 'weather_code_' + weather_code
            if observation_text != "":
                observation_text +=  " + ' ' + "
            observation_text += "textLabels[lang]['" + weather_code_key + "']"

        return observation_text

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

        data = json.loads(body)

        if data['success']:
            return data['response']
        else:
            logerr(F"An error occurred: {data['error']['description']}")
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
                forecast['day'] = "textLabels[lang]['" + day_of_week_key + "']"
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

    def _get_current(self):
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
            if self.skin_dict['Extras']['pages'][page].get('enable', True) and 'forecast' in self.skin_dict['Extras']['pages'][page].sections:
                return True

        return False

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

                            if obs_data_binding not in observations[observation]['aggregate_types']:
                                observations[observation]['aggregate_types'][aggregate_type][obs_data_binding] = {}

                            unit = weewx_options.get('unit', 'default')
                            observations[observation]['aggregate_types'][aggregate_type][obs_data_binding][unit] = {}
                            aggregate_types[aggregate_type] = {}

        minmax_observations = self.skin_dict.get('Extras', {}).get('minmax', {}).get('observations', {})
        minmax_data_binding = self.skin_dict.get('Extras', {}).get('minmax', {}).get('data_binding', skin_data_binding)
        for observation in self.skin_dict['Extras']['minmax']['observations'].sections:
            data_binding = minmax_observations[observation].get('data_binding', minmax_data_binding)
            if observation not in self.wind_observations:
                unit = minmax_observations[observation].get('unit', 'default')
                if observation not in observations:
                    observations[observation] = {}
                    observations[observation]['aggregate_types'] = {}

                if 'min' not in observations[observation]['aggregate_types']:
                    observations[observation]['aggregate_types']['min'] = {}
                    observations[observation]['aggregate_types']['min'][data_binding] = {}
                observations[observation]['aggregate_types']['min'][data_binding][unit] = {}
                aggregate_types['min'] = {}
                if 'max' not in observations[observation]['aggregate_types']:
                    observations[observation]['aggregate_types']['max'] = {}
                    observations[observation]['aggregate_types']['max'][data_binding] = {}
                observations[observation]['aggregate_types']['max'][data_binding][unit] = {}
                aggregate_types['max'] = {}

        thisdate_observations = self.skin_dict.get('Extras', {}).get('thisdate', {}).get('observations', {})
        thisdate_data_binding = self.skin_dict.get('Extras', {}).get('thisdate', {}).get('data_binding', skin_data_binding)
        for observation in thisdate_observations:
            data_binding = thisdate_observations[observation].get('data_binding', thisdate_data_binding)
            if observation not in self.wind_observations:
                unit = thisdate_observations[observation].get('unit', 'default')
                if observation not in observations:
                    observations[observation] = {}
                    observations[observation]['aggregate_types'] = {}

                if 'min' not in observations[observation]['aggregate_types']:
                    observations[observation]['aggregate_types']['min'] = {}
                    observations[observation]['aggregate_types']['min'][data_binding] = {}
                observations[observation]['aggregate_types']['min'][data_binding][unit] = {}
                aggregate_types['min'] = {}
                if 'max' not in observations[observation]['aggregate_types']:
                    observations[observation]['aggregate_types']['max'] = {}
                    observations[observation]['aggregate_types']['max'][data_binding] = {}
                observations[observation]['aggregate_types']['max'][data_binding][unit] = {}
                aggregate_types['max'] = {}

        return observations, aggregate_types

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
            self.chart_defs[chart]['weewx']['yAxis'] = {}
            self.chart_defs[chart]['weewx']['yAxis']['0'] = {}
            self.chart_defs[chart]['weewx']['yAxis']['0']['obs'] = obs
            
            if self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs].get('weewx', False):
                self.chart_defs[chart]['weewx']['yAxis']['0']['unit'] = self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs]['weewx'].get('unit', None)

            # ToDo: rework
            for value in self.skin_dict['Extras']['chart_definitions'][chart]['series']:
                charttype = self.skin_dict['Extras']['chart_definitions'][chart]['series'][value].get('type', None)
                if not charttype:
                    charttype = "'line'"
                    self.chart_defs[chart]['series'][value]['type'] = charttype

                y_axis_index = self.skin_dict['Extras']['chart_definitions'][chart]['series'][value].get('yAxisIndex', None)
                if y_axis_index is not None:
                    if y_axis_index not in self.chart_defs[chart]['weewx']['yAxis']:
                        self.chart_defs[chart]['weewx']['yAxis'][y_axis_index] = {}
                    self.chart_defs[chart]['weewx']['yAxis'][y_axis_index]['obs'] = value
                    if self.skin_dict['Extras']['chart_definitions'][chart]['series'][value].get('weewx', False):
                        self.chart_defs[chart]['weewx']['yAxis']['0']['unit'] = self.skin_dict['Extras']['chart_definitions'][chart]['series'][value]['weewx'].get('unit', None)

                self.chart_defs[chart]['series'][value].merge((self.chart_series_defaults.get(coordinate_type, {}).get(charttype, {})))
                weewx_options['observation'] = value
                if 'weewx' not in self.chart_defs[chart]['series'][value]:
                    self.chart_defs[chart]['series'][value]['weewx'] = {}
                weeutil.config.conditional_merge(self.chart_defs[chart]['series'][value]['weewx'], weewx_options)

    def _iterdict(self, indent, page, chart, chart_js, series_type, interval, dictionary, chart_data_binding):
        chart2 = chart_js
        for key, value in dictionary.items():
            if isinstance(value, dict):
                if key == 'weewx':
                    continue
                if key == 'series':
                    chart2 += indent + "series: [\n"

                    if series_type == 'comparison':
                        obs = next(iter(value))
                        (start_year, end_year) = self._get_range(self.skin_dict['Extras']['pages'][page].get('start', None),
                                                                 self.skin_dict['Extras']['pages'][page].get('end', None),
                                                                 chart_data_binding)
                        for year in range(start_year, end_year):
                            chart2 += indent + " {\n"
                            chart2 += "    name: '" + str(year) + "',\n"
                            chart2 = self._iterdict(indent + '  ', page, chart, chart2, series_type, interval, value[obs], chart_data_binding)
                            chart2 += indent + "  },\n"
                    else:
                        for obs in value:
                            aggregate_type = self.chart_defs[chart]['series'][obs]['weewx']['aggregate_type']
                            aggregate_interval = self.skin_dict['Extras']['page_definition'][page].get('aggregate_interval', {}) \
                                                .get(aggregate_type, 'none')

                            # set the aggregate_interval at the beginning of the chart definition, so it can be used in the chart
                            # Note, this means the last observation's aggregate type will be used to determine the aggregate interval
                            if series_type == 'multiple':
                                chart2 = "#set global aggregate_interval_global = 'multiyear'\n" + chart2
                            elif series_type == 'mqtt':
                                chart2 = "#set global aggregate_interval_global = 'mqtt'\n" + chart2
                            else:
                                chart2 = "#set global aggregate_interval_global = '" + aggregate_interval + "'\n" + chart2

                            chart2 += indent + " {\n"
                            chart2 = self._iterdict(indent + '  ', page, chart, chart2, series_type, interval, value[obs], chart_data_binding)

                            chart2 += indent + "},\n"

                    chart2 += indent +"],\n"
                else:
                    chart2 += indent + key + ":" + " {\n"
                    chart2 = self._iterdict(indent + '  ', page, chart, chart2, series_type, interval, value, chart_data_binding)
                    chart2 += indent + "},\n"
            else:
                chart2 += indent + key + ": " + value + ",\n"
        return chart2

    def _gen_charts(self, page, interval, page_name):
        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        page_series_type = self.skin_dict['Extras']['page_definition'][page].get('series_type', 'single')

        #chart_final = 'var pageCharts = [];\n'
        chart_final = '## charts\n'
        chart2 = ""
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
                #self.charts_def[chart].merge(self.skin_dict['Extras']['pages'][page][chart])
                for observation in chart_def['series']:
                    obs = chart_def['series'][observation].get('weewx', {}).get('observation', observation)

                #

                chart_js = "var option = {\n"
                chart2 += self._iterdict('  ', page, chart, chart_js, series_type, interval, chart_def, chart_data_binding)

                # ToDo: do not hard code 'grid'
                if 'polar' in self.skin_dict['Extras']['chart_definitions'][chart]:
                    coordinate_type = 'polar'
                elif 'grid' in self.skin_dict['Extras']['chart_definitions'][chart]:
                    coordinate_type = 'grid'
                else:
                    coordinate_type = 'grid'
                default_grid_properties = self.skin_dict['Extras']['chart_defaults'].get('properties', {}).get('grid', None)
                if 'yAxis' not in chart_def and coordinate_type == 'grid':
                    chart2 += '  yAxis: [\n'
                    for i in range(0, len(chart_def['weewx']['yAxis'])):
                        if str(i) in chart_def['weewx']['yAxis']:
                       
                            unit_name = chart_def['weewx']['yAxis'][str(i)].get('unit', None)
                            if unit_name is not None:
                                y_axis_label = self._get_unit_label(unit_name)
                            else:
                                y_axis_label = self._get_obs_unit_label( chart_def['weewx']['yAxis'][str(i)]['obs'])

                            chart2 += "#set yAxisLabel = '" + y_axis_label + "'\n"

                        chart2 += '  #set index = ' + str(i) + '\n'
                        chart2 += '    {\n'
                        chart2 += self._iterdict('      ',
                                                 page, chart,
                                                 '',
                                                 series_type,
                                                 interval,
                                                 default_grid_properties['yAxis'],
                                                 chart_data_binding)
                        chart2 += '    },\n'
                    chart2 += '  ],\n'

                chart2 += "};\n"
                chart2 += "var telem = document.getElementById('" + chart + page_name + "');\n"
                chart2 += "var " + chart + "chart = echarts.init(document.getElementById('" + chart + page_name + "'));\n"
                chart2 += chart + "chart.setOption(option);\n"

                chart2 += "pageChart = {};\n"

                if series_type == 'mqtt':
                    chart2 += "pageChart.option = null;\n"
                elif series_type == 'multiple':
                    chart2 += "option = {\n"
                    chart2 += "  series: [\n"
                    for obs in chart_def['series']:
                        aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                        obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        chart2 += "    {name: " + chart_def['series'][obs].get('name', 'observationLabels[lang][' + "'" + obs + "']") + ",\n"
                        chart2 += "     data: [\n"
                        (start_year, end_year) = self._get_range(self.skin_dict['Extras']['pages'][page].get('start', None),
                                                                 self.skin_dict['Extras']['pages'][page].get('end', None),
                                                                 chart_data_binding)
                        for year in range(start_year, end_year):
                            chart2 += "            ...year" + str(year) + "_" + aggregate_type \
                                      + "." + chart_def['series'][obs]['weewx']['observation'] + "_"  + obs_data_binding + ",\n"
                        chart2 += "          ]},\n"
                    chart2 += "]};\n"
                    chart2 += "pageChart.option = option;\n"
                elif series_type == 'comparison':
                    text_translations = self.generator.skin_dict.get('Texts', weeutil.config.config_from_str('lang = en'))
                    year_to_year_xaxis_label = text_translations.get('year_to_year_xaxis_label', 'MM/DD')

                    chart2 += "option = {\n"
                    chart2 += "  series: [\n"
                    obs = next(iter(chart_def['series']))
                    obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                    aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                    (start_year, end_year) = self._get_range(self.skin_dict['Extras']['pages'][page].get('start', None),
                                                             self.skin_dict['Extras']['pages'][page].get('end', None),
                                                             chart_data_binding)
                    for year in range(start_year, end_year):
                        chart2 += "    {name: '" + str(year) + "',\n"
                        chart2 += "     data: year" + str(year) + "_" + aggregate_type \
                                + "." + obs + "_"  + obs_data_binding \
                                + ".map(arr => [moment.unix(arr[0] / 1000).utcOffset(" + str(self.utc_offset) + ").format(dateTimeFormat[lang].chart.yearToYearXaxis), arr[1]]),\n" \
                                + "},\n"
                    chart2 += "]};\n"
                    chart2 += "pageChart.option = option;\n"
                else:
                    chart2 += "option = {\n"
                    chart2 += "  series: [\n"
                    for obs in chart_def['series']:
                        aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                        obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        unit_name = chart_def['series'][obs].get('weewx', {}).get('unit', None)
                        obs_data_unit = ""
                        if unit_name is not None:
                            obs_data_unit = "_" + unit_name
                        chart2 += "    {name: " + chart_def['series'][obs].get('name', "observationLabels[lang]['" + obs + "']") + ",\n"
                        chart2 += "    data: " \
                                + interval + "_" + aggregate_type \
                                + "." + chart_def['series'][obs]['weewx']['observation'] + "_"  + obs_data_binding + obs_data_unit \
                                + "},\n"
                    chart2 += "]};\n"
                    chart2 += "pageChart.option = option;\n"

                chart2 += "pageChart.chart = " + chart + "chart;\n"
                chart2 += "pageCharts.push(pageChart);\n"

        chart_final += chart2

        return chart_final

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
