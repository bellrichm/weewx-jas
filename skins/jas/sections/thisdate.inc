##    Copyright (c) 2021 Rich Bell <bellrichm@gmail.com>
##    See the file LICENSE.txt for your rights.

<link type="text/css" rel="stylesheet" href="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.css">

<script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>

<div class="col-12 col-xl-6 mb-4">
    <div class="card">
        <div class="card-body text-center">
                <h5 class="h5-responsive indigo-text">
                  $gettext("thisdate.title")
                </h5>     
                <input type="text" id="datetimerange-input1" style="text-align:center">   
                <table class="table table-sm" style="font-size:80%"">
                  <tbody>
                    #for observation in $getVar('$Extras.thisdate.observations')
                        #set aggregation_type = $getVar("$Extras.thisdate.observations." + $observation + ".type", None)
                        #set label = '$obs.label.' + $observation 
                        <tr>
                        <th scope="row">#include source=$label #</th>
                        #if $aggregation_type is None
                            #set $id = $observation + "_thisdate_min"
                            <td id="$id">
                            </td>               
                            #set $id = $observation + "_thisdate_max"
                            <td id="$id">
                            </td>                                                          
                        #else
                            #set $id = $observation + "_thisdate_" + $aggregation_type
                            <td id="$id">
                            </td>
                            <td></td>
                        #end if
                        </tr>    
                    #end for                
                </tbody>
                </table>     
        </div>
    </div>
</div>
        ## ToDo - move the cdn urls
        <script src="https://cdn.jsdelivr.net/momentjs/latest/moment.min.js" type="text/javascript"></script>
        <script src="https://cdn.jsdelivr.net/gh/alumuko/vanilla-datetimerange-picker@latest/dist/vanilla-datetimerange-picker.js"></script>






