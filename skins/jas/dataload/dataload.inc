##    Copyright (c) 2023 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#from weeutil.weeutil import to_list
#set page_name = $year($data_binding=$data_binding).start.format('%Y') + '-' + $month($data_binding=$data_binding).start.format('%m')


#set momentjs_version = $getVar("$Extras.momentjs_version", "latest")
#set momentjs_minified = ""
#if $getVar("$Extras.momentjs_minified", True)
  #set momentjs_minified = ".min"
#end if

#if 'data' in to_list($getVar("$Extras.pages." + $page + ".query_string_on", $getVar("$Extras.pages.query_string_on", [])))
  #set query_string = "?ts=" + str($current.dateTime.raw)
#else
  #set query_string = ""
#end if

<!doctype html>
<html>
  <head>
    #echo '    <script src="https://cdn.jsdelivr.net/npm/moment@' + $momentjs_version + '/moment' + $momentjs_minified + '.js"></script>\n'
    #if $page_name_global == 'yeartoyear' or $page_name_global == 'multiyear'
      #set $data_binding = $getVar('Extras.pages.' + $page + '.data_binding', $getVar("$Extras.data_binding", $data_binding))
      #set (year_start,year_end) = $getRange($getVar('$Extras.pages.' + $page + '.start', None), $getVar('$Extras.pages.' + $page + '.end', None), $data_binding)
      #for $year in range($year_start, $year_end)
        #echo '    <script src="' + str($year) + '.js' + $query_string + '"></script>\n'
      #end for    
    #else
      #echo '    <script src="' + $page_name_global +  '.js' + $query_string + '"></script>\n'
    #end if
    #include 'dataload/eventlistener.inc'
  </head>
</html>