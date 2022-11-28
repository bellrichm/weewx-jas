##    Copyright (c) 2021-2022 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text" text_label="thisdate_title">
                </h5>     
                <input type="text" id="thisdatetimerange-input" style="text-align:center">   
                <table class="table">
                  <tbody>
                    #for observation in $getVar('$Extras.thisdate.observations')
                        #set aggregation_type = $getVar("$Extras.thisdate.observations." + $observation + ".type", None)
                        <tr  class="row mx0">
                        <th class="col" scope="row" obs_label="$observation"></th>
                        #if $aggregation_type is None
                            #set $id = $observation + "_thisdate_min"
                            <td id="$id" class="col">
                            </td>               
                            #set $id = $observation + "_thisdate_max"
                            <td id="$id" class="col">
                            </td>                                                          
                        #else
                            #set $id = $observation + "_thisdate_" + $aggregation_type
                            <td id="$id" class="col">
                            </td>
                            <td class="col"></td>
                        #end if
                        </tr>    
                    #end for                
                </tbody>
                </table>     
        </div>
    </div>
</div>
