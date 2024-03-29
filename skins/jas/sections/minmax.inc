##    Copyright (c) 2021-2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#set grid_cols = $getVar('$Extras.pages.' + $page + '.' + $section_global + '.grid_cols', 
                            $getVar('$Extras.pages.' + $page + '.grid_cols',
                                $getVar('$Extras.grid_cols')))
<div class="$grid_cols">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="card-title"  text_label="minmax_title"></h5>
                </h5>        
                ## ToDo: move to style sheet, resize observation table to match?
                <table class="table">
                  <tbody>
                    #for observation in $Extras.minmax.observations.sections
                        #set min_id = $observation + "_minmax_min"
                        #set max_id = $observation + "_minmax_max"
                        <tr class="row mx0">
                            <th class="col" scope="row" obs_label="$observation"></th>
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