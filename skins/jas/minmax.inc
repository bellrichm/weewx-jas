##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext["minmax.title"]
                </h5>        
                <table class="table">
                  <tbody>
                    #for observation in $Extras.minmax.observations
                        #set label = '$obs.label.' + $observation 
                        #set min_value = '$' + $interval + '.' + $observation + '.min'
                        #set min_value_time = '$' + $interval + '.' + $observation + '.mintime'
                        #set max_value = '$' + $interval + '.' + $observation + '.max'                
                        #set max_value_time = '$' + $interval + '.' + $observation + '.maxtime'
                        <tr>
                            <th scope="row">#include source=$label #</th>
                            <td>#include source=$min_value #
                            <br>
                            #include source=$min_value_time #
                            </td>
                            <td>#include source=$max_value #
                            <br>
                            #include source=$max_value_time #                            
                            </td>
                        </tr>
           
                    #end for
                </tbody>
            </table>
            $current.dateTime
        </div>
    </div>
</div>