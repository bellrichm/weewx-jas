##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<script>
    function updateMinMax(startTimestamp, endTimestamp) {
        ## todo - optimize to only get index once for all observations?
        #for $observation in $getVar('Extras.minmax.observations')
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
            #echo "var min = " + $min_data_array + "[minIndex];\n"
            #echo "var max = " + $max_data_array + "[maxIndex];\n"
            #echo "var minDate = " + $min_datetime_array + "[minIndex];\n"
            #echo "var maxDate = " + $max_datetime_array + "[maxIndex];\n"
            
            var observation_element=document.getElementById("$min_id")
            observation_element.innerHTML = min + '<br>' + minDate
            var observation_element=document.getElementById("$max_id")
            observation_element.innerHTML = max + '<br>' + maxDate
            
            #echo "console.log('" + $observation + "');\n"

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
    #if $getVar('Extras.page_definition.' + $page + '.aggregate_interval.min', None) is not None
        #set $endTimestamp = "endTimestamp_min"
    #else
        #set $endTimestamp = "endTimestamp"
    #end if
    window.addEventListener("load", function (event) {
        updateMinMax(startTimestamp, $endTimestamp)
    });
</script>

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext["minmax.title"]
                </h5>        
                ## todo move to style sheet, resize observation table to match?
                <table class="table table-sm" style="font-size:80%"">
                  <tbody>
                    #for observation in $Extras.minmax.observations
                        #set label = '$obs.label.' + $observation 
                        #set min_value = '$' + $interval_global + '.' + $observation + '.min'
                        #set min_value_time = '$' + $interval_global + '.' + $observation + '.mintime.format'
                        #set max_value = '$' + $interval_global + '.' + $observation + '.max'                
                        #set max_value_time = '$' + $interval_global + '.' + $observation + '.maxtime.format'
                        #set min_id = $observation + "_minmax_min"
                        #set max_id = $observation + "_minmax_max"
                        <tr>
                            <th scope="row">#include source=$label #</th>
                            <td id="$min_id">
                            </td>
                            <td id="$max_id">
                            </td>
                        </tr>
                    #end for
                </tbody>
            </table>
        </div>
    </div>
</div>