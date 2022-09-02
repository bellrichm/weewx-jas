##    Copyright (c) 2021-2022 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

#set date_picker_version = $getVar("$Extras.date_picker_version", "latest")
<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@$date_picker_version/dist/vanilla-datetimerange-picker.css">
<nav class="navbar navbar-expand-md navbar-light bg-light justify-content-center">
    <div class="navbar-text">
        $gettext('zoomControl_label')
        <input type="text" id="datetimerange-input2" style="text-align:center">   
        <input TYPE="button" name="resetRange" value="$gettext('resetRange_label')" onclick="resetRange()">
    </div>
</nav>
    #set momentjs_version = $getVar("$Extras.momentjs_version", "latest")
    <script src="https://cdn.jsdelivr.net/npm/moment@$momentjs_version/moment.min.js" type="text/javascript"></script>
    <script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@$date_picker_version/dist/vanilla-datetimerange-picker.js"></script>
