#    Copyright (c) 2021-2022 Rich Bell <bellrichm@gmail.com>
#    See the file LICENSE.txt for your rights.

"""
This search list extension provides the following tags:
  aggregate_types
    Returns:
      A dictionary of all aggregate types (avg, max, min, sum, etc.) used.

  $forecasts
    Returns:
      A list of dictionaries containing forecastdata.
      ToDo - determine and document what forecast data is returned.

  $genCharts
    Arguments:
      page: The page to generate the charts for
      interval: The time interval to generate the chart for (day, yesterday, 2000, 200001, etc)
    Returns:
      The charts for the page.

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

  $ordinateNames
    The names of the compass ordinates.

  $skinDebug
    The skin debug option.

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

"""

import copy
import datetime
import errno
import os
import time
import json

from io import StringIO

import configobj

import weewx
try:
    # Python 3
    from urllib.request import Request, urlopen, HTTPError
except ImportError:
    # Python 2
    from urllib2 import Request, urlopen, HTTPError

from weewx.cheetahgenerator import SearchList
from weewx.units import get_label_string
from weewx.tags import TimespanBinder
from weeutil.weeutil import to_bool, TimeSpan

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
        syslog.syslog(level, 'Belchertown Extension: %s' % msg)

    def logdbg(msg):
        """ log debug messages """
        logmsg(syslog.LOG_DEBUG, msg)

    def loginf(msg):
        """ log informational messages """
        logmsg(syslog.LOG_INFO, msg)

    def logerr(msg):
        """ log error messages """
        logmsg(syslog.LOG_ERR, msg)


VERSION = "0.2.1"

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

        self.chart_defaults = self.skin_dict['Extras']['chart_defaults'].get('global', {})
        self.chart_series_defaults = self.skin_dict['Extras']['chart_defaults'].get('chart_type', {}).get('series', {})

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
            self.forecast_url = "%s%s,%s?format=json&filter=day&limit=7&client_id=%s&client_secret=%s" \
                                % (forecast_endpoint, latitude, longitude, client_id, client_secret)

            self.current_url = "%s%s,%s?&format=json&filter=allstations&limit=1&client_id=%s&client_secret=%s" \
                            % (current_endpoint, latitude, longitude, client_id, client_secret)

        self.observations, self.aggregate_types = self._get_observations()

        self._set_chart_defs()

        self.data_forecast = None
        if self._check_forecast():
            self.data_forecast = self._get_forecasts()

        self.data_current = None
        if to_bool(self.skin_dict['Extras'].get('display_aeris_observation', False)):
            self.data_current = self._get_current()

    def get_extension_list(self, timespan, db_lookup):
        # save these for use when the template variable/function is evaluated
        self.timespan = timespan
        self.db_lookup = db_lookup

        search_list_extension = {'aggregate_types': self.aggregate_types,
                                 'current_observation': self.data_current,
                                 'forecasts': self.data_forecast,
                                 'genCharts': self._gen_charts,
                                 'getUnitsLabels': self._get_units_labels,
                                 'last24hours': self._get_last24hours(),
                                 'last7days': self._get_last_n_days(7),
                                 'last31days': self._get_last_n_days(31),
                                 'last366days': self._get_last_n_days(366),
                                 'logdbg': logdbg,
                                 'loginf': loginf,
                                 'logerr': logerr,
                                 'observations': self.observations,
                                 'ordinateNames': self.ordinate_names,
                                 'skinDebug': self._skin_debug,
                                 'utcOffset': self.utc_offset,
                                 'version': VERSION,
                                 'windCompass': self._get_wind_compass,
                                 }

        return [search_list_extension]

    def _skin_debug(self, msg):
        if self.skin_debug:
            logdbg(msg)

    def _get_last24hours(self):
        start_timestamp = self.timespan.stop - 86400
        last24hours = TimespanBinder(TimeSpan(start_timestamp, self.timespan.stop),
                                     self.db_lookup,
                                     context='last24hours',
                                     formatter=self.generator.formatter,
                                     converter=self.generator.converter)

        return last24hours

    def _get_last_n_days(self, days):
        start_date = datetime.date.fromtimestamp(self.timespan.stop) - datetime.timedelta(days=days)
        start_timestamp = time.mktime(start_date.timetuple())
        last_n_days = TimespanBinder(TimeSpan(start_timestamp, self.timespan.stop),
                                     self.db_lookup,
                                     context='last_n_hours',
                                     formatter=self.generator.formatter,
                                     converter=self.generator.converter)

        return last_n_days


    def _get_units_labels(self, units):
        # For now, return label for first observations unit. ToDo - possibly change to return all?
        return get_label_string(self.generator.formatter, self.generator.converter, units[0], plural=False)

    def _get_wind_compass(self, start_offset=86400, end_offset=0):
        # default is the last 24 hrs
        db_manager = self.db_lookup()

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

        data_timespan = TimeSpan(
            self.timespan.stop - start_offset, self.timespan.stop - end_offset)
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
            if wind_speed > 0:
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

        for ordinate_name in wind_data:
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

        for wind_ordinal_data in wind_data:
            wind_compass_avg.append(wind_data[wind_ordinal_data]['average'])
            wind_compass_max.append(wind_data[wind_ordinal_data]['max'])

            i = 0
            for wind_x in wind_data[wind_ordinal_data]['speed_data']:
                wind_compass_speeds[i].append(wind_x)
                i += 1

        wind_speed_unit = self.skin_dict["Units"]["Groups"]["group_speed"]
        wind_speed_unit_label = self.skin_dict["Units"]["Labels"][wind_speed_unit]
        low_range = wind_ranges[wind_speed_unit][0]
        wind_range_legend = "['<%s %s', " % (low_range, wind_speed_unit_label)
        for high_range in wind_ranges[wind_speed_unit][1:]:
            wind_range_legend += "'%s-%s %s', " % (low_range, high_range, wind_speed_unit_label)
            low_range = high_range
        wind_range_legend += "'>%s %s']" % (high_range, wind_speed_unit_label)

        return wind_compass_avg, wind_compass_max, wind_compass_speeds, wind_range_legend

    def _get_observation_text(self, coded_weather):
        cloud_codes = ["CL", "FW", "SC", "BK", "OV",]
        text_translations = self.generator.skin_dict.get('Texts', weeutil.config.config_from_str('lang = en'))

        coverage_code = coded_weather.split(":")[0]
        intensity_code = coded_weather.split(":")[1]
        weather_code = coded_weather.split(":")[2]

        if weather_code in cloud_codes:
            cloud_code_key = 'cloud_code_' + weather_code
            observation_text = text_translations.get(cloud_code_key, cloud_code_key)
        else:
            observation_text = ''
            if coverage_code:
                coverage_code_key = 'coverage_code_' + coverage_code
                observation_text += text_translations.get(coverage_code_key, coverage_code_key) + " "
            if intensity_code:
                intensity_code_key = 'intensity_code_' + intensity_code
                observation_text += text_translations.get(intensity_code_key, intensity_code_key) + " "

            weather_code_key = 'weather_code_' + weather_code
            observation_text += text_translations.get(weather_code_key, weather_code_key)

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
            logerr("An error occurred: %s" % (data['error']['description']))
            return {}

    def _get_forecasts(self):
        now = time.time()
        current_hour = int(now - now % 3600)
        if not os.path.isfile(self.forecast_filename):
            forecast_data = self._retrieve_forecasts(current_hour)
        else:
            with open(self.forecast_filename, "r") as forecast_fp:
                forecast_data = json.load(forecast_fp)

            if current_hour > forecast_data['generated']:
                forecast_data = self._retrieve_forecasts(current_hour)

        return forecast_data['forecasts']

    def _retrieve_forecasts(self, current_hour):
        data = self._call_api(self.forecast_url)
        with open(self.raw_forecast_data_file, "w") as raw_forecast_fp:
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
                forecast['day'] = datetime.datetime.fromtimestamp(period['timestamp']).strftime("%a")
                forecast['date'] = datetime.datetime.fromtimestamp(period['timestamp']).strftime("%m/%d")
                forecast['min_temp'] = period['minTempF']
                forecast['max_temp'] = period['maxTempF']
                forecast['rain'] = period['pop']
                forecast['min_wind'] = period['windSpeedMinMPH']
                forecast['max_wind'] = period['windSpeedMaxMPH']
                forecasts.append(forecast)

            forecast_data['forecasts'] = forecasts
            with open(self.forecast_filename, "w") as forecast_fp:
                json.dump(forecast_data, forecast_fp, indent=2)
        return forecast_data

    def _get_current(self):
        now = time.time()
        current_hour = int(now - now % 3600)
        if not os.path.isfile(self.current_filename):
            current_data = self._retrieve_current(current_hour)
        else:
            with open(self.current_filename, "r") as current_fp:
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
            with open(self.current_filename, "w") as current_fp:
                json.dump(current_data, current_fp, indent=2)

        return current_data

    def _check_forecast(self):
        pages = self.skin_dict.get('Extras', {}).get('pages', {})
        for page in pages:
            if 'forecast' in self.skin_dict['Extras']['pages'][page].sections:
                return True

        return False

    def _get_observations(self):
        # todo - rename now has 'side effect' of returning aggregate_types
        
        observations = {}
        aggregate_types = {}
        skin_data_binding = self.skin_dict['Extras'].get('data_binding','wx_binding')
        charts = self.skin_dict.get('Extras', {}).get('chart_definitions', {})

        pages =  self.skin_dict.get('Extras', {}).get('pages', {})
        for page in pages:
            for chart in pages[page].sections:
                if chart in charts:
                    chart_data_binding = charts[chart].get('weewx', {}).get('data_binding', skin_data_binding)
                    series = charts[chart].get('series', {})
                    for obs in series:
                        weewx_options = series[obs].get('weewx', {})
                        observation = weewx_options.get('observation', obs)
                        data_binding =  series[obs].get('weewx', {}).get('data_binding', chart_data_binding)
                        if observation not in self.wind_observations:
                            if observation not in observations:
                                observations[observation] = {}
                                observations[observation]['aggregate_types'] = {}

                            aggregate_type = weewx_options.get('aggregate_type', 'avg')
                            observations[observation]['aggregate_types'][aggregate_type] = {}
                            observations[observation]['aggregate_types'][aggregate_type][data_binding] = {}
                            aggregate_types[aggregate_type] = {}

        minmax_observations = self.skin_dict.get('Extras', {}).get('minmax', {}).get('observations', {})
        minmax_data_binding = self.skin_dict.get('Extras', {}).get('minmax', {}).get('data_binding', skin_data_binding)
        for observation in minmax_observations:
            data_binding =  minmax_observations[observation].get('data_binding', minmax_data_binding)
            if observation not in self.wind_observations:
                if observation not in observations:
                    observations[observation] = {}
                    observations[observation]['aggregate_types'] = {}

                observations[observation]['aggregate_types']['min'] = {}
                observations[observation]['aggregate_types']['min'][data_binding] = {}
                aggregate_types['min'] = {}
                observations[observation]['aggregate_types']['max'] = {}
                observations[observation]['aggregate_types']['max'][data_binding] = {}
                aggregate_types['max'] = {}

        return observations, aggregate_types

    def _iterdict(self, indent, page, chart, chart_js, interval, dictionary):
        chart2 = chart_js
        for key, value in dictionary.items():
            if isinstance(value, dict):
                if key == 'weewx':
                    continue
                if key == 'series':
                    chart2 += indent + "series: [\n"
                    
                    if self.chart_defs[chart].get('weewx', {}).get('type') == 'yeartoyear':
                        obs = next(iter(value))
                        for year in range(int(self.skin_dict['Extras']['pages'][page]['start']), int(self.skin_dict['Extras']['pages'][page]['end']) + 1):
                            chart2 += indent + " {\n"
                            chart2 += "    name: '" + str(year) + "',\n"
                            chart2 = self._iterdict(indent + '  ', page, chart, chart2, interval, value[obs])
                            chart2 += indent + "  },\n"
                    else:
                        for obs in value:
                            aggregate_type = self.skin_dict['Extras']['chart_definitions'][chart]['series'][obs]['weewx']['aggregate_type']
                            aggregate_interval = self.skin_dict['Extras']['page_definition'][page].get('aggregate_interval', {}).get(aggregate_type, 'none')

                            # set the aggregate_interval at the beginning of the chart definition, somit can be used in the chart
                            # Note, this means the last observation's aggregate type will be used to determine the aggregate interval
                            chart2 = "#set global aggregate_interval_global = 'aggregate_interval_" + aggregate_interval + "'\n" + chart2

                            chart2 += indent + " {\n"
                            chart2 = self._iterdict(indent + '  ', page, chart, chart2, interval, value[obs])

                            chart2 += indent + "},\n"

                    chart2 += indent +"]\n"
                else:
                    chart2 += indent + key + ":" + " {\n"
                    chart2 = self._iterdict(indent + '  ', page, chart, chart2, interval, value)
                    chart2 += indent + "},\n"
            else:
                chart2 += indent + key + ": " + value + ",\n"
        return chart2

    def _set_chart_defs(self):
        self.chart_defs = configobj.ConfigObj()
        for chart in self.skin_dict['Extras']['chart_definitions'].sections:
            self.chart_config = configobj.ConfigObj(StringIO("[%s]" % (chart)))
            self.chart_defs[chart] = {}
            if 'polar' in self.skin_dict['Extras']['chart_definitions'][chart]:
                coordinate_type = 'polar'
            elif 'grid' in self.skin_dict['Extras']['chart_definitions'][chart]:
                coordinate_type = 'grid'
            elif 'weewx' in self.skin_dict['Extras']['chart_definitions'][chart]:
                coordinate_type = self.skin_dict['Extras']['chart_definitions'][chart]['weewx'].get('type', 'grid')
            else:
                coordinate_type = 'grid'
            self.chart_config[chart].merge(self.chart_defaults.get(coordinate_type, {}))
            self.chart_defs[chart].merge(self.chart_defaults.get(coordinate_type, {}))

            self.chart_config[chart].merge(self.skin_dict['Extras']['chart_definitions'][chart])
            self.chart_defs[chart].merge(self.skin_dict['Extras']['chart_definitions'][chart])

            weewx_options = {}
            weewx_options['aggregate_type'] = 'avg'

            for value in self.skin_dict['Extras']['chart_definitions'][chart]['series']:
                charttype =  self.skin_dict['Extras']['chart_definitions'][chart]['series'][value]['type']
                self.chart_defs[chart]['series'][value].merge((self.chart_series_defaults.get(coordinate_type, {}).get(charttype,{})))
                weewx_options['observation'] = value
                if 'weewx' not in self.chart_defs[chart]['series'][value]:
                    self.chart_defs[chart]['series'][value]['weewx'] = {}
                weeutil.config.conditional_merge(self.chart_defs[chart]['series'][value]['weewx'], weewx_options)

    def _gen_charts(self, page, interval, page_name):
        skin_data_binding = self.skin_dict['Extras'].get('data_binding','wx_binding')

        #chart_final = 'var pageCharts = [];\n'
        chart_final = '## charts\n'
        chart2 = ""
        charts = self.skin_dict['Extras']['chart_definitions']
        for chart in self.skin_dict['Extras']['pages'][page]:
            if chart in charts.sections:
                chart_data_binding = charts[chart].get('weewx', {}).get('data_binding', skin_data_binding)
                chart2 += "#set global series_observations_global = []\n"

                # for now, do not support overriding chart options by page
                #self.charts_def[chart].merge(self.skin_dict['Extras']['pages'][page][chart])
                for observation in self.chart_defs[chart]['series']:
                    obs = self.chart_defs[chart]['series'][observation].get('weewx', {}).get('observation', observation)
                    data_binding = self.chart_defs[chart]['series'][observation].get('weewx', {}).get('data_binding', chart_data_binding)
                    chart2 += "$series_observations_global.append('" + obs + "')\n"
                #chart2 += "$series_observations_global\n"

                chart_js = "var option = {\n"
                chart2 += self._iterdict('  ', page, chart, chart_js, interval, self.chart_defs[chart])
                chart2 += "};\n"
                chart2 += "var telem = document.getElementById('" + chart + page_name + "');\n"
                chart2 += "var " + chart + "chart = echarts.init(document.getElementById('" + chart + page_name + "'));\n"
                chart2 += chart + "chart.setOption(option);\n"

                chart2 += "pageChart = {};\n"

                if interval != 'mqtt':
                    chart2 += "option = {\n"
                    chart2 += "  series: [\n"
                    chart_type = self.chart_defs[chart].get('weewx', {}).get('type')
                    if page_name == 'historical':
                        for obs in self.chart_defs[chart]['series']:
                            aggregate_type = self.chart_defs[chart]['series'][obs]['weewx']['aggregate_type']
                            chart2 += "    {name: " + self.chart_defs[chart]['series'][obs]['name'] + ",\n"
                            chart2 += "     data: [\n" 
                            for year in range(int(self.skin_dict['Extras']['pages'][page]['start']), int(self.skin_dict['Extras']['pages'][page]['end']) + 1):
                                chart2 += "            ...year" + str(year) + "_" + aggregate_type + "." + self.chart_defs[chart]['series'][obs]['weewx']['observation'] + "_"  + data_binding + ",\n"
                            chart2 += "          ]},\n"
                    elif chart_type == 'yeartoyear':
                        obs = next(iter( self.chart_defs[chart]['series']))
                        aggregate_type = self.chart_defs[chart]['series'][obs]['weewx']['aggregate_type']
                        for year in range(int(self.skin_dict['Extras']['pages'][page]['start']), int(self.skin_dict['Extras']['pages'][page]['end']) + 1):
                            chart2 += "    {name: '" + str(year) + "',\n"
                            chart2 += "     data: year" + str(year) + "_" + aggregate_type \
                                   + "." + obs + "_"  + data_binding \
                                   + ".map(arr => [moment.unix(arr[0] / 1000).utcOffset(" + "-240.0).format('MM/DD'), arr[1]]),\n" \
                                   + "},\n"
                    else:
                        for obs in self.chart_defs[chart]['series']:
                            aggregate_type = self.chart_defs[chart]['series'][obs]['weewx']['aggregate_type']
                            chart2 += "    {name: " + self.chart_defs[chart]['series'][obs]['name'] + ",\n"
                            chart2 += "    data: " \
                                    + interval + "_" + aggregate_type \
                                    + "." + self.chart_defs[chart]['series'][obs]['weewx']['observation'] + "_"  + data_binding \
                                    + "},\n"
                    chart2 += "]};\n"
                    chart2 += "pageChart.option = option;\n"
                else:
                    chart2 += "pageChart.option = null;\n"

                chart2 += "pageChart.chart = " + chart + "chart;\n"
                chart2 += "pageCharts.push(pageChart);\n"
                chart2 += "#set global series_observations_global = None\n"
                chart2 += "$series_observations_global\n"

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
