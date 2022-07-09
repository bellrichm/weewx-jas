##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext("minmax.title")
                </h5>        
                ## ToDo: move to style sheet, resize observation table to match?
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