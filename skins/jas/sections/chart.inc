#set id = $section + $page_name_global
<div class="col-12 col-xl-6 mb-4">
    <div class="card">
    <div class="card-body text-center">
        #set text_label = False
        #if $getVar('$Extras.chart_definitions.' + $section + '.weewx', False)
        #set text_label = $getVar('$Extras.chart_definitions.' + $section + '.weewx.title', False)
        #end if
        #if $text_label
        <h5 class="h5-responsive indigo-text">
            $text_label
        #else
        #echo '               <h5 class="h5-responsive indigo-text" text_label="' + $section + '_title">\n'
        #end if
        </h5>
        <div id="$id"></div>
    </div>
    </div>   
</div>   