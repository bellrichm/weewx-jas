##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#echo '    <script>\n'
#echo '      window.addEventListener("load", function (event) {\n'
#echo '      console.debug(Date.now().toString() + " iframe start");\n'

#set $series_type = $getVar('$Extras.page_definition.' + $page + '.series_type', 'single')
#if $series_type == 'single'    
    #echo '        ' + $interval_long_name_global + 'dataLoad();\n'
#else if $series_type == 'multiple' or $series_type == 'comparison'
    #set $data_binding = $getVar('Extras.pages.' + $page + '.data_binding', $getVar("$Extras.data_binding", $data_binding))
    #set (year_start,year_end) = $getRange($getVar('$Extras.pages.' + $page + '.start', None), $getVar('$Extras.pages.' + $page + '.end', None), $data_binding)
    #for $year in range($year_start, $year_end)
        #echo '        year' + str($year) + '_dataLoad();\n'
    #end for
#end if

#echo '        message = {};\n'
#echo '        message.kind = "dataLoaded";\n'
#echo '        message.message = JSON.stringify(pageData);\n'
#echo '        window.parent.postMessage(message, "*");\n'
#echo '        console.debug(Date.now().toString() + " iframe end");\n'
#echo '      })\n'
#echo '    </script>\n'
