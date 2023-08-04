##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#set id = $section_global + $page_name_global
#set grid_cols = $getVar('$Extras.pages.' + $page + '.' + $section_global + '.grid_cols', 
                            $getVar('$Extras.pages.' + $page + '.grid_cols',
                                $getVar('$Extras.grid_cols')))
<div class="$grid_cols">
    <div class="card">
    <div class="card-body text-center">
        #set text_label = False
        #if $getVar('$Extras.chart_definitions.' + $section_global + '.weewx', False)
        #set text_label = $getVar('$Extras.chart_definitions.' + $section_global + '.weewx.title', False)
        #end if
        #if $text_label
            #echo '               <h5 class="card-title" data-bs-toggle="modal" data-bs-target="#chartModal" data-bs-chart="' + id + '">'
            $text_label
        #else
            #echo '               <h5 class="card-title" text_label="' + $section_global + '_title" data-bs-toggle="modal" data-bs-target="#chartModal" data-bs-chart="' + id + '">\n'
        #end if
        </h5>
        <div id="$id"></div>
    </div>
    </div>   
</div>   