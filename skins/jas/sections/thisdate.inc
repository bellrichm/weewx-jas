##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#import datetime

<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.css">

<script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext("thisdate.title")
                </h5>     
                <input type="text" id="datetimerange-input1" style="text-align:center">   
                <table class="table table-sm" style="font-size:80%"">
                  <tbody>
                    #for observation in $getVar('$Extras.thisdate.observations')
                        #set aggregation_type = $getVar("$Extras.thisdate.observations." + $observation + ".type", None)
                        #set label = '$obs.label.' + $observation 
                        <tr>
                        <th scope="row">#include source=$label #</th>
                        #if $aggregation_type is None
                            #set $id = $observation + "_thisdate_min"
                            <td id="$id">
                            </td>               
                            #set $id = $observation + "_thisdate_max"
                            <td id="$id">
                            </td>                                                          
                        #else
                            #set $id = $observation + "_thisdate_" + $aggregation_type
                            <td id="$id">
                            </td>
                            <td></td>
                        #end if
                        </tr>    
                    #end for                
                </tbody>
                </table>     
        </div>
    </div>
</div>
        ## ToDo - move the cdn urls
        <script src="https://cdn.jsdelivr.net/momentjs/latest/moment.min.js" type="text/javascript"></script>
        <script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>
        <script>
            function getObservation(timeStamp, observations) {
                var array_result = observations.filter(function(v,i) { return v[0] === timeStamp; });    
                if (array_result.length > 0)     {
                    return array_result[0][1]
                }

               return observations[0][1]
            }
            function updateThisDate(timeStamp) {
                #for observation in $Extras.thisdate.observations
                    #set aggregation_type = $getVar("$Extras.thisdate.observations." + $observation + ".type", None)
                    #if $aggregation_type is None
                        #set value = $interval_name_global + '_min.' + $observation
                        #set line = "var obs = getObservation(timeStamp, " + $value + ")"
                        #set id = $observation + "_thisdate_min"
                        $line
                        var observation=document.getElementById("$id")
                        observation.innerHTML = obs                   
                        #set value = $interval_name_global + '_max.' + $observation
                        #set line = "var obs = getObservation(timeStamp, " + $value + ")"
                        #set id = $observation + "_thisdate_max"
                        $line
                        var observation=document.getElementById("$id")
                        observation.innerHTML = obs                             
                    #else
                        #set value = $interval_name_global + '_' + $aggregation_type + '.' + $observation
                        #set line = "var obs = getObservation(timeStamp, " + $value + ")"
                        #set id = $observation + "_thisdate_" + $aggregation_type
                        $line
                        var observation=document.getElementById("$id")
                        observation.innerHTML = obs
                    #end if
                #end for  
            }            
            window.addEventListener("load", function (event) {
                var dateRangePicker = new DateRangePicker('datetimerange-input1',
                                    {singleDatePicker: true,
                                     minDate: startDate,
                                     maxDate: endDate
                                    },
                                     function(start, end, label) {
                                         updateThisDate(start.unix() * 1000)
                                    }
                );
                #set today = datetime.datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)
                #set selected_year = $today.year
                #if $year_global is not None
                    #set selected_year = $year_global
                #end if
                #set selected_month = $today.month
                #if $month_global is not None
                    #set selected_month = $month_global
                #end if

                #set extra_days = 0
                #while True:
                    #try:
                        #set selected_date = $today.replace(year=int($selected_year), month=int($selected_month), day=$today.day - $extra_days)
                        #break
                    #except ValueError:
                        $set extra_days += 1
                    #end try
                #end while

                dateRangePicker.setStartDate(moment.unix($selected_date.timestamp()).utcOffset($utcOffset));
                dateRangePicker.setEndDate(moment.unix($selected_date.timestamp()).utcOffset($utcOffset));
                updateThisDate($selected_date.timestamp() * 1000)
            });
        </script>





