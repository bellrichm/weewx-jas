##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext("minmax.title")
                </h5>        
                ## ToDo: move to style sheet, resize observation table to match?
                <table class="table">
                  <tbody>
                    #for observation in $Extras.minmax.observations.sections
                        #set label = '$obs.label.' + $observation 
                        #set min_id = $observation + "_minmax_min"
                        #set max_id = $observation + "_minmax_max"
                        <tr class="row mx0">
                            <th class="col" scope="row">#include source=$label #</th>
                            <td id="$min_id" class="col">
                            </td>
                            <td id="$max_id" class="col">
                            </td>
                        </tr>
                    #end for
                </tbody>
            </table>
        </div>
    </div>
</div>