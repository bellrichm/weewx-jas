##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#from weeutil.weeutil import to_bool

#set id = $section_global + $page_name_global
#set grid_cols = $getVar('$Extras.pages.' + $page + '.' + $section_global + '.grid_cols', 
                            $getVar('$Extras.pages.' + $page + '.grid_cols',
                                $getVar('$Extras.grid_cols')))
                                
#set series_type = $getVar('$Extras.pages.' + $page + '.' + $section_global + '.series_type',
                            $getVar('$Extras.page_definition.' + $page + '.series_type', 'single'))
                                
#set modal_classes = ''
#if to_bool($getVar('$Extras.pages.' + $page + '.' + $section_global + '.chart_modal', 
                    $getVar('$Extras.pages.' + $page + '.chart_modal',
                              $getVar('$Extras.chart_modal', False))))
                              
    #if $series_type != 'mqtt'
        #set modal_classes = 'data-bs-toggle="modal" data-bs-target="#chartModal"'
    #else
        #set logmsg = 'MQTT chart ' + $section_global + ' on page ' + $page + ' cannot be modal.'
        $logerr($logmsg)
    #end if
#end if
             
<div class="$grid_cols">
    <div class="card">
    <div class="card-body text-center">
        #set text_label = False
        #if $getVar('$Extras.chart_definitions.' + $section_global + '.weewx', False)
        #set text_label = $getVar('$Extras.chart_definitions.' + $section_global + '.weewx.title', False)
        #end if
        #if $text_label
            #echo '               <h5 class="card-title" ' + $modal_classes + ' data-bs-chart="' + id + '" data-bs-title="' + $text_label + '">'
            $text_label
        #else
            #set label = $section_global + '_title'
            #echo '               <h5 class="card-title" text_label="' + $label + '" ' + $modal_classes + ' data-bs-chart="' + id + '" data-bs-title="' + $label + '">\n'
        #end if
        </h5>
        <div id="$id"></div>
    </div>
    </div>   
</div>   