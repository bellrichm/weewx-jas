##    Copyright (c) 2021-2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#set modal_classes = ''
#if $current_modal_global
    #set modal_classes = 'data-bs-toggle="modal" data-bs-target="#currentModal"'
#end if

#set grid_cols = $getVar('$Extras.pages.' + $page + '.' + $section_global + '.grid_cols', 
                            $getVar('$Extras.pages.' + $page + '.grid_cols',
                                $getVar('$Extras.grid_cols')))
<div class="$grid_cols">
    <div class="card">
        <div class="card-body text-center">
            #if $getVar('$Extras.current.observation', False)
              #set line = '<h1 class="card-title" ' + $modal_classes + ' id="' + $Extras.current.observation + '"></h1>'
              $line
            #end if
            #if $getVar("$Extras.display_aeris_observation", False)
                <div class="card-text" id="currentObservation"></div>
            #end if
            #set i = 0
                <table class="table">
                  <tbody>
                    #for observation in $Extras.current.observations
                        #set i += 1
                        #set valueId = $observation + '_value'
                        #if $i % 2 # <tr class="row mx0"> #end if
                            <th scope="row" class="col" obs_label="$observation"></th>
                            <td id="$valueId" class="col"></td>
                        #if not $i % 2 # </tr> #end if
                    #end for
                </tbody>
            </table>
            <div id="updateDate"></div>
        </div>
    </div>
</div>