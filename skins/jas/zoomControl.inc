<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.css">
<nav class="navbar navbar-expand-md navbar-light bg-light justify-content-center">
    <div class="navbar-text">
        $gettext['zoomControl_label']
        <input type="text" id="datetimerange-input2" style="text-align:center">   
        <input TYPE="button" name="resetRange" value="$gettext['resetRange_label']" onclick="resetRange()">
    </div>
</nav>
    <script src="https://cdn.jsdelivr.net/momentjs/latest/moment.min.js" type="text/javascript"></script>
    <script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>
<script>
    function resetRange() {
        dateRangePicker2.setStartDate(startDate)
        dateRangePicker2.setEndDate(endDate)
        #for $section in $getVar('Extras.pages.' + $page)
            ## todo - cleanup to not use continue
            #if $section not in $getVar('$Extras.charts')
                #continue
            #end if
            #set line = $section + 'chart'  + '.zoomX(startTimestamp, endTimestamp)'
            $line
        #end for
        updateMinMax(startTimestamp, endTimestamp_min)
    }
    function updateMinMax(startTimestamp, endTimestamp) {
        ## minmax_observations = self.skin_dict.get('Extras', {}),.get('minmax', {}).get('observations', {})
        ## todo - optimize to only get index once for all observations?
        #for $observation in $getVar('Extras.minmax.observations')
            $logdbg($observation)
            #set min_datetime_array = $interval_name_global + "_min_" + $observation + "_dateTime"
            #set min_data_array = $interval_name_global + "_min_" + $observation + "_data"
            #set max_datetime_array = $interval_name_global + "_max_" + $observation + "_dateTime"
            #set max_data_array = $interval_name_global + "_max_" + $observation + "_data"            
            #set min_id = $observation + "_minmax_min"
            #set max_id = $observation + "_minmax_max"

            #echo "startIndex = " + $min_datetime_array + ".findIndex(element => element == startTimestamp);\n"
            #echo "endIndex = " + $min_datetime_array + ".findIndex(element => element == endTimestamp);\n"
            #echo "var minIndex =" + $min_data_array + ".indexOf(Math.min(..." + $min_data_array + ".slice(startIndex, endIndex)));\n"
            #echo "var maxIndex =" + $max_data_array + ".indexOf(Math.max(..." + $max_data_array + ".slice(startIndex, endIndex)));\n"
            ## todo - format datetime, labels, etc.
            ## todo use this for initial population of page
            #echo "var min = " + $min_data_array + "[minIndex];\n"
            #echo "var max = " + $max_data_array + "[maxIndex];\n"
            #echo "var minDate = " + $min_datetime_array + "[minIndex];\n"
            #echo "var maxDate = " + $max_datetime_array + "[maxIndex];\n"
            
            var observation_element=document.getElementById("$min_id")
            ##observation_element.innerHTML = min + '<br>' + minDate
            var observation_element=document.getElementById("$max_id")
            ##observation_element.innerHTML = max + '<br>' + maxDate
            
            #echo "console.log('" + $observation + "');\n"
            console.log(last31days_min.heatindex)
            console.log(last31days_max.heatindex)
            console.log(startIndex)
            console.log(endIndex)
            console.log(minIndex)
            console.log(maxIndex)
            console.log(max)
            console.log(startTimestamp)
            console.log(endTimestamp)
            console.log("done")            
        #end for
    }
    window.addEventListener("load", function (event) {
        dateRangePicker2 = new DateRangePicker('datetimerange-input2',
                            {
                                minDate: startDate,
                                maxDate: endDate,
                                startDate: startDate,
                                endDate: endDate,                                     
                            },
                            function(start, end, label) {
                                #for $section in $getVar('Extras.pages.' + $page)
                                    ## todo - cleanup to not use continue
                                    ##if not isinstance($Extras.pages[$page][$section],dict)
                                    #if $section not in $getVar('$Extras.charts')
                                        #continue
                                    #end if
                                    #set line = $section + 'chart'  + '.zoomX(start.unix() * 1000, end.unix() * 1000)'
                                    $line
                                #end for
                                updateMinMax(start.unix() * 1000, end.startOf('day').unix() * 1000)
                        }
        );
    });
</script>
