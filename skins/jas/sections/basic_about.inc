##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<script>
    function formatDuration(timeSpan) {
        var formattedDuration = '';
        var duration = moment.duration(timeSpan, 'seconds');
        var days = Math.floor(duration.asDays());
        if (days > 0) {
            formattedDuration += days + ' ' + getText('day', days) + ' ';
        }
        var hours = duration.hours();
        if (hours > 0) {
            formattedDuration += hours + ' ' + getText('hour', hours) + ' ';
        }
        var minutes = duration.minutes();
        if (minutes > 0) {
            formattedDuration += minutes + ' ' + getText('minute', minutes) + ' ';
        }
        var seconds = duration.seconds();
        if (seconds > 0) {
            formattedDuration += seconds + ' ' + getText('second', seconds) + ' ';
        }
        return formattedDuration;
    }

    window.addEventListener("load", function (event) {
        document.getElementById("stationUptime").innerText = formatDuration($station.uptime.raw);
        document.getElementById("osUptime").innerText = formatDuration($station.os_uptime.raw);
    })

</script>

  <table>
    <tr>
      <td text_label="station_hardware"></td>
      <td>$station.hardware</td>
    </tr>
    <tr>
      <td text_label="station_latitude"></td>
      <td>$station.latitude[0]&deg; $station.latitude[1]' $station.latitude[2]</td>
    </tr>
    <tr>
      <td text_label="station_longitude"></td>
      <td>$station.longitude[0]&deg; $station.longitude[1]' $station.longitude[2]</td>
    </tr>
    <tr>
      <td text_label="station_altitude"></td>
      <td>$station.altitude</td>
    </tr>
    <tr>
      <td text_label="server_uptime"></td>
      <td id="osUptime"></td>
    </tr>
    <tr>
      <td text_label="station_uptime"></td>
      <td id="stationUptime"></td>
    </tr>
    <tr>
      <td text_label="weewx_version"></td>
      <td>$station.version</td>
    </tr>
    <tr>
      <td text_label="skin"></td>
      <td>$SKIN_NAME $SKIN_VERSION</td>
    </tr>
  </table>
