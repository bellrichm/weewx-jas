<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
            <h1 class="display-2 indigo-text"> #include source='$current.' + $getVar('Extras.current.observation') # </h1>
            #if $getVar("$Extras.display_aeris_observation", False)
                $current_observation['observation']
            #end if
            #set i = 0
                <table class="table">
                  <tbody>
                    #for observation in $Extras.current.observations
                        #set i += 1
                        #set label = '$obs.label.' + $observation 
                        #set observation_value = '$current.' + $observation
                        #if $i % 2 # <tr> #end if
                            <th scope="row">#include source=$label #</th>
                            <td>#include source=$observation_value #</td>
                        #if not $i % 2 # </tr> #end if
                    #end for
                </tbody>
            </table>
            $current.dateTime
        </div>
    </div>
</div>