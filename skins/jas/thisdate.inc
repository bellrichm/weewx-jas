<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.css">

<script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext["thisdate.title"]
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
                            #set $id = $observation + "min"
                            <td id="$id">
                            </td>               
                            #set $id = $observation + "max"
                            <td id="$id">
                            </td>                                                          
                        #else
                            #set $id = $observation + $aggregation_type
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
                var result = observations.filter(function(v,i) { return v[0] === timeStamp; })[0][1];               
               return result
            }
            function updateThisDate(timeStamp) {
                #for observation in $Extras.thisdate.observations
                    #set aggregation_type = $getVar("$Extras.thisdate.observations." + $observation + ".type", None)
                    #if $aggregation_type is None
                        #set value = $interval_name_global + '_min.' + $observation
                        #set line = "var obs = getObservation(timeStamp, " + $value + ")"
                        #set id = $observation + "min"
                        $line
                        var observation=document.getElementById("$id")
                        observation.innerHTML = obs                   
                        #set value = $interval_name_global + '_max.' + $observation
                        #set line = "var obs = getObservation(timeStamp, " + $value + ")"
                        #set id = $observation + "max"
                        $line
                        var observation=document.getElementById("$id")
                        observation.innerHTML = obs                             
                    #else
                        #set value = $interval_name_global + '_' + $aggregation_type + '.' + $observation
                        #set line = "var obs = getObservation(timeStamp, " + $value + ")"
                        #set id = $observation + $aggregation_type
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
                dateRangePicker.setStartDate(startDate);
                updateThisDate(startDate.unix() * 1000)
            });
        </script>





