##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

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
                        #set type = $getVar("$Extras.current.observations" + "." + $observation + ".type", "")
                        #set suffix = $getVar("$Extras.current.observations" + "." + $observation + ".suffix", "")
                        #if $type == 'sum'
                            #set observation_value = '$' + $interval_global + '.' + $observation + "." + $type
                        #else
                            #set observation_value = '$current.' + $observation
                        #end if
                        #set $observation_value += " " + $suffix
                        #set label = '$obs.label.' + $observation + $type
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