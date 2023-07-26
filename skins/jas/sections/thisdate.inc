##    Copyright (c) 2021-2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#set grid_cols = $getVar('$Extras.pages.' + $page + '.' + $section_global + '.grid_cols', 
                            $getVar('$Extras.pages.' + $page + '.grid_cols',
                                $getVar('$Extras.grid_cols')))
<div class="$grid_cols">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="card-title"  text_label="thisdate_title"></h5>
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
