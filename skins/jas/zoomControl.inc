<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.css">
<nav class="navbar navbar-expand-md navbar-light bg-light justify-content-center">
    <div class="navbar-text">
        $gettext['zoomControl_label']
        <input type="text" id="datetimerange-input2" style="text-align:center">   
        <input TYPE="button" name="resetRange" value="$gettext['resetRange_label']" onclick="resetRange()">
    </div>
</nav>
    <script src="https://cdn.jsdelivr.net/momentjs/latest/moment.min.js" type="text/javascript"></script>
    <script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>
<script>
    function resetRange() {
        dateRangePicker2.setStartDate(startDate)
        dateRangePicker2.setEndDate(endDate)
        #for $section in $getVar('Extras.pages.' + $page)
            ## todo - cleanup to not use continue
            #if $section not in $getVar('$Extras.charts')
                #continue
            #end if
            #set line = $section + 'chart'  + '.zoomX(startTimestamp, endTimestamp)'
            $line
        #end for
    }
    window.addEventListener("load", function (event) {
        dateRangePicker2 = new DateRangePicker('datetimerange-input2',
                            {
                                minDate: startDate,
                                maxDate: endDate,
                                startDate: startDate,
                                endDate: endDate,                                     
                            },
                            function(start, end, label) {
                                #for $section in $getVar('Extras.pages.' + $page)
                                    ## todo - cleanup to not use continue
                                    ##if not isinstance($Extras.pages[$page][$section],dict)
                                    #if $section not in $getVar('$Extras.charts')
                                        #continue
                                    #end if
                                    #set line = $section + 'chart'  + '.zoomX(start.unix() * 1000, end.unix() * 1000)'
                                    $line
                                #end for
                        }
        );
    });
</script>
