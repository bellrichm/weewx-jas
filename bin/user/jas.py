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
import os
import time
import json

import configobj

import weewx
import weecfg
try:
    # Python 3
    from urllib.request import Request, urlopen, HTTPError # pyright: ignore reportMissingImports=false
except ImportError:
    # Python 2
    from urllib2 import Request, urlopen, HTTPError # pyright: ignore reportMissingImports=false

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


VERSION = "0.3.2-rc01a"

class JAS(SearchList):
    """ Implement tags used by templates in the skin. """
    def __init__(self, generator):
        SearchList.__init__(self, generator)

        self.unit = weewx.units.UnitInfoHelper(generator.formatter, generator.converter)

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
            self.data_current = self._get_current_obs()

    def get_extension_list(self, timespan, db_lookup):
        # save these for use when the template variable/function is evaluated
        #self.db_lookup = db_lookup
        self.timespan = timespan

        search_list_extension = {'aggregate_types': self.aggregate_types,
                                 'current_observation': self.data_current,
                                 'dateTimeFormats': self._get_date_time_formats,
                                 'data_binding': self.data_binding,
                                 'forecasts': self.data_forecast,
                                 'genCharts': self._gen_charts,
                                 'genData': self._gen_data,
                                 'genJs': self._gen_js,
                                 'genJasOptions': self._gen_jas_options,
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
                                 'ordinateNames': self.ordinate_names,
                                 'skinDebug': self._skin_debug,
                                 'textLabels': self._get_text_labels,
                                 'utcOffset': self.utc_offset,
                                 'version': VERSION,
                                 'weewx_version': weewx.__version__,
                                 'windCompass': self._get_wind_compass,
                                }

        return [search_list_extension]

    def _skin_debug(self, msg):
        if self.skin_debug:
            logdbg(msg)

    def _get_skin_dict(self, language):
        self.skin_dicts[language] = copy.deepcopy(self.skin_dict)
        merge_lang(language, self.generator.config_dict, self.skin_dict['REPORT_NAME'], self.skin_dicts[language])
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
            observation_text = "getText('" + cloud_code_key + "')"
        else:
            observation_text = ''
            if coverage_code:
                coverage_code_key = 'coverage_code_' + coverage_code
                if observation_text != "":
                    observation_text +=  " + ' ' + "
                observation_text += "getText('" + coverage_code_key + "')"
            if intensity_code:
                intensity_code_key = 'intensity_code_' + intensity_code
                if observation_text != "":
                    observation_text +=  " + ' ' + "
                observation_text += "getText('" + intensity_code_key + "')"

            weather_code_key = 'weather_code_' + weather_code
            if observation_text != "":
                observation_text +=  " + ' ' + "
            observation_text += "getText('" + weather_code_key + "')"

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
                forecast['day'] = "getText('" + day_of_week_key + "')"
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

                            if obs_data_binding not in observations[observation]['aggregate_types'][aggregate_type]:
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
                                chart2 = "aggregate_interval = 'multiyear'\n" + chart2
                            elif series_type == 'mqtt':
                                chart2 = "aggregate_interval = 'mqtt'\n" + chart2
                            else:
                                chart2 = "aggregate_interval = '" + aggregate_interval + "'\n" + chart2

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

    def _gen_charts(self, filename, page, interval, page_name):
        start_time = time.time()
        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        page_series_type = self.skin_dict['Extras']['page_definition'][page].get('series_type', 'single')

        #chart_final = 'var pageCharts = [];\n'
        chart_final = 'utc_offset = ' + str(self.utc_offset) + ';\n'
        chart_final += "ordinateNames = ['" + "', '".join(self.ordinate_names) + "'];\n"
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

                        #chart2 += '  #set index = ' + i_str + '\n'
                        chart2 += self._iterdict('      ',
                                                 page, chart,
                                                 '',
                                                 series_type,
                                                 interval,
                                                 y_axis_default,
                                                 chart_data_binding)
                        chart2 += '    },\n'
                    chart2 += '  ],\n'

                chart2 += "};\n"
                chart2 += "var telem = document.getElementById('" + chart + page_name + "');\n"
                chart2 += "var " + chart + "chart = echarts.init(document.getElementById('" + chart + page_name + "'));\n"
                chart2 += chart + "chart.setOption(option);\n"

                chart2 += "pageChart = {};\n"

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
                    chart2 += "option = {\n"
                    chart2 += "  series: [\n"
                    for obs in chart_def['series']:
                        aggregate_type = chart_def['series'][obs]['weewx']['aggregate_type']
                        obs_data_binding = chart_def['series'][obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        chart2 += "    {name: " + chart_def['series'][obs].get('name', 'getLabel(' + "'" + obs + "')") + ",\n"
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
                                + ".map(arr => [moment.unix(arr[0] / 1000).utcOffset(" + str(self.utc_offset) \
                                + ").format(dateTimeFormat[lang].chart.yearToYearXaxis), arr[1]]),\n" \
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
                        chart2 += "    {name: " + chart_def['series'][obs].get('name', "getLabel('" + obs + "')") + ",\n"
                        chart2 += "    data: " \
                                + interval + "_" + aggregate_type \
                                + "." + chart_def['series'][obs]['weewx']['observation'] + "_"  + obs_data_binding + obs_data_unit \
                                + "},\n"
                    chart2 += "]};\n"
                    chart2 += "pageChart.option = option;\n"

                chart2 += "pageChart.chart = " + chart + "chart;\n"
                chart2 += "pageCharts.push(pageChart);\n"

        chart_final += chart2

        elapsed_time = time.time() - start_time
        log_msg = "Generated " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return chart_final

    # Create time stamps by aggregation time for the end of interval
    # For example: endTimestamp_min, endTimestamp_max
    def _gen_interval_end_timestamp(self, page_data_binding, interval_name, page_definition_name, interval_long_name):
        data = ''
        for aggregate_type in self.skin_dict['Extras']['page_definition'][page_definition_name]['aggregate_interval']:
            aggregate_interval = self.skin_dict['Extras']['page_definition'][page_definition_name]['aggregate_interval'][aggregate_type]
            if aggregate_interval == 'day':
                endTimestamp =(self._get_TimeSpanBinder(interval_name, page_data_binding).end.raw // 86400 * 86400 - (self.utc_offset * 60)) * 1000
            elif aggregate_interval == 'hour':
                endTimestamp =(self._get_TimeSpanBinder(interval_name, page_data_binding).end.raw // 3600 * 3600 - (self.utc_offset * 60)) * 1000
            else:
                endTimestamp =(self._get_TimeSpanBinder(interval_name, page_data_binding).end.raw // 60 * 60 - (self.utc_offset * 60)) * 1000

            data +=  "var " + interval_long_name + "endTimestamp_" + aggregate_type + " = " + str(endTimestamp) + ";\n"

        return data

    # Populate the 'aggegate' objects
    # Example: last7days_min.outTemp = [[dateTime1, outTemp1], [dateTime2, outTemp2]]
    def _gen_aggregate_objects(self, interval, page_definition_name, interval_long_name):
        data = ""

        for observation in self.observations:
            for aggregate_type in self.observations[observation]['aggregate_types']:
                aggregate_interval = self.skin_dict['Extras']['page_definition'][page_definition_name]['aggregate_interval'].get(aggregate_type, None)
                interval_name = interval_long_name + aggregate_type
                for data_binding in self.observations[observation]['aggregate_types'][aggregate_type]:
                    for unit_name in self.observations[observation]['aggregate_types'][aggregate_type][data_binding]:
                        name_prefix = interval_name + "." + observation + "_"  + data_binding
                        name_prefix2 = interval_name + "_" + observation + "_"  + data_binding
                        if unit_name == "default":
                            pass
                        else:
                            name_prefix += "_" + unit_name
                            name_prefix2 += "_" + unit_name

                        array_name = name_prefix
                        dateTime_name = name_prefix2 + "_dateTime"
                        data_name = name_prefix2 + "_data"

                        if aggregate_interval is not None:
                            data += array_name + " = " + self._get_series(observation, data_binding, interval, aggregate_type, aggregate_interval, 'start', 'unix_epoch_ms', unit_name, 2, True) + ";\n"
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
                            data += array_name + " = " + self._get_series(weewx_observation, data_binding, interval, None, None, 'start', 'unix_epoch_ms', unit_name, 2, True) + ";\n"

                        # Cache the dateTimes into its own list variable
                        data += dateTime_name + " = [].concat(" + array_name + ".map(arr => arr[0]));\n"
                        # Cache the values into its own list variable
                        data += data_name + " = [].concat(" + array_name + ".map(arr => arr[1]));\n"
                        data += "\n"

        return data

    def _gen_this_date(self, skin_data_binding, interval_long_name):
        data = ""

        thisdate_data_binding = self.skin_dict['Extras']['thisdate'].get('data_binding', skin_data_binding)
        for observation in self.skin_dict['Extras']['thisdate']['observations']:
            data_binding = self.skin_dict['Extras']['thisdate']['observations'][observation].get('data_binding', thisdate_data_binding)
            unit_name = self.skin_dict['Extras']['thisdate']['observations'][observation].get('unit', "default")
            if unit_name == "default":
                unit_suffix = ""
                label = getattr(self.unit.label, observation)
            else:
                unit_suffix = "_" + unit_name
                label = self._get_unit_label(unit_name)

            aggregation_type = self.skin_dict['Extras']['thisdate']['observations'][observation].get('type', None)
            max_decimals = self.skin_dict['Extras']['thisdate']['observations'][observation].get('max_decimals', False)

            data += "thisDateObs = [];\n"
            data += "maxDecimals = null;\n"
            if max_decimals:
                data += "maxDecimals = " + max_decimals + ";\n"

            if aggregation_type is None:
                data += 'thisDateObsDetail = {};\n'
                data += 'thisDateObsDetail.label = "' + label + '";\n'
                data += 'thisDateObsDetail.maxDecimals = maxDecimals;\n'
                value = interval_long_name + 'min.' + observation + "_" + data_binding + unit_suffix
                id_value = observation + "_thisdate_min"
                data += 'thisDateObsDetail.dataArray = ' + value + ';\n'
                data += 'thisDateObsDetail.id = "' + id_value + '";\n'
                data += 'thisDateObs.push(thisDateObsDetail);\n'
                data += '\n'

                data += 'thisDateObsDetail = {};\n'
                data += 'thisDateObsDetail.label = "' + label + '";\n'
                data += 'thisDateObsDetail.maxDecimals = maxDecimals;\n'
                value = interval_long_name + 'max.' + observation + "_" + data_binding + unit_suffix
                id_value = observation + "_thisdate_max"
                data += 'thisDateObsDetail.dataArray = ' + value + ';\n'
                data += 'thisDateObsDetail.id = "' + id_value + '";\n'
                data += 'thisDateObs.push(thisDateObsDetail);\n'
                data += '\n'
            else:
                data += 'thisDateObsDetail = {};\n'
                data += 'thisDateObsDetail.label = "' + label + '";\n'
                data += 'thisDateObsDetail.maxDecimals = maxDecimals;\n'
                value = interval_long_name + aggregation_type + '.' + observation + "_" + data_binding + unit_suffix
                id_value = observation + "_thisdate_" + aggregation_type
                data += 'thisDateObsDetail.dataArray = ' + value + ';\n'
                data += 'thisDateObsDetail.id = "' + id_value + '";\n'
                data += 'thisDateObs.push(thisDateObsDetail);\n'
                data += '\n'

            data += 'thisDateObsList.push(thisDateObs);\n'

        return data

    def _gen_min_max(self, skin_data_binding, interval_long_name):
        data = ''

        minmax_data_binding = self.skin_dict['Extras']['minmax'].get('data_binding', skin_data_binding)
        for observation in self.skin_dict['Extras']['minmax']['observations']:
            data_binding = self.skin_dict['Extras']['minmax']['observations'][observation].get('data_binding', minmax_data_binding)
            unit_name = self.skin_dict['Extras']['minmax']['observations'][observation].get('unit', "default")

            min_name_prefix = interval_long_name + "min_" + observation + "_" + data_binding
            max_name_prefix = interval_long_name + "max_" + observation + "_" + data_binding
            if unit_name != "default":
                min_name_prefix += "_" + unit_name
                max_name_prefix += "_" + unit_name
                label = self._get_unit_label(unit_name)
            else:
                label = getattr(self.unit.label, observation)

            data += 'minMaxObsData = {};\n'
            data += 'minMaxObsData.minDateTimeArray = ' + min_name_prefix + '_dateTime;\n'
            data += 'minMaxObsData.minDataArray = ' +  min_name_prefix + '_data;\n'
            data += 'minMaxObsData.maxDateTimeArray = ' + max_name_prefix + '_dateTime;\n'
            data += 'minMaxObsData.maxDataArray = ' +  max_name_prefix + '_data;\n'
            data += 'minMaxObsData.label = "' + label + '";\n'
            data += 'minMaxObsData.minId =  "' + observation + '_minmax_min";\n'
            data += 'minMaxObsData.maxId = "' + observation + '_minmax_max";\n'
            data += 'minMaxObsData.maxDecimals = ' + self.skin_dict['Extras']['minmax']['observations'][observation].get('max_decimals', "null") +';\n'
            data += 'minMaxObs.push(minMaxObsData);\n'
            data += '\n'

        return data

    # Create the data used to display current conditions.
    # This data is only used when MQTT is not enabled.
    # This data is stored in a javascript object named 'current'.
    # 'current.header' is an object with the data for the header portion of this section.
    # 'current.observations' is a map. The key is the observation name, like 'outTemp'. The value is the data to populate the section.
    # 'current.suffixes is also a map'. Its key is observation_suffix, for example 'outTemp_suffix'.
    def _gen_current(self, skin_data_binding, interval):
        data = ''

        current_data_binding = self.skin_dict['Extras']['current'].get('data_binding', skin_data_binding)
        interval_current = self.skin_dict['Extras']['current'].get('interval', interval)

        data += 'var mqtt_enabled = false;\n'
        data += 'var updateDate = ' + str(self._get_current('dateTime', data_binding=current_data_binding, unit_name='default').raw * 1000) +';\n'
        data += 'var current = {};\n'
        if self.skin_dict['Extras']['current'].get('observation', False):
            data += 'current.header = {};\n'
            data += 'current.header.name = "' + self.skin_dict['Extras']['current']['observation'] +'";\n'

            data_binding = self.skin_dict['Extras']['current'].get('header_data_binding', current_data_binding)
            data += 'current.header.value = ' + self._get_current(self.skin_dict['Extras']['current']['observation'], data_binding, 'default').format(add_label=False,localize=False) + ';\n'
            header_max_decimals = self.skin_dict['Extras']['current'].get('header_max_decimals', False)
            if header_max_decimals:
                data += 'current.header.value = current.header.value.toFixed(' + header_max_decimals + ');\n'

            data += 'if (!isNaN(current.header.value)) {\n'
            data += '    current.header.value = Number(current.header.value).toLocaleString(lang);\n'
            data += '}\n'
            data += 'current.header.unit = "' + getattr(self.unit.label, self.skin_dict['Extras']['current']['observation']) + '";\n'

        data += 'current.observations = new Map();\n'
        data += 'current.suffixes = new Map();\n'

        for observation in self.skin_dict['Extras']['current']['observations']:
            data_binding = self.skin_dict['Extras']['current']['observations'][observation].get('data_binding', current_data_binding)
            type_value =  self.skin_dict['Extras']['current']['observations'][observation].get('type', "")
            unit_name = self.skin_dict['Extras']['current']['observations'][observation].get('unit', "default")

            if unit_name != "default":
                observation_unit = self._get_unit_label(unit_name)
            else:
                observation_unit = getattr(self.unit.label, observation)

            if type_value == 'rise':
                 # todo this is a place holder and needs work
                #set observation_value = '"' + str($getattr($almanac, $observation + 'rise')) + '";'
                observation_value = '"bar"'
                observation_unit = " "
                #label = 'foo'
            elif type_value == 'sum':
                observation_value = self._get_aggregate(observation, data_binding, interval_current, type_value, unit_name, False)
            else:
                observation_value = self._get_current(observation, data_binding, unit_name).format(add_label=False,localize=False)

            data += 'var observation = {};\n'
            data += 'observation.name = "' + observation + '";\n'
            data += 'observation.mqtt = ' + self.skin_dict['Extras']['current']['observations'][observation].get('mqtt', 'true').lower() + ';\n'
            data += 'observation.value = ' + observation_value +';\n'
            max_decimals = self.skin_dict['Extras']['current']['observations'][observation].get('max_decimals', False)
            if max_decimals:
                data += 'observation.value = observation.value.toFixed(' + max_decimals + ');\n'
            data += 'if (!isNaN(observation.value)) {\n'
            data += '    observation.value = Number(observation.value).toLocaleString(lang);\n'
            data += '}\n'
            data += 'observation.unit = "' + observation_unit + '";\n'
            data += 'observation.maxDecimals = ' + self.skin_dict['Extras']['current']['observations'][observation].get('max_decimals', 'null') +';\n'
            data += 'current.observations.set("' + observation + '", observation);\n'
            data += '\n'

        return data

    def _gen_mqtt(self, page):
        data = ''

        ## Create an array of mqtt observations in charts
        data += 'mqttData2 = {};\n'
        data += 'mqttData = {};\n'

        page_series_type = self.skin_dict['Extras']['page_definition'].get('series_type', 'single')
        for chart in self.skin_dict['Extras']['chart_definitions']:
            if chart in self.skin_dict['Extras']['pages'][page]:
                chart_series_type = self.skin_dict['Extras']['pages'][page][chart].get('series_type', page_series_type)
                if chart_series_type == 'mqtt':
                    for observation in self.skin_dict['Extras']['chart_definitions'][chart]['series']:
                        data += "mqttData2['" + observation + "'] = {};\n"
                        data += "mqttData2['" + observation + "'] = [];\n"
                        data+= "mqttData." + observation + "= [];\n"

        data += "fieldMap = new Map();\n"
        # ToDo: optimize - only do if page uses MQTT
        if self.skin_dict['Extras'].get('mqtt', False):
            for field in self.skin_dict['Extras']['mqtt'].get('fields', []):
                fieldname = self.skin_dict['Extras']['mqtt']['fields'][field]['name']
                data += "fieldMap.set('" + fieldname + "', '" + field + "');\n"
        return data

    # Proof of concept - wind rose
    # Create data for wind rose chart
    def _gen_windrose(self, page_data_binding, interval_name, page_definition_name, interval_long_name):
        data = ''

        interval_start_seconds_global = self._get_TimeSpanBinder(interval_name, page_data_binding).start.raw
        interval_end_seconds_global = self._get_TimeSpanBinder(interval_name, page_data_binding).end.raw

        if self.skin_dict['Extras']['pages'][page_definition_name].get('windRose', None) is not None:
            avg_value, max_value, wind_directions, wind_range_legend = self._get_wind_compass(data_binding=page_data_binding, start_time=interval_start_seconds_global, end_time=interval_end_seconds_global)
            data += "var windRangeLegend = " + wind_range_legend + ";\n"
            i = 0
            for wind in wind_directions:
                data += interval_long_name + "avg.windCompassRange"  + str(i) + "_" + page_data_binding + " = "  + str(wind) +  ";\n"
                i += 1

        return data

    def _gen_data(self, filename, page, interval, interval_type, page_definition_name, interval_long_name):
        start_time = time.time()

        skin_data_binding = self.skin_dict['Extras'].get('data_binding', self.data_binding)
        page_data_binding = self.skin_dict['Extras']['pages'][page_definition_name].get('data_binding', skin_data_binding)

        skin_timespan_binder = self._get_TimeSpanBinder(interval, skin_data_binding)
        page_timespan_binder = self._get_TimeSpanBinder(interval, page_data_binding)

        data = ''
        data += '// the start\n'

        if interval_type == 'active':
            data += "var " + interval_long_name + "startDate = moment('" + getattr(page_timespan_binder, 'start').format("%Y-%m-%dT%H:%M:%S") + "').utcOffset(" + str(self.utc_offset) + ");\n"
            data += "var " + interval_long_name + "endDate = moment('" + getattr(page_timespan_binder, 'end').format("%Y-%m-%dT%H:%M:%S") + "').utcOffset(" + str(self.utc_offset) + ");\n"
            data += "var " + interval_long_name + "startTimestamp = " + str(getattr(page_timespan_binder, 'start').raw * 1000) + ";\n"
            data += "var " + interval_long_name + "endTimestamp = " + str(getattr(page_timespan_binder, 'end').raw * 1000) + ";\n"
        else:
            # ToDo: document that skin data binding controls start/end of historical data
            # ToDo: make start/end configurable
            start_timestamp = weeutil.weeutil.startOfDay(getattr(getattr(skin_timespan_binder, 'usUnits'), 'firsttime').raw)
            end_timestamp = weeutil.weeutil.startOfDay(getattr(getattr(skin_timespan_binder, 'usUnits'), 'lasttime').raw)
            start_date = datetime.datetime.fromtimestamp(start_timestamp).strftime('%Y-%m-%dT%H:%M:%S')
            end_date = datetime.datetime.fromtimestamp(end_timestamp).strftime('%Y-%m-%dT%H:%M:%S')

            data += "var " + interval_long_name + "startTimestamp =  " + str(start_timestamp * 1000) + ";\n"
            data += "var " + interval_long_name + "startDate = moment('" + start_date + "').utcOffset(" + str(self.utc_offset) + ");\n"
            data += "var " + interval_long_name + "endTimestamp =  " + str(end_timestamp * 1000) + ";\n"
            data += "var " + interval_long_name + "endDate = moment('" + end_date + "').utcOffset(" + str(self.utc_offset) + ");\n"

        data += "\n"
        data += self._gen_interval_end_timestamp(page_data_binding, interval, page_definition_name, interval_long_name)

        data += "\n"
        # Define the 'aggegate' objects to hold the data
        # For example: last7days_min = {}, last7days_max = {}
        for aggregate_type in self.aggregate_types:
            data += interval_long_name + aggregate_type + " = {};\n"

        data += "\n"
        data += self._gen_aggregate_objects(interval, page_definition_name, interval_long_name)

        data += "\n"
        data += "thisDateObsList = [];\n"
        if 'thisdate' in self.skin_dict['Extras']['pages'][page]:
            data += self._gen_this_date(skin_data_binding, interval_long_name)

        data += "\n"
        data += "minMaxObs = [];\n"
        if 'minmax' in self.skin_dict['Extras']['pages'][page]:
            data += self._gen_min_max(skin_data_binding, interval_long_name)

        data += "\n"
        if self.skin_dict['Extras']['pages'][page_definition_name].get('current', None) is not None:
            data += self._gen_current(skin_data_binding, interval)

        data += "\n"
        data += self._gen_mqtt(page)

        data += "\n"
        if self.skin_dict['Extras']['pages'][page_definition_name].get('windRose', None) is not None:
            data += self._gen_windrose(page_data_binding, interval, page_definition_name, interval_long_name)

        data += '// the end\n'

        elapsed_time = time.time() - start_time
        log_msg = "Generated " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return data

    def _gen_js(self, filename, page, year, month, interval_long_name):
        start_time = time.time()
        data = ''

        data += '// start\n'

        if interval_long_name:
            startDate = interval_long_name + "startDate"
            endDate = interval_long_name + "endDate"
            startTimestamp = interval_long_name + "startTimestamp"
            endTimestamp = interval_long_name + "endTimestamp"
        else:
            startDate = "null"
            endDate = "null"
            startTimestamp = "null"
            endTimestamp = "null"

        today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

        selected_year = str(today.year)
        if year is not None:
            selected_year = str(year)

        selected_month = str(today.month)
        if month is not None:
            selected_month = str(month)

        offset_seconds = str(self.utc_offset * 60)

        if self.skin_dict['Extras'].get('display_aeris_observation', False):
            data += 'current_observation = ' + self.data_current['observation'] + ';\n'
        else:
            data += 'current_observation = null;\n'

        data += 'headerMaxDecimals = ' + self.skin_dict['Extras']['current'].get('header_max_decimals', 'null') + ';\n'
        data += "logLevel = sessionStorage.getItem('logLevel');\n"

        data += 'if (!logLevel) {\n'
        data += '    logLevel = "' + self.skin_dict['Extras'].get('jas_debug_level', '3') + '";\n'
        data += "    sessionStorage.setItem('logLevel', logLevel);\n"
        data += '}\n'


        data += 'function setupZoomDate() {\n'
        data += '    zoomDateRangePicker = new DateRangePicker("zoomdatetimerange-input",\n'
        data += '                        {\n'
        data += '                            minDate: ' + startDate + ',\n'
        data += '                            maxDate: '+ endDate + ',\n'
        data += '                            startDate: '+ startDate + ',\n'
        data += '                            endDate: ' + endDate + ',\n'
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
        data += '                            minDate: ' + startDate + ',\n'
        data += '                            maxDate: ' + endDate + ',\n'
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
        data += 'function setupPageReload() {\n'
        data += '    // Set a timer to reload the iframe/page.\n'
        data += '    var currentDate = new Date();\n'
        data += '    var futureDate = new Date();\n'
        data += '    futureDate.setTime(futureDate.getTime() + ' + wait_milliseconds + ');\n'
        data += '    var futureTimestamp = Math.floor(futureDate.getTime()/' + wait_milliseconds + ') * '+ wait_milliseconds + ';\n'
        data += '    var timeout = futureTimestamp - currentDate.getTime() + ' + delay_milliseconds + ';\n'
        data += '    setTimeout(function() { window.location.reload(true); }, timeout);\n'
        data += '}\n'
        data += '\n'
        data += '// Handle reset button of zoom control\n'
        data += 'function resetRange() {\n'
        data += '    zoomDateRangePicker.setStartDate(' + startDate + ');\n'
        data += '    zoomDateRangePicker.setEndDate(' + endDate + ');\n'
        data += '    pageCharts.forEach(function(pageChart) {\n'
        data += '            pageChart.chart.dispatchAction({type: "dataZoom", startValue: ' + startTimestamp + ', endValue: ' + endTimestamp + '});\n'
        data += '    });\n'
        data += '    updateMinMax(' + startTimestamp + ', ' + endTimestamp + ');\n'
        data += '}\n'
        data += '// Handle event messages of type "mqtt".\n'
        data += 'var test_obj = null; // Not a great idea to be global, but makes remote debugging easier.\n'
        data += 'function updateCurrentMQTT(test_obj) {\n'
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
        data +='        }\n'
        data += '\n'
        data +='        // Handle information that will be appended to the observation value.\n'
        data +='        suffix_list = sessionStorage.getItem("suffixes");\n'
        data +='        if (suffix_list) {\n'
        data +='            suffixes = suffix_list.split(",");\n'
        data +='            suffixes.forEach(function(suffix) {\n'
        data +='                suffixInfo = current.suffixes.get(suffix);\n'
        data +='                if (suffixInfo && suffixInfo.mqtt && test_obj[suffix]) {\n'
        data +='                    data = JSON.parse(sessionStorage.getItem(suffix));\n'
        data +='                    data.value = test_obj[suffix];\n'
        data +='                    sessionStorage.setItem(suffix, JSON.stringify(data));\n'
        data +='                }\n'
        data +='            });\n'
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
        data +='                suffix = JSON.parse(sessionStorage.getItem(data.suffix));\n'
        data +='                if ( suffix=== null) {\n'
        data +='                    suffixText = "";\n'
        data +='                }\n'
        data +='                else {\n'
        data +='                    suffixText = " " + suffix.value;\n'
        data +='                }\n'
        data += '\n'
        data +='                labelElem = document.getElementById(observation + "_label");\n'
        data +='                if (labelElem) {\n'
        data +='                    labelElem.innerHTML = data.label;\n'
        data +='                }\n'
        data +='                dataElem = document.getElementById(data.name + "_value");\n'
        data +='                if (dataElem) {\n'
        data +='                    dataElem.innerHTML = data.value + data.unit + suffixText;\n'
        data +='                }\n'
        data +='            }\n'
        data +='        });\n'
        data += '\n'
        data +='        // And the "current" section date/time.\n'
        data +='        if (test_obj.dateTime) {\n'
        data +='            sessionStorage.setItem("updateDate", test_obj.dateTime*1000);\n'
        data +='            timeElem = document.getElementById("updateDate");\n'
        data +='            if (timeElem) {\n'
        data +='                timeElem.innerHTML = moment.unix(test_obj.dateTime).utcOffset(' + str(self.utc_offset) + ').format(dateTimeFormat[lang].current);\n'
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
        data += '    // ToDo: cleanup, perhaps put suffix data into an array and store that\n'
        data += '    // ToDo: do a bit more in cheetah?\n'
        data += '    suffixes = [];\n'
        data += '    for (var [suffix, data] of current.suffixes) {\n'
        data +='        suffixes.push(suffix);\n'
        data +='        if (sessionStorage.getItem(suffix) === null || !jasOptions.MQTTConfig){\n'
        data +='            sessionStorage.setItem(suffix, JSON.stringify(data));\n'
        data +='        }\n'
        data += '    }\n'
        data += '    sessionStorage.setItem("suffixes", suffixes.join(","));\n'
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
        data +='        suffix = JSON.parse(sessionStorage.getItem(data.suffix));\n'
        data +='        if ( suffix=== null) {\n'
        data +='            suffixText = "";\n'
        data +='        }\n'
        data +='        else {\n'
        data +='            suffixText = " " + suffix.value;\n'
        data +='        }\n'
        data += '\n'
        data +='        document.getElementById(obs.name + "_value").innerHTML = obs.value + obs.unit + suffixText;\n'
        data += '    }\n'
        data += '    sessionStorage.setItem("observations", observations.join(","));\n'
        data += '\n'
        data += '    if(sessionStorage.getItem("updateDate") === null || !jasOptions.MQTTConfig){\n'
        data +='        sessionStorage.setItem("updateDate", updateDate);\n'
        data += '    }\n'
        data += '    document.getElementById("updateDate").innerHTML = moment.unix(sessionStorage.getItem("updateDate")/1000).utcOffset(' + str(self.utc_offset) +').format(dateTimeFormat[lang].current);\n'       
        data += '}\n'
        data += '\n'
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
        data +='        minDate = moment.unix(minMaxObsData.minDateTimeArray[minIndex]/1000).utcOffset(-300.0).format(dateTimeFormat[lang].chart["none"].label);\n'
        data +='        maxDate = moment.unix(minMaxObsData.maxDateTimeArray[maxIndex]/1000).utcOffset(-300.0).format(dateTimeFormat[lang].chart["none"].label);\n'
        data += '\n'
        data +='        observation_element=document.getElementById(minMaxObsData.minId);\n'
        data +='        observation_element.innerHTML = min + "<br>" + minDate;\n'
        data +='        observation_element=document.getElementById(minMaxObsData.maxId);\n'
        data +='        observation_element.innerHTML = max + "<br>" + maxDate;\n'
        data += '    });\n'
        data += '}\n'
        data += '\n'
        data += 'window.addEventListener("load", function (event) {\n'
        data += '    // Todo: create functions for code in the if statements\n'
        data += '    // Tell the parent page the iframe size\n'
        data += '    let message = { height: document.body.scrollHeight, width: document.body.scrollWidth };\n'
        data += '    // window.top refers to parent window\n'
        data += '    window.top.postMessage(message, "*");\n'
        data += '\n'
        data += '    // When the iframe size changes, let the parent page know\n'
        data += '    const myObserver = new ResizeObserver(entries => {\n'
        data +='        entries.forEach(entry => {\n'
        data +='        let message = { height: document.body.scrollHeight, width: document.body.scrollWidth };\n'
        data +='        // window.top refers to parent window\n'
        data +='        window.top.postMessage(message, "*");\n'
        data +='        });\n'
        data += '    });\n'
        data += '    myObserver.observe(document.body);\n'
        data += '\n'
        data += '    updateTexts();\n'
        data += '    updateLabels();\n'
        data += '    updateCharts();\n'
        data += '\n'
        data += '    if (jasOptions.minmax) {\n'
        data +='        updateMinMax(' + startTimestamp + ', ' + endTimestamp + ');\n'
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
        data += '    if (jasOptions.reload) {\n'
        data +='        setupPageReload();\n'
        data += '    }\n'
        data += '\n'
        data += '    if (jasOptions.current) {\n'
        data +='        updateCurrentObservations();\n'
        data += '    }\n'
        data +='\n'
        data += '    if (jasOptions.forecast) {\n'
        data +='        updateForecasts();\n'
        data += '    }\n'
        data += '});\n'

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

var pageCharts = [];

// Update the chart data
function updateCharts() {
    currTime = Date.now();
    startTime = currTime
    for (var index in pageCharts) {
        if (pageCharts[index].option) {
            pageCharts[index].chart.setOption(pageCharts[index].option);
        }
        prevTime = currTime;
        currTime = Date.now();
    }
}

// Ensure that the height of charts is consistent ratio of the width.
function refreshSizes() {
    radarElem = document.getElementById("radar");
    if (radarElem) {
        radarElem.style.height = radarElem.offsetWidth / 1.618 + 17  +"px"; // adding is a hack
    }

    for (var index in pageCharts) {
      chartElem = pageCharts[index].chart.getDom();
      height = chartElem.offsetWidth / 1.618 + 17  +"px"; // adding is a hack
      pageCharts[index].chart.resize({width: null, height: height});
    }
}

function getLogLevel() {
    return "Sub-page log level: " + sessionStorage.getItem("logLevel")
}

function setLogLevel(logLevel) {
    sessionStorage.setItem("logLevel", logLevel);
    updatelogLevel(logLevel.toString());
    return "Sub-page log level: " + sessionStorage.getItem("logLevel")
}

// Handle event messages of type "lang".
function handleLang(lang) {
    sessionStorage.setItem("currentLanguage", lang);
    window.location.reload(true);
}


// Handle event messages of type "log".
function handleLog(message) {
    var logDisplayElem = document.getElementById("logDisplay");
    if (logDisplayElem) {
        logDisplayElem.innerHTML = message + "\\n<br>" + logDisplayElem.innerHTML;
    }
}


function handleMQTT(message) {
    test_obj = JSON.parse(message.payload);
    
    jasLogDebug("test_obj: ", test_obj);
    jasLogDebug("sessionStorage: ", sessionStorage);
    jasLogDebug("fieldMap: ", Object.fromEntries(fieldMap));
    // To Do - only exists on pages with "current" section
    //jasLogDebug("current.observations: ", Object.fromEntries(current.observations));

    if (jasOptions.current && jasOptions.pageMQTT)
    {
        updateCurrentMQTT(test_obj);
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
        observationId = "forecastObservation" + i;
        document.getElementById("forecastDate" + i).innerHTML = forecast["day"]  + " " + forecast["date"];
        document.getElementById("forecastObservation" + i).innerHTML = forecast["observation"];
        document.getElementById("forecastTemp" + i).innerHTML = forecast["temp_min"] + " | " + forecast["temp_max"];
        document.getElementById("forecastRain" + i).innerHTML = '<i class="wi wi-raindrop"></i>' + ' ' + forecast['rain'] + '%';
        document.getElementById('forecastWind' + i).innerHTML = '<i class="wi wi-strong-wind"></i>' + ' ' + forecast['wind_min'] + ' | ' + forecast['wind_max'] + ' ' + forecast['wind_unit'];
        i += 1;
    });
}
window.addEventListener("onresize", function() {
    let message = { height: document.body.scrollHeight, width: document.body.scrollWidth };	

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
                        if (message.kind == "mqtt")
                        {
                            handleMQTT(message.message);
                        }
                        if (message.kind == "log")
                        {
                            handleLog(message.message);
                        }},
                        false
                       );
        '''

        data += javascript + "\n"

        data += '// end\n'

        elapsed_time = time.time() - start_time
        log_msg = "Generated " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return data

    def _gen_jas_options(self, filename, page):
        start_time = time.time()
        data = ''

        data += "jasOptions = {};\n"

        data += "jasOptions.pageMQTT = " + self.skin_dict['Extras']['pages'][page].get('mqtt', 'true').lower() + ";\n"
        data += "jasOptions.displayAerisObservation = -" + self.skin_dict['Extras'].get('display_aeris_observation', 'false').lower() + ";\n"
        data += "jasOptions.reload = " + self.skin_dict['Extras']['pages'][page].get('reload', 'false').lower() + ";\n"
        data += "jasOptions.zoomcontrol = " + self.skin_dict['Extras']['pages'][page].get('zoomControl', 'false').lower() + ";\n"

        data += "jasOptions.currentHeader = null;\n"

        if self.skin_dict['Extras']['current'].get('observation', False):
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
        log_msg = "Generated " + self.html_root + "/" + filename + " in " + str(elapsed_time)
        if to_bool(self.skin_dict['Extras'].get('log_times', True)):
            logdbg(log_msg)
        return data

    def _get_TimeSpanBinder(self, time_period, data_binding):
        return TimespanBinder(self._get_timespan(time_period, self.timespan.stop),
                                     self.generator.db_binder.bind_default(data_binding),
                                     data_binding=data_binding,
                                     context=time_period,
                                     formatter=self.generator.formatter,
                                     converter=self.generator.converter)

    def _get_current(self, observation, data_binding, unit_name=None):
        self.current_obj = weewx.tags.CurrentObj(
                    self.generator.db_binder.bind_default(data_binding),
                    data_binding,
                    self.timespan.stop,
                    self.generator.formatter,
                    self.generator.converter,
                    None,
                    self.generator.record
                )
        current_value = getattr(self.current_obj, observation)

        if unit_name != 'default':
            return getattr(current_value, unit_name)
        else:
            return current_value

    def _get_aggregate(self, observation, data_binding, time_period, aggregate_type, unit_name = None, rounding=2, add_label=False, localize=False):
        obs_binder = weewx.tags.ObservationBinder(
            observation,
            self._get_timespan(time_period, self.timespan.stop),
            self.generator.db_binder.bind_default(data_binding),
            data_binding,
            time_period,
            self.generator.formatter,
            self.generator.converter,
        )

        data_aggregate_binder = getattr(obs_binder, aggregate_type)

        if unit_name != 'default':
            data = getattr(data_aggregate_binder, unit_name)
        else:
            data = data_aggregate_binder

        if rounding:
            return data.round(rounding).format(add_label=add_label, localize=localize)

        return data.format(add_label=add_label, localize=localize)

    def _get_series(self, observation, data_binding, time_period, aggregate_type=None, aggregate_interval=None, time_series='both', time_unit='unix_epoch', unit_name = None, rounding=2, jsonize=True):
        obs_binder = weewx.tags.ObservationBinder(
            observation,
            self._get_timespan(time_period, self.timespan.stop),
            self.generator.db_binder.bind_default(data_binding),
            data_binding,
            time_period,
            self.generator.formatter,
            self.generator.converter,
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
