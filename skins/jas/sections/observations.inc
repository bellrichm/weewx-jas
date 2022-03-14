##    Copyright (c) 2021-2022 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<script src="../data/current.js"> </script>
<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
            <h1 id="$Extras.current.observation" class="display-2 indigo-text"></h1>
            #if $getVar("$Extras.display_aeris_observation", False)
                $current_observation['observation']
            #end if
            #set i = 0
                <table class="table">
                  <tbody>
                    #for observation in $Extras.current.observations
                        #set i += 1
                        #set labelId = $observation + '_label'
                        #set valueId = $observation + '_value'
                        #if $i % 2 # <tr> #end if
                            <th id="$labelId" scope="row"></th>
                            <td id="$valueId"></td>
                        #if not $i % 2 # </tr> #end if
                    #end for
                </tbody>
            </table>
            <div id="updateDate"></div>
        </div>
    </div>
</div>